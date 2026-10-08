import io
import threading
import time

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, transaction
from PIL import Image
from procrastinate import testing
from procrastinate.contrib.django import app
from procrastinate.contrib.django.models import ProcrastinateJob

from apps.accounts.models import User
from apps.listings import services, tasks
from apps.listings.models import Category, ItemDetails, ListingPhoto
from apps.schools.models import School


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def seller():
    umd = School.objects.get(slug="umd")
    return User.objects.create_user("seller@umd.edu", "pw-123456789", username="seller", school=umd)


@pytest.fixture
def in_memory_jobs():
    """Jobs go to Procrastinate's in-memory connector instead of Postgres, and
    in_memory_jobs.run_worker(wait=False) runs them in this process."""
    with app.replace_connector(testing.InMemoryConnector()) as in_memory_app:
        yield in_memory_app


def photo(size, image_format="JPEG", name="photo.jpg", mode="RGB", color="red"):
    buffer = io.BytesIO()
    Image.new(mode, size, color).save(buffer, image_format)
    return SimpleUploadedFile(name, buffer.getvalue())


def create_listing(seller, photos):
    return services.create_item_listing(
        seller,
        category=Category.objects.get(slug="women-coats-jackets"),
        title="Gray winter jacket",
        price_cents=2500,
        condition=ItemDetails.Condition.LIKE_NEW,
        photos=photos,
    )


def thumbnail_files(media_root):
    return [p for p in (media_root / "listings" / "thumbnails").rglob("*") if p.is_file()]


# Committed transactions, because the worker runs each job in a thread with its own database
# connection; serialized_rollback restores the seeded school and categories afterwards.
@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_upload_ends_with_a_thumbnail(client, seller, media_root, in_memory_jobs):
    client.force_login(seller)
    photos = [
        photo((1200, 900), "JPEG", "a.jpg"),
        photo((300, 1000), "PNG", "b.png"),
        photo((100, 80), "WEBP", "c.webp"),  # already small: never upscaled
    ]
    response = client.post(
        "/api/listings/",
        {
            "category": Category.objects.get(slug="women-coats-jackets").pk,
            "title": "Gray winter jacket",
            "price_cents": 2500,
            "condition": "like_new",
            "photos": photos,
        },
    )
    assert response.status_code == 201
    listing_id = response.json()["id"]
    assert [p["thumbnail_url"] for p in response.json()["photos"]] == [None, None, None]
    assert [job["task_name"] for job in in_memory_jobs.connector.jobs.values()] == [
        "listings.make_photo_thumbnail"
    ] * 3

    in_memory_jobs.run_worker(wait=False, install_signal_handlers=False, listen_notify=False)

    assert {job["status"] for job in in_memory_jobs.connector.jobs.values()} == {"succeeded"}
    photos = client.get(f"/api/listings/{listing_id}/").json()["photos"]
    expected = [("JPEG", (400, 300)), ("PNG", (120, 400)), ("WEBP", (100, 80))]
    for body, (image_format, size) in zip(photos, expected, strict=True):
        assert body["thumbnail_url"].startswith("/media/listings/thumbnails/")
        thumbnail = ListingPhoto.objects.get(pk=body["id"]).thumbnail
        with Image.open(media_root / thumbnail.name) as image:
            assert (image.format, image.size) == (image_format, size)


@pytest.mark.django_db
def test_thumbnail_job_is_queued_in_the_upload_transaction(seller):
    """With the real (Postgres) connector, the job row commits or rolls back with the photo."""
    with pytest.raises(RuntimeError), transaction.atomic():
        create_listing(seller, [photo((800, 600))])
        assert ProcrastinateJob.objects.filter(task_name="listings.make_photo_thumbnail").exists()
        raise RuntimeError("the upload fails after the photo is stored")

    assert not ListingPhoto.objects.exists()
    assert not ProcrastinateJob.objects.exists()


@pytest.mark.django_db
def test_photo_added_while_editing_gets_a_thumbnail_job(seller):
    listing = create_listing(seller, [photo((800, 600))])
    added = services.add_photo(listing, seller, photo((800, 600)))
    jobs = ProcrastinateJob.objects.filter(task_name="listings.make_photo_thumbnail")
    assert jobs.filter(args={"photo_id": added.pk}).exists()


@pytest.mark.django_db
def test_deleting_a_photo_deletes_its_thumbnail(
    seller, media_root, django_capture_on_commit_callbacks
):
    listing = create_listing(seller, [photo((800, 600)), photo((800, 600))])
    first = listing.photos.get(position=0)
    tasks.make_photo_thumbnail(photo_id=first.pk)
    assert len(thumbnail_files(media_root)) == 1

    with django_capture_on_commit_callbacks(execute=True):
        services.delete_photo(listing, seller, first.pk)

    assert thumbnail_files(media_root) == []


