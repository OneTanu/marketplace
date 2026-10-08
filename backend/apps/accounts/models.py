import re
from urllib.parse import urlparse

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

instagram_handle_validator = re.compile(r"^[A-Za-z0-9._]{1,30}$")
public_username_validator = RegexValidator(
    regex=r"^[A-Za-z0-9._]+$",
    message="Usernames may contain only letters, numbers, periods, and underscores.",
)


def normalize_instagram_handle(value):
    """Return a bare, lowercase Instagram handle from a handle or profile URL."""
    if value is None:
        return ""
    value = value.strip()
    if not value:
        return ""
    if value.startswith("@"):
        value = value[1:]
    elif "://" in value:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {
            "instagram.com",
            "www.instagram.com",
        }:
            raise ValidationError("Enter a valid Instagram handle or profile URL.")
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) != 1:
            raise ValidationError("Enter a valid Instagram profile URL.")
        value = path_parts[0]
    value = value.strip().rstrip("/").lower()
    if not instagram_handle_validator.fullmatch(value):
        raise ValidationError(
            "Instagram handles may contain only letters, numbers, periods, and underscores."
        )
    return value


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        if not extra_fields.get("username"):
            raise ValueError("Users must have a username")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Tanu user. Signs in with email and has a permanent public username."""

    username = models.CharField(
        max_length=30,
        unique=True,
        validators=[MinLengthValidator(3), public_username_validator],
    )
    email = models.EmailField(unique=True)
    instagram_handle = models.CharField(max_length=30, blank=True)
    profile_description = models.CharField(max_length=300, blank=True)
    # Set from the verified email domain at signup. Null only for staff accounts
    # created outside signup (e.g. createsuperuser).
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
            models.UniqueConstraint(Lower("username"), name="accounts_user_username_ci_unique"),
            models.UniqueConstraint(
                Lower("instagram_handle"),
                condition=~Q(instagram_handle=""),
                name="accounts_user_instagram_ci_unique",
            ),
        ]

    def clean(self):
        # Model forms (the admin) call clean(), so a bad handle becomes a field error there
        # instead of reaching save(), where the same check raises.
        super().clean()
        try:
            self.instagram_handle = normalize_instagram_handle(self.instagram_handle)
        except ValidationError as error:
            raise ValidationError({"instagram_handle": error.messages}) from error

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        self.username = self.username.strip().lower()
        self.instagram_handle = normalize_instagram_handle(self.instagram_handle)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class Follow(models.Model):
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following_relationships",
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower_relationships",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"],
                name="accounts_follow_unique",
            ),
            models.CheckConstraint(
                condition=~Q(follower=models.F("following")),
                name="accounts_follow_not_self",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"
