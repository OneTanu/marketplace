from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.core.exceptions import ValidationError


def is_allowed_email(email: str) -> bool:
    """True only for an exact allowed domain, so lookalikes such as "x@fakeumd.edu" fail."""
    domain = email.rsplit("@", 1)[-1].strip().lower()
    return domain in settings.TANU_ALLOWED_EMAIL_DOMAINS


class AccountAdapter(DefaultAccountAdapter):
    def clean_email(self, email):
        email = super().clean_email(email)
        if not is_allowed_email(email):
            raise ValidationError(
                "Sign up with your UMD email address (@umd.edu or @terpmail.umd.edu)."
            )
        return email