@pytest.mark.django_db
def test_thumbnail_job_can_run_again(seller, media_root):
    listing_photo = create_listing(seller, [photo((800, 600))]).photos.get()
    tasks.make_photo_thumbnail(photo_id=listing_photo.pk)
    first = ListingPhoto.objects.get(pk=listing_photo.pk).thumbnail.name

    tasks.make_photo_thumbnail(photo_id=listing_photo.pk)

    assert ListingPhoto.objects.get(pk=listing_photo.pk).thumbnail.name == first
    assert len(thumbnail_files(media_root)) == 1


@pytest.mark.django_db
def test_thumbnail_job_skips_a_deleted_photo(seller, media_root):
    listing_photo = create_listing(seller, [photo((800, 600))]).photos.get()
    listing_photo.delete()

    tasks.make_photo_thumbnail(photo_id=listing_photo.pk)  # doesn't raise

    assert thumbnail_files(media_root) == []


def run_and_close_connection(target, *args):
    """Each thread gets its own database connection; close it when the thread ends."""
    try:
        target(*args)
    finally:
        connection.close()


def wait_until(condition, timeout=10):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.05)


def waiting_on_a_row_lock():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_stat_activity"
            " WHERE datname = current_database() AND wait_event_type = 'Lock'"
        )
        return cursor.fetchone()[0] > 0


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_thumbnail_finished_during_a_photo_delete_leaves_no_file(seller, media_root, monkeypatch):
    """delete_photo has read the photo (no thumbnail yet) but not deleted it when the job
    finishes. The job's write must wait for the delete, find the photo gone and drop its
    file; without the row lock it would record a thumbnail the delete never removes."""
    listing = create_listing(seller, [photo((800, 600)), photo((800, 600))])
    doomed = listing.photos.get(position=0)
    has_read, may_delete = threading.Event(), threading.Event()
    delete = ListingPhoto.delete

    def pause_then_delete(self, *args, **kwargs):
        has_read.set()
        assert may_delete.wait(timeout=10)
        return delete(self, *args, **kwargs)

    monkeypatch.setattr(ListingPhoto, "delete", pause_then_delete)
    deleting = threading.Thread(
        target=run_and_close_connection,
        args=(services.delete_photo, listing, seller, doomed.pk),
    )
    deleting.start()
    assert has_read.wait(timeout=10)

    job = threading.Thread(
        target=run_and_close_connection, args=(tasks.make_photo_thumbnail, doomed.pk)
    )
    job.start()
    wait_until(lambda: waiting_on_a_row_lock() or not job.is_alive())
    may_delete.set()
    deleting.join(timeout=10)
    job.join(timeout=10)

    assert not ListingPhoto.objects.filter(pk=doomed.pk).exists()
    assert thumbnail_files(media_root) == []


@pytest.mark.django_db
def test_photo_deleted_while_its_thumbnail_is_made_leaves_no_file(seller, media_root, monkeypatch):
    listing_photo = create_listing(seller, [photo((800, 600))]).photos.get()
    encode = services._encode_photo

    def delete_photo_then_encode(*args):
        ListingPhoto.objects.filter(pk=listing_photo.pk).delete()
        return encode(*args)

    monkeypatch.setattr(services, "_encode_photo", delete_photo_then_encode)
    tasks.make_photo_thumbnail(photo_id=listing_photo.pk)

    assert thumbnail_files(media_root) == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("image_format", "mode", "color", "thumbnail_mode"),
    [
        ("JPEG", "L", 128, "L"),
        ("JPEG", "CMYK", (0, 0, 0, 0), "CMYK"),
        ("PNG", "RGBA", (255, 0, 0, 128), "RGBA"),
        ("PNG", "P", 3, "RGB"),  # converted, so it scales smoothly
        ("PNG", "I;16", 1000, "I;16"),  # 16-bit greyscale
        ("WEBP", "RGBA", (255, 0, 0, 128), "RGBA"),
    ],
)
def test_thumbnail_keeps_format_and_pixel_mode(
    seller, media_root, image_format, mode, color, thumbnail_mode
):
    upload = photo((2048, 1024), image_format, mode=mode, color=color)
    listing_photo = create_listing(seller, [upload]).photos.get()

    tasks.make_photo_thumbnail(photo_id=listing_photo.pk)

    thumbnail = ListingPhoto.objects.get(pk=listing_photo.pk).thumbnail
    with Image.open(media_root / thumbnail.name) as image:
        assert (image.format, image.mode, image.size) == (image_format, thumbnail_mode, (400, 200))


@pytest.mark.django_db
def test_thumbnail_job_that_loses_a_race_leaves_one_file(seller, media_root, monkeypatch):
    listing_photo = create_listing(seller, [photo((800, 600))]).photos.get()
    encode = services._encode_photo

    def another_run_finishes_first(*args):
        monkeypatch.setattr(services, "_encode_photo", encode)
        tasks.make_photo_thumbnail(photo_id=listing_photo.pk)
        return encode(*args)

    monkeypatch.setattr(services, "_encode_photo", another_run_finishes_first)
    tasks.make_photo_thumbnail(photo_id=listing_photo.pk)

    recorded = ListingPhoto.objects.get(pk=listing_photo.pk).thumbnail.name
    assert [p.relative_to(media_root).as_posix() for p in thumbnail_files(media_root)] == [recorded]
