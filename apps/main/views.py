from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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
    """List all active villages. Filter by city slug via `?city=<slug>`."""
    serializer_class = serializers.VillageListSerializer

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'city',
                openapi.IN_QUERY,
                description="Filter villages by city slug (e.g. `samarqand`)",
                type=openapi.TYPE_STRING,
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = models.Village.objects.active().select_related('city').order_by('order')
        city_slug = self.request.query_params.get('city')
        if city_slug:
            qs = qs.filter(city__slug=city_slug)
            
        return qs


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

    @swagger_auto_schema(
        responses={200: serializers.MainSettingsSerializer()},
    )
    def get(self, request):
        settings_obj = models.MainSettings.load()
        serializer = serializers.MainSettingsSerializer(settings_obj, context={'request': request})
        return Response(serializer.data)
