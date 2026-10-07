from allauth.account.models import EmailAddress
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User

from .models import Conversation, ConversationParticipant, Message
from .serializers import (
    ConversationSerializer,
    MarkReadSerializer,
    MessagePageSerializer,
    MessageQuerySerializer,
    MessageSerializer,
    SendMessageSerializer,
    StartConversationSerializer,
)
from .services import mark_conversation_read, send_message, start_direct_conversation


def conversation_queryset(user):
    return (
        Conversation.objects.filter(participants=user)
        .prefetch_related(
            Prefetch(
                "participant_records",
                queryset=ConversationParticipant.objects.select_related("user__school"),
            ),
            "messages__sender__school",
        )
        .distinct()
    )


class ConversationListCreateView(ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return conversation_queryset(self.request.user)

    @extend_schema(
        request=StartConversationSerializer,
        responses={200: ConversationSerializer, 201: ConversationSerializer},
    )
    def post(self, request):
        payload = StartConversationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        verified_ids = EmailAddress.objects.filter(verified=True).values("user_id")
        recipient = get_object_or_404(
            User.objects.filter(is_active=True, id__in=verified_ids),
            username__iexact=payload.validated_data["username"],
        )
        try:
            conversation = start_direct_conversation(sender=request.user, recipient=recipient)
        except DjangoValidationError as error:
            raise ValidationError({"detail": error.message}) from error
        hydrated = conversation_queryset(request.user).get(pk=conversation.pk)
        return Response(self.get_serializer(hydrated).data)


class ConversationDetailView(RetrieveAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return conversation_queryset(self.request.user)


class ConversationMessageView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    PAGE_SIZE = 50

    def get_conversation(self):
        return get_object_or_404(conversation_queryset(self.request.user), pk=self.kwargs["pk"])

    @extend_schema(parameters=[MessageQuerySerializer], responses=MessagePageSerializer)
    def get(self, request, pk):
        conversation = self.get_conversation()
        query = MessageQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        messages = conversation.messages.select_related("sender__school")
        before_id = query.validated_data.get("before_id")
        after_id = query.validated_data.get("after_id")

        if after_id:
            page = list(messages.filter(id__gt=after_id).order_by("id"))
            has_more = False
        else:
            if before_id:
                messages = messages.filter(id__lt=before_id)
            descending = list(messages.order_by("-id")[: self.PAGE_SIZE + 1])
            has_more = len(descending) > self.PAGE_SIZE
            page = list(reversed(descending[: self.PAGE_SIZE]))

        return Response(
            {
                "messages": MessageSerializer(page, many=True, context={"request": request}).data,
                "has_more": has_more,
            }
        )

    @extend_schema(request=SendMessageSerializer, responses={201: MessageSerializer})
    def post(self, request, pk):
        conversation = self.get_conversation()
        payload = SendMessageSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            message = send_message(
                conversation=conversation,
                sender=request.user,
                body=payload.validated_data["body"],
            )
        except DjangoValidationError as error:
            raise ValidationError({"detail": error.message}) from error
        return Response(MessageSerializer(message, context={"request": request}).data, status=201)


class MarkConversationReadView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MarkReadSerializer

    @extend_schema(responses={204: None})
    def post(self, request, pk):
        conversation = get_object_or_404(conversation_queryset(request.user), pk=pk)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        message = None
        if message_id := payload.validated_data.get("message_id"):
            message = get_object_or_404(Message, pk=message_id)
        try:
            mark_conversation_read(conversation=conversation, user=request.user, message=message)
        except DjangoValidationError as error:
            raise ValidationError({"detail": error.message}) from error
        return Response(status=204)


class UnreadCountView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        count = 0
        for conversation in conversation_queryset(request.user):
            membership = next(
                record
                for record in conversation.participant_records.all()
                if record.user_id == request.user.pk
            )
            messages = conversation.messages.exclude(sender=request.user)
            if membership.last_read_message_id:
                messages = messages.filter(id__gt=membership.last_read_message_id)
            count += messages.count()
        return Response({"unread_count": count})
