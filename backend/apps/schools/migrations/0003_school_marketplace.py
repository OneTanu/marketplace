from django.db import migrations, models


def configure_umd(apps, schema_editor):
    School = apps.get_model("schools", "School")
    School.objects.filter(slug="umd").update(
        marketplace_status="open",
        city="College Park",
        state="Maryland",
        country_code="US",
        timezone="America/New_York",
    )


class Migration(migrations.Migration):
    dependencies = [("schools", "0002_seed_umd")]

    operations = [
        migrations.RenameField(
            model_name="school",
            old_name="is_active",
            new_name="signup_is_open",
        ),
        migrations.AlterField(
            model_name="school",
            name="signup_is_open",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="school",
            name="marketplace_status",
            field=models.CharField(
                choices=[
                    ("planned", "Planned"),
                    ("waitlist", "Waitlist"),
                    ("open", "Open"),
                    ("paused", "Paused"),
                ],
                default="planned",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="school",
            name="city",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="school",
            name="state",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="school",
            name="country_code",
            field=models.CharField(default="US", max_length=2),
        ),
        migrations.AddField(
            model_name="school",
            name="timezone",
            field=models.CharField(default="UTC", max_length=64),
        ),
        migrations.AddField(
            model_name="school",
            name="sort_order",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name="school",
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.RunPython(configure_umd, migrations.RunPython.noop),
    ]
