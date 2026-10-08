import pytest
from allauth.account.models import EmailAddress
from django.core.management import CommandError, call_command

from apps.accounts.models import User

LOGIN_URL = "/api/auth/browser/v1/auth/login"
PASSWORD = "a-long-test-password-123"


@pytest.fixture
def debug_on(settings):
    settings.DEBUG = True


def login(client, email, password):
    return client.post(
        LOGIN_URL, {"email": email, "password": password}, content_type="application/json"
    )


@pytest.mark.django_db
def test_creates_a_verified_user_who_can_log_in(client, debug_on):
    call_command("create_verified_user", "Terp@UMD.edu", "--password", PASSWORD)

    user = User.objects.get(email="terp@umd.edu")
    assert user.school.slug == "umd"
    address = EmailAddress.objects.get(user=user)
    assert (address.email, address.verified, address.primary) == ("terp@umd.edu", True, True)
    assert login(client, "terp@umd.edu", PASSWORD).status_code == 200


@pytest.mark.django_db
def test_resets_an_existing_unverified_user(client, debug_on):
    user = User.objects.create_user("terp@umd.edu", "old-password-456", username="terp")
    EmailAddress.objects.create(user=user, email="terp@umd.edu", verified=False, primary=True)

    call_command("create_verified_user", "terp@umd.edu", "--password", PASSWORD)

    assert User.objects.count() == 1
    address = EmailAddress.objects.get(user=user)
    assert address.verified and address.primary
    assert login(client, "terp@umd.edu", "old-password-456").status_code != 200
    assert login(client, "terp@umd.edu", PASSWORD).status_code == 200


@pytest.mark.django_db
def test_rejects_email_not_on_a_school_domain(debug_on):
    with pytest.raises(CommandError, match="not on a domain"):
        call_command("create_verified_user", "terp@gmail.com", "--password", PASSWORD)
    assert not User.objects.exists()


@pytest.mark.django_db
def test_refuses_to_run_without_debug(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError, match="DEBUG"):
        call_command("create_verified_user", "terp@umd.edu", "--password", PASSWORD)
    assert not User.objects.exists()

    call_command(
        "create_verified_user", "terp@umd.edu", "--password", PASSWORD, "--allow-without-debug"
    )
    assert User.objects.filter(email="terp@umd.edu").exists()


@pytest.mark.django_db
def test_refuses_to_reactivate_a_deactivated_account(debug_on):
    User.objects.create_user("terp@umd.edu", "old-password-456", username="terp", is_active=False)
    with pytest.raises(CommandError, match="deactivated"):
        call_command("create_verified_user", "terp@umd.edu", "--password", PASSWORD)
    assert not User.objects.get(email="terp@umd.edu").is_active


@pytest.mark.django_db
def test_refuses_an_email_verified_on_another_account(debug_on):
    owner = User.objects.create_user("owner@umd.edu", "owner-password-456", username="owner")
    EmailAddress.objects.create(user=owner, email="terp@umd.edu", verified=True, primary=False)
    with pytest.raises(CommandError, match="another account"):
        call_command("create_verified_user", "terp@umd.edu", "--password", PASSWORD)
    assert not User.objects.filter(email="terp@umd.edu").exists()


@pytest.mark.django_db
def test_refuses_to_reset_a_staff_account(debug_on):
    User.objects.create_superuser("admin@umd.edu", "admin-password-789", username="admin")
    with pytest.raises(CommandError, match="staff"):
        call_command("create_verified_user", "admin@umd.edu", "--password", PASSWORD)
    assert User.objects.get(email="admin@umd.edu").check_password("admin-password-789")


@pytest.mark.django_db
def test_new_user_gets_a_username(debug_on):
    call_command("create_verified_user", "e2e-student@umd.edu", "--password", PASSWORD)
    call_command(
        "create_verified_user", "second@umd.edu", "--password", PASSWORD, "--username", "terp.two"
    )
    assert User.objects.get(email="e2e-student@umd.edu").username == "e2e_student"
    assert User.objects.get(email="second@umd.edu").username == "terp.two"


@pytest.mark.django_db
def test_taken_username_is_refused(debug_on):
    User.objects.create_user("other@umd.edu", PASSWORD, username="terp")
    with pytest.raises(CommandError, match="taken"):
        call_command("create_verified_user", "terp@umd.edu", "--password", PASSWORD)
