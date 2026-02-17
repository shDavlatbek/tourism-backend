from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from . import models, serializers


# ──────────────────────────────────────────────
# City
# ──────────────────────────────────────────────

class CityListView(ListAPIView):
    """List all active cities ordered by position."""
    serializer_class = serializers.CityListSerializer

    def get_queryset(self):
        return models.City.objects.active().order_by('order')


class CityDetailView(RetrieveAPIView):
    """Retrieve a city by slug, including its villages."""
    serializer_class = serializers.CityDetailSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return models.City.objects.active()


# ──────────────────────────────────────────────
# Village
# ──────────────────────────────────────────────

class VillageListView(ListAPIView):
    """List all active villages. Filter by `city` query param."""
    serializer_class = serializers.VillageListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['city']

    def get_queryset(self):
        return models.Village.objects.active().select_related('city').order_by('order')


class VillageDetailView(RetrieveAPIView):
    """Retrieve a village by slug, including gallery and comments."""
    serializer_class = serializers.VillageDetailSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return models.Village.objects.active().select_related('city')


# ──────────────────────────────────────────────
# MainSettings
# ──────────────────────────────────────────────

class MainSettingsView(APIView):
    """Retrieve singleton site settings."""

    def get(self, request):
        settings_obj = models.MainSettings.load()
        serializer = serializers.MainSettingsSerializer(settings_obj, context={'request': request})
        return Response(serializer.data)
