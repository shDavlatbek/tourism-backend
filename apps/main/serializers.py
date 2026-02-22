from rest_framework import serializers
from django.conf import settings

from apps.common.imgproxy import build_imgproxy_url
from . import models


class ImgproxyImageField(serializers.ImageField):
    """Serializer field that wraps image URLs through imgproxy."""

    def __init__(self, *args, imgproxy_options=None, **kwargs):
        self.imgproxy_options = imgproxy_options or {}
        self.imgproxy_options.setdefault('format', 'webp')
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        if not value:
            return None

        request = self.context.get('request')
        if request:
            original_url = request.build_absolute_uri(value.url)
        else:
            original_url = value.url

        return {
            'original': original_url,
            'optimized': build_imgproxy_url(f"local:///{value.name}", **self.imgproxy_options),
        }


# ──────────────────────────────────────────────
# City
# ──────────────────────────────────────────────

class CityListSerializer(serializers.ModelSerializer):
    village_count = serializers.IntegerField(source='villages.count', read_only=True)

    class Meta:
        model = models.City
        fields = ('id', 'name', 'slug', 'short_description', 'village_count')


class CityDetailSerializer(serializers.ModelSerializer):
    villages = serializers.SerializerMethodField()

    class Meta:
        model = models.City
        fields = ('id', 'name', 'slug', 'short_description', 'villages')

    def get_villages(self, obj):
        villages = obj.villages.active().order_by('order')
        return VillageListSerializer(villages, many=True, context=self.context).data


# ──────────────────────────────────────────────
# Village
# ──────────────────────────────────────────────

class VillageListSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    image = ImgproxyImageField(imgproxy_options={'quality': 80, 'width': 1200})

    class Meta:
        model = models.Village
        fields = ('id', 'name', 'slug', 'short_description', 'city', 'city_name', 'latitude', 'longitude', 'image', 'seo_tags', 'activities')


class GallerySerializer(serializers.ModelSerializer):
    image = ImgproxyImageField(imgproxy_options={'quality': 60, 'width': 800})

    class Meta:
        model = models.Gallery
        fields = ('id', 'image', 'name')


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Comment
        fields = ('id', 'full_name', 'who', 'comment', 'created_at')


class VillageDetailSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    image = ImgproxyImageField(imgproxy_options={'quality': 90})
    gallery = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = models.Village
        fields = (
            'id', 'name', 'slug', 'short_description', 'description',
            'city', 'city_name', 'latitude', 'longitude',
            'image', 'seo_tags', 'activities',
            'gallery', 'comments',
        )

    def get_gallery(self, obj):
        qs = obj.gallery.active().order_by('order')
        return GallerySerializer(qs, many=True, context=self.context).data

    def get_comments(self, obj):
        qs = obj.comments.active().order_by('order')
        return CommentSerializer(qs, many=True, context=self.context).data


# ──────────────────────────────────────────────
# MainSettings
# ──────────────────────────────────────────────

class MainSettingsSerializer(serializers.ModelSerializer):
    bg_image = ImgproxyImageField(imgproxy_options={'quality': 90})

    class Meta:
        model = models.MainSettings
        fields = ('about_title', 'about_description', 'bg_image')
