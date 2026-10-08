from django.db.models import Count, F, OuterRef, Prefetch, Q, Subquery
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.services import verified_users
from apps.errors import service_validation_errors

from .models import Conversation, ConversationParticipant, Message
from .serializers import (
    ConversationSerializer,
    MarkReadSerializer,
    MessagePageSerializer,
    MessageQuerySerializer,
    MessageSerializer,
    SendMessageSerializer,
    StartConversationSerializer,
    UnreadCountSerializer,
)
from .services import mark_conversation_read, send_message, start_direct_conversation


def my_conversations(user):
    return Conversation.objects.filter(participant_records__user=user)


def unread_messages(user):
    """Counts, over my_conversations(user), the messages from others after the user's last read
    message (all of them if nothing is read yet). The F() reuses my_conversations()' participant
    join, so it reads the user's own read position, not the other student's."""
    after_last_read = Q(participant_records__last_read_message__isnull=True) | Q(
        messages__id__gt=F("participant_records__last_read_message_id")
    )
    return Count("messages", filter=~Q(messages__sender=user) & after_last_read)


def conversation_queryset(user):
    """The user's conversations, ready for ConversationSerializer in a fixed number of queries:
    unread counts are annotated, and only each conversation's latest message is prefetched."""
    latest_id = Message.objects.filter(conversation=OuterRef("pk")).order_by("-id").values("id")
    latest_ids = my_conversations(user).annotate(latest_id=Subquery(latest_id[:1]))
    return (
        my_conversations(user)
        .annotate(unread_count=unread_messages(user))
        # Restated because Django drops Meta.ordering from GROUP BY queries.
        .order_by(*Conversation._meta.ordering)
        .prefetch_related(
            Prefetch(
                "participant_records",
                queryset=ConversationParticipant.objects.select_related(
                    "user__school"
                ).prefetch_related("user__school__domains"),
            ),
            Prefetch(
                "messages",
                queryset=Message.objects.filter(id__in=latest_ids.values("latest_id"))
                .select_related("sender__school")
                .prefetch_related("sender__school__domains"),
                to_attr="latest_messages",
            ),
        )
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
        recipient = get_object_or_404(
            verified_users(), username__iexact=payload.validated_data["username"]
        )
        with service_validation_errors():
            conversation = start_direct_conversation(sender=request.user, recipient=recipient)
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
        return get_object_or_404(my_conversations(self.request.user), pk=self.kwargs["pk"])

    @extend_schema(parameters=[MessageQuerySerializer], responses=MessagePageSerializer)
    def get(self, request, pk):
        conversation = self.get_conversation()
        query = MessageQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        messages = conversation.messages.select_related("sender__school").prefetch_related(
            "sender__school__domains"
        )
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
        with service_validation_errors():
            message = send_message(
                conversation=conversation,
                sender=request.user,
                body=payload.validated_data["body"],
            )
        return Response(MessageSerializer(message, context={"request": request}).data, status=201)


class MarkConversationReadView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MarkReadSerializer

    @extend_schema(responses={204: None})
    def post(self, request, pk):
        conversation = get_object_or_404(my_conversations(request.user), pk=pk)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        message = None
        if message_id := payload.validated_data.get("message_id"):
            message = get_object_or_404(Message, pk=message_id)
        with service_validation_errors():
            mark_conversation_read(conversation=conversation, user=request.user, message=message)
        return Response(status=204)


class UnreadCountView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UnreadCountSerializer)
    def get(self, request):
        totals = my_conversations(request.user).aggregate(
            unread_count=unread_messages(request.user)
        )
        return Response(totals)
