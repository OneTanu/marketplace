from django.db import migrations

# Launch item categories. Tickets stays out until the resale decision is made; add it (or
# retire one of these) as data in the admin, not here.
ITEM_CATEGORIES = [
    ("clothing", "Clothing"),
    ("dorm-furniture", "Dorm & furniture"),
    ("electronics", "Electronics"),
    ("textbooks", "Textbooks"),
    ("free", "Free"),  # $0 only; services.FREE_CATEGORY_SLUG
    ("other", "Other"),
]


def seed_item_categories(apps, schema_editor):
    Category = apps.get_model("listings", "Category")
    for slug, name in ITEM_CATEGORIES:
        Category.objects.get_or_create(slug=slug, defaults={"name": name, "kind": "item"})


class Migration(migrations.Migration):
    dependencies = [("listings", "0003_listing_removed_by_removed_at")]

    operations = [migrations.RunPython(seed_item_categories, migrations.RunPython.noop)]
