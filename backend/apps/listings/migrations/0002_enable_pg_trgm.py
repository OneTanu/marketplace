from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Enable pg_trgm (typo-tolerant text matching) for listing search."""

    dependencies = [("listings", "0001_initial")]

    operations = [TrigramExtension()]
