from .models import School


def school_for_email(email: str) -> School | None:
    """The active school whose domain exactly matches the email's domain, or None.

    Exact matching means lookalikes ("x@fakeumd.edu") and subdomains ("x@cs.umd.edu")
    don't match unless that exact domain is registered.
    """
    domain = email.rsplit("@", 1)[-1].strip().lower()
    return School.objects.filter(is_active=True, domains__domain=domain).first()
