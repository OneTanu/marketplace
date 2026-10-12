from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.deals.models import Deal

from .models import Review
from .serializers import ReviewCreateSerializer, ReviewSerializer
from .services import create_review


def deal_for(user, deal_id):
    return get_object_or_404(Deal.objects.filter(Q(buyer=user) | Q(seller=user)), pk=deal_id)


class DealReviewView(GenericAPIView):
    serializer_class = ReviewCreateSerializer

    @extend_schema(responses={200: ReviewSerializer(many=True)})
    def get(self, request, deal_id):
        deal = deal_for(request.user, deal_id)
        reviews = Review.objects.filter(deal=deal).select_related("author", "subject")
        return Response(ReviewSerializer(reviews, many=True).data)

    @extend_schema(responses={201: ReviewSerializer})
    def post(self, request, deal_id):
        deal = deal_for(request.user, deal_id)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            review = create_review(deal=deal, author=request.user, **payload.validated_data)
        except DjangoValidationError as exc:
            if hasattr(exc, "error_dict"):
                raise serializers.ValidationError(exc.message_dict) from exc
            raise serializers.ValidationError({"detail": " ".join(exc.messages)}) from exc
        return Response(
            ReviewSerializer(review).data,
            status=status.HTTP_201_CREATED,
        )
