from contextlib import contextmanager

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError


@contextmanager
def service_validation_errors():
    """Turn a service's Django ValidationError into a DRF one (a 400). Field errors stay keyed
    by field ({"instagram_handle": [...]}); any other error becomes {"detail": "..."}."""
    try:
        yield
    except DjangoValidationError as error:
        if hasattr(error, "error_dict"):
            raise ValidationError(error.message_dict) from error
        raise ValidationError({"detail": " ".join(error.messages)}) from error
