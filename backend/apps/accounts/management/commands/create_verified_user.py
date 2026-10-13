import re

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.schools.services import school_for_email

# Matches the groups created by trust's 0002_staff_roles migration.
ROLES = {"moderator": "Moderator", "senior-moderator": "Senior moderator"}


class Command(BaseCommand):
    help = (
        "Create or reset a student account with a verified school email, skipping the "
        "verification email. For local development and end-to-end tests only."
    )

    def add_arguments(self, parser):
        parser.add_argument("email", help="Email on a registered school domain, e.g. x@umd.edu.")
        parser.add_argument("--password", required=True, help="Password to set on the account.")
        parser.add_argument(
            "--username",
            help="Public username for a new account. Defaults to the email's local part.",
        )
        parser.add_argument(
            "--role",
            choices=sorted(ROLES),
            help="Also make the account a staff moderator with this role (new accounts only).",
        )
        parser.add_argument(
            "--allow-without-debug",
            action="store_true",
            help="Run even though DEBUG is off. Never use this against production.",
        )

    def handle(self, *args, email, password, username, allow_without_debug, role=None, **options):
        if not settings.DEBUG and not allow_without_debug:
            raise CommandError(
                "Refusing to run with DEBUG off: this command skips email verification. "
                "Pass --allow-without-debug if this really is a test database."
            )

        email = email.strip().lower()
        school = school_for_email(email)
        if school is None:
            raise CommandError(f"{email} is not on a domain registered to an active school.")

        with transaction.atomic():
            user = User.objects.filter(email__iexact=email).first()
            if user is not None and (user.is_staff or user.is_superuser):
                raise CommandError(f"{email} is a staff account; refusing to reset its password.")
            if user is not None and not user.is_active:
                raise CommandError(f"{email} is deactivated; reactivate it in the admin first.")
            other_owner = (
                EmailAddress.objects.filter(email__iexact=email, verified=True)
                .exclude(user=user)
                .exists()
            )
            if other_owner:
                raise CommandError(f"{email} is a verified address of another account.")
            created = user is None
            if created:
                user = User(email=email, username=self._new_username(username, email))
            elif role:
                raise CommandError("--role only applies when creating a new account.")
            user.school = school
            user.set_password(password)
            user.is_staff = bool(role)
            user.save()
            if role:
                user.groups.add(Group.objects.get(name=ROLES[role]))

            EmailAddress.objects.filter(user=user, primary=True).exclude(email=email).update(
                primary=False
            )
            EmailAddress.objects.update_or_create(
                user=user, email=email, defaults={"verified": True, "primary": True}
            )

        action = "Created" if created else "Reset"
        as_role = f" as {ROLES[role]}" if role else ""
        self.stdout.write(
            self.style.SUCCESS(f"{action} verified user {email} ({school}){as_role}.")
        )

    @staticmethod
    def _new_username(username: str | None, email: str) -> str:
        """The given username, or one made from the email's local part ("e2e-student" ->
        "e2e_student"). Usernames are required, validated and unique."""
        if not username:
            username = re.sub(r"[^A-Za-z0-9._]", "_", email.split("@", 1)[0]).ljust(3, "_")[:30]
        try:
            User._meta.get_field("username").run_validators(username)
        except ValidationError as exc:
            raise CommandError(f"Invalid username {username!r}: {' '.join(exc.messages)}") from exc
        if User.objects.filter(username__iexact=username).exists():
            raise CommandError(f"Username {username!r} is taken; pass --username.")
        return username
