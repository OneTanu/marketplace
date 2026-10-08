from django.db import migrations

# The launch category tree: departments, each either a leaf or a parent of subcategories.
# Listings go in leaves. Shoes is its own department (not a subcategory of Women and Men), so
# every shoe listing has exactly one category. Change the tree in the admin, not here.
#
# (slug, name, [(child slug suffix, child name), ...]); child slugs are "<department>-<suffix>".
TREE = [
    (
        "women",
        "Women",
        [
            ("tops", "Tops"),
            ("jeans", "Jeans"),
            ("sweaters", "Sweaters"),
            ("skirts", "Skirts"),
            ("dresses", "Dresses"),
            ("coats-jackets", "Coats & Jackets"),
            ("bags", "Bags"),
            ("accessories", "Accessories"),
        ],
    ),
    (
        "men",
        "Men",
        [
            ("t-shirts", "T-shirts"),
            ("shirts", "Shirts"),
            ("jeans", "Jeans"),
            ("pants", "Pants"),
            ("hoodies-sweats", "Hoodies & Sweats"),
            ("coats-jackets", "Coats & Jackets"),
            ("bags", "Bags"),
            ("accessories", "Accessories"),
        ],
    ),
    ("shoes", "Shoes", [("women", "Women's"), ("men", "Men's"), ("unisex", "Unisex")]),
    (
        "accessories",
        "Accessories",
        [
            ("bags", "Bags"),
            ("jewelry", "Jewelry"),
            ("hats", "Hats"),
            ("sunglasses", "Sunglasses"),
            ("belts", "Belts"),
            ("watches", "Watches"),
            ("wallets", "Wallets"),
            ("scarves", "Scarves"),
            ("hair-accessories", "Hair Accessories"),
        ],
    ),
    # Seeded flat by 0004; they stay top-level leaves.
    ("dorm-furniture", "Dorm & furniture", []),
    ("electronics", "Electronics", []),
    ("textbooks", "Textbooks", []),
    ("free", "Free", []),  # $0 only; services.FREE_CATEGORY_SLUG
    ("other", "Other", []),
]

# 0004's flat Clothing category, now split into Women, Men, Shoes and Accessories. It's
# retired rather than deleted, so listings already in it keep their category.
RETIRED = "clothing"


def seed_tree(apps, schema_editor):
    Category = apps.get_model("listings", "Category")
    for department_order, (slug, name, children) in enumerate(TREE, start=1):
        department, _ = Category.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "kind": "item",
                "parent": None,
                "sort_order": department_order * 10,
                "is_active": True,
            },
        )
        for child_order, (suffix, child_name) in enumerate(children, start=1):
            Category.objects.update_or_create(
                slug=f"{slug}-{suffix}",
                defaults={
                    "name": child_name,
                    "kind": "item",
                    "parent": department,
                    "sort_order": child_order,
                    "is_active": True,
                },
            )
    Category.objects.filter(slug=RETIRED).update(is_active=False)


def unseed_tree(apps, schema_editor):
    """Back to 0004's flat list. Fails (PROTECT) if a listing is in a category this created."""
    Category = apps.get_model("listings", "Category")
    created = [slug for slug, _, children in TREE if children]
    created += [f"{slug}-{suffix}" for slug, _, children in TREE for suffix, _ in children]
    Category.objects.filter(parent__slug__in=created).delete()
    Category.objects.filter(slug__in=created).delete()
    Category.objects.filter(slug=RETIRED).update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [("listings", "0006_category_sort_order")]

    operations = [migrations.RunPython(seed_tree, unseed_tree)]
