from django.db import models


class School(models.Model):
    """A campus on Tanu. Users and listings belong to exactly one school."""

    name = models.CharField(max_length=200)  # "University of Maryland"
    short_name = models.CharField(max_length=50)  # "UMD"
    slug = models.SlugField(unique=True)
    # Inactive schools are known to Tanu but closed to signups (e.g. not launched yet).
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.short_name


class SchoolDomain(models.Model):
    """An email domain that proves membership in a school, e.g. "umd.edu"."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="domains")
    domain = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["domain"]

    def __str__(self):
        return self.domain

    def save(self, *args, **kwargs):
        self.domain = self.domain.strip().lower()
        super().save(*args, **kwargs)
