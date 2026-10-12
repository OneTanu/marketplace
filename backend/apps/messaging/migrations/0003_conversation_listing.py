import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0007_seed_category_tree"),
        ("messaging", "0002_remove_message_edited_deleted_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="listing",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="shared_messages",
                to="listings.listing",
            ),
        ),
    ]
