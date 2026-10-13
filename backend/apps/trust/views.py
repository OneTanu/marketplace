from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response

from apps.accounts.models import User
from apps.errors import service_validation_errors

from . import checks, services
from .models import Block
from .serializers import (
    BlockCreateSerializer,
    BlockedUserSerializer,
    MyRestrictionSerializer,
    ReportCreateSerializer,
    ReportReceiptSerializer,
)


class ReportCreateView(GenericAPIView):
    """Report a listing, profile, message, conversation, deal, or review. The reporter only
    learns that the report was received."""

    serializer_class = ReportCreateSerializer

    @extend_schema(responses={201: ReportReceiptSerializer})
    def post(self, request):
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        with service_validation_errors():
            report = services.create_report(reporter=request.user, **payload.validated_data)
        return Response(ReportReceiptSerializer(report).data, status=status.HTTP_201_CREATED)


class BlockListCreateView(ListAPIView):
    """The students I've blocked, and blocking another one."""

    serializer_class = BlockedUserSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Block.objects.filter(blocker=self.request.user)
            .select_related("blocked")
            .order_by("-created_at", "-id")
        )

    @extend_schema(request=BlockCreateSerializer, responses={201: BlockedUserSerializer})
    def post(self, request):
        payload = BlockCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        blocked = get_object_or_404(User, username__iexact=payload.validated_data["username"])
        with service_validation_errors():
            block = services.block_user(blocker=request.user, blocked=blocked)
        return Response(BlockedUserSerializer(block).data, status=status.HTTP_201_CREATED)


class BlockDeleteView(GenericAPIView):
    serializer_class = BlockedUserSerializer

    @extend_schema(responses={204: None})
    def delete(self, request, username):
        blocked = get_object_or_404(User, username__iexact=username)
        services.unblock_user(blocker=request.user, blocked=blocked)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyRestrictionsView(ListAPIView):
    """My account's active restrictions, so the app can explain what's paused and until when."""

    serializer_class = MyRestrictionSerializer
    pagination_class = None

    def get_queryset(self):
        return checks.active_restrictions(self.request.user).order_by("expires_at")
