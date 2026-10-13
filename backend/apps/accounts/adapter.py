from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError

from apps.schools.services import school_for_email
from apps.trust.checks import email_is_banned


class AccountAdapter(DefaultAccountAdapter):
    def clean_email(self, email):
        email = super().clean_email(email)
        school = school_for_email(email)
        if school is None:
            raise ValidationError(
                "Sign up with your school email. Tanu may not be at your school yet."
            )
        if email_is_banned(email, school):
            raise ValidationError("This email can't be used to join Tanu.")
        return email

    def save_user(self, request, user, form, commit=True):
        # School is assigned once, at signup. Adding or changing emails later doesn't move
        # a user to another school; that's an admin action.
        user = super().save_user(request, user, form, commit=False)
        user.school = school_for_email(user.email)
        if commit:
            user.save()
        return user
