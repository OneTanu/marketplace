"""Staff roles are Django groups, so superusers assign them in /admin like any permission."""

from django.db import migrations

ROLES = ["Moderator", "Senior moderator", "School administrator"]


def create_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ROLES:
        Group.objects.get_or_create(name=name)


def remove_roles(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=ROLES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("trust", "0001_moderation_foundation"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(create_roles, remove_roles)]
