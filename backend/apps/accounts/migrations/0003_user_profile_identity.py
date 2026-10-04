import re

import django.core.validators
import django.db.models.functions.text
from django.db import migrations, models
from django.db.models import Q


def populate_usernames(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    used = set()
    for user in User.objects.order_by("pk"):
        base = re.sub(r"[^a-z0-9._]", "", user.email.split("@", 1)[0].lower())[:30]
        if len(base) < 3:
            base = f"user{user.pk}"
        candidate = base
        suffix = 2
        while candidate.lower() in used or User.objects.filter(username__iexact=candidate).exists():
            suffix_text = str(suffix)
            candidate = f"{base[: 30 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        user.username = candidate
        user.save(update_fields=["username"])
        used.add(candidate.lower())


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_user_school")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="instagram_handle",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="user",
            name="profile_description",
            field=models.CharField(blank=True, max_length=300),
        ),
        migrations.AddField(
            model_name="user",
            name="username",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.RunPython(populate_usernames, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(
                max_length=30,
                unique=True,
                validators=[
                    django.core.validators.MinLengthValidator(3),
                    django.core.validators.RegexValidator(
                        message=(
                            "Usernames may contain only letters, numbers, periods, and underscores."
                        ),
                        regex="^[A-Za-z0-9._]+$",
                    ),
                ],
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("username"),
                name="accounts_user_username_ci_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("instagram_handle"),
                condition=~Q(instagram_handle=""),
                name="accounts_user_instagram_ci_unique",
            ),
        ),
    ]
