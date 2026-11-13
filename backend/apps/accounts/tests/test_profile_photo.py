import io

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.models import Follow
from apps.accounts.tests.test_social import verified_user


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    cache.clear()  # the upload throttle counts in the cache
    return tmp_path


def photo(size=(1200, 800), image_format="JPEG", name="me.jpg", exif=None):
    buffer = io.BytesIO()
    options = {"exif": exif} if exif else {}
    Image.new("RGB", size, "red").save(buffer, image_format, **options)
    return SimpleUploadedFile(name, buffer.getvalue())


def upload(client, file):
    return client.post("/api/me/photo/", {"photo": file}, format="multipart")


def stored(media_root, url):
    return media_root / url.removeprefix("/media/")


@pytest.mark.django_db
def test_upload_stores_a_square_copy_without_metadata(client, media_root):
    me = verified_user("me", "Me")
    client.force_login(me)
    exif = Image.Exif()
    exif[0x8825] = {2: (38.0, 59.0, 0.0)}  # GPS latitude

    response = client.post(
        "/api/me/photo/",
        {"photo": photo(exif=exif, name="../../evil.html")},
    )

    assert response.status_code == 200, response.content
    url = response.json()["profile_photo_url"]
    assert url.startswith("/media/profile-photos/") and url.endswith(".jpg")
    assert "evil" not in url
    with Image.open(stored(media_root, url)) as saved:
        assert saved.size == (512, 512)
        assert not saved.getexif()


@pytest.mark.django_db
def test_small_photos_are_cropped_square_but_not_upscaled(client, media_root):
    client.force_login(verified_user("me", "Me"))

    url = client.post(
        "/api/me/photo/", {"photo": photo(size=(300, 200), image_format="PNG")}
    ).json()["profile_photo_url"]

    assert url.endswith(".png")
    with Image.open(stored(media_root, url)) as saved:
        assert saved.size == (200, 200)


@pytest.mark.django_db
def test_replacing_and_removing_delete_the_old_file(
    client, media_root, django_capture_on_commit_callbacks
):
    client.force_login(verified_user("me", "Me"))
    with django_capture_on_commit_callbacks(execute=True):
        first = client.post("/api/me/photo/", {"photo": photo()}).json()["profile_photo_url"]
    with django_capture_on_commit_callbacks(execute=True):
        second = client.post("/api/me/photo/", {"photo": photo()}).json()["profile_photo_url"]

    assert first != second
    assert not stored(media_root, first).exists()
    assert stored(media_root, second).exists()

    with django_capture_on_commit_callbacks(execute=True):
        removed = client.delete("/api/me/photo/")
    assert removed.status_code == 200
    assert removed.json()["profile_photo_url"] is None
    assert not stored(media_root, second).exists()


@pytest.mark.django_db
def test_rejects_files_that_arent_photos(client):
    client.force_login(verified_user("me", "Me"))

    response = client.post(
        "/api/me/photo/", {"photo": SimpleUploadedFile("me.jpg", b"<html>not a photo</html>")}
    )

    assert response.status_code == 400
    assert "isn't a JPEG, PNG or WebP image" in str(response.json())


@pytest.mark.django_db
def test_rejects_photos_over_10_mb(client):
    client.force_login(verified_user("me", "Me"))
    huge = SimpleUploadedFile("huge.jpg", b"\0" * (10 * 1024 * 1024 + 1))

    response = client.post("/api/me/photo/", {"photo": huge})

    assert response.status_code == 400
    assert "larger than 10 MB" in str(response.json())


@pytest.mark.django_db
def test_requires_sign_in(client):
    assert client.post("/api/me/photo/", {"photo": photo()}).status_code in (401, 403)


@pytest.mark.django_db
def test_photo_shows_on_profiles_follow_lists_and_listings(client):
    me = verified_user("me", "Me")
    viewer = verified_user("viewer", "Viewer")
    Follow.objects.create(follower=me, following=viewer)
    client.force_login(me)
    url = client.post("/api/me/photo/", {"photo": photo()}).json()["profile_photo_url"]
    client.force_login(viewer)

    assert client.get("/api/users/me/").json()["profile_photo_url"] == url
    followers = client.get("/api/users/viewer/followers/").json()["results"]
    assert followers[0]["profile_photo_url"] == url
    assert client.get("/api/users/viewer/").json()["profile_photo_url"] is None


@pytest.mark.django_db
def test_reporting_a_profile_keeps_a_copy_of_its_photo(client, django_capture_on_commit_callbacks):
    from apps.trust.models import EvidenceFile, Report
    from apps.trust.services import create_report

    me = verified_user("me", "Me")
    reporter = verified_user("reporter", "Reporter")
    client.force_login(me)
    client.post("/api/me/photo/", {"photo": photo()})
    me.refresh_from_db()

    report = create_report(
        reporter=reporter,
        target_type=Report.TargetType.USER,
        target_id=me.pk,
        reason=Report.Reason.SPAM,
    )
    # Changing the photo afterwards doesn't touch the evidence copy.
    with django_capture_on_commit_callbacks(execute=True):
        client.delete("/api/me/photo/")

    evidence = EvidenceFile.objects.get(snapshot__report=report)
    assert evidence.original_name == me.profile_photo.name
    with evidence.file.open("rb") as copy, Image.open(copy) as saved:
        assert saved.size == (512, 512)
