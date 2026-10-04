from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_user_profile_identity"),
    ]

    operations = [
        migrations.CreateModel(
            name="Follow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("follower", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="following_relationships", to=settings.AUTH_USER_MODEL)),
                ("following", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="follower_relationships", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="follow",
            constraint=models.UniqueConstraint(fields=("follower", "following"), name="accounts_follow_unique"),
        ),
        migrations.AddConstraint(
            model_name="follow",
            constraint=models.CheckConstraint(condition=~models.Q(("follower", models.F("following"))), name="accounts_follow_not_self"),
        ),
    ]
