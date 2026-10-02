from django.db import migrations

UMD_DOMAINS = ["umd.edu", "terpmail.umd.edu"]


def seed_umd(apps, schema_editor):
    School = apps.get_model("schools", "School")
    SchoolDomain = apps.get_model("schools", "SchoolDomain")
    umd, _ = School.objects.get_or_create(
        slug="umd",
        defaults={"name": "University of Maryland", "short_name": "UMD"},
    )
    for domain in UMD_DOMAINS:
        SchoolDomain.objects.get_or_create(domain=domain, defaults={"school": umd})


class Migration(migrations.Migration):
    dependencies = [("schools", "0001_initial")]

    operations = [migrations.RunPython(seed_umd, migrations.RunPython.noop)]
