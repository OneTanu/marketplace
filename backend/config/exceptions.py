"""API error responses shared by every app."""

from django.core.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.trust.checks import Restricted


def exception_handler(exc, context):
    """DRF's handler, plus restriction errors that say which restriction applies and until
    when, so the app can explain it instead of showing a bare 403."""
    if isinstance(exc, Restricted):
        until = exc.expires_at.isoformat() if exc.expires_at else None
        return Response({"detail": str(exc), "code": exc.code, "until": until}, status=403)
    if isinstance(exc, PermissionDenied) and str(exc):
        # Services explain refusals ("Only a senior moderator can do this."); keep the reason
        # instead of DRF's generic message.
        return Response({"detail": str(exc)}, status=403)
    return drf_exception_handler(exc, context)
