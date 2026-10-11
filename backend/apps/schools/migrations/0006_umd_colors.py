from django.db import migrations

UMD_COLORS = ["#E21833", "#FFD200", "#000000"]  # red, gold, black


def set_umd_colors(apps, schema_editor):
    School = apps.get_model("schools", "School")
    School.objects.filter(slug="umd", colors=[]).update(colors=UMD_COLORS)


class Migration(migrations.Migration):
    dependencies = [("schools", "0005_school_colors")]

    operations = [migrations.RunPython(set_umd_colors, migrations.RunPython.noop)]
