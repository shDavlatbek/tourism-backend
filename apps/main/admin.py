from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from adminsortable2.admin import SortableAdminMixin
from modeltranslation.admin import TranslationStackedInline, TranslationTabularInline
from modeltranslation import settings as mt_settings

from apps.common.mixins import AdminTranslation
from . import models
from django import forms
import json

class VillageAdminForm(forms.ModelForm):
    activities = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'tagify-input'}),
        help_text=_("Vergul bilan ajratilgan faoliyatlarni kiriting (masalan: hiking, swimming)")
    )
    seo_tags = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'tagify-input'}),
        help_text=_("Vergul bilan ajratilgan SEO taglarni kiriting (masalan: tourism, nature)")
    )

    class Meta:
        model = models.Village
        fields = '__all__'

    class Media:
        css = {
            'all': ('css/tagify.css',)
        }
        js = (
            'js/tagify.min.js',
            'js/admin_tags.js',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Convert list back to comma separated string for the form
            if isinstance(self.instance.activities, list):
                self.initial['activities'] = ', '.join(str(v) for v in self.instance.activities)
            if isinstance(self.instance.seo_tags, list):
                self.initial['seo_tags'] = ', '.join(str(v) for v in self.instance.seo_tags)

    def clean_activities(self):
        data = self.cleaned_data.get('activities', '')
        if not data:
            return []
        # Split by comma and strip whitespace
        return [item.strip() for item in data.split(',') if item.strip()]

    def clean_seo_tags(self):
        data = self.cleaned_data.get('seo_tags', '')
        if not data:
            return []
        return [item.strip() for item in data.split(',') if item.strip()]


class SortableAdminMixinCustom(SortableAdminMixin):
    class Media:
        css = {
            "all": (
                "css/sortable_admin.css",
            ),
        }

# ──────────────────────────────────────────────
# Inlines
# ──────────────────────────────────────────────

class GalleryInline(TranslationStackedInline):
    model = models.Gallery
    extra = 0
    fields = ('order', 'image', 'name', 'is_active')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" style="height:50px;width:50px;object-fit:cover;border-radius:4px;" />'
            )
        return ""
    image_preview.short_description = _("Ko'rish")

    class Media:
        js = (
            "admin/js/jquery.init.js",
            "js/admin_inline.js",
        )


class CommentInline(TranslationStackedInline):
    model = models.Comment
    extra = 0
    fields = ('order', 'full_name', 'who', 'comment', 'is_active')

    class Media:
        js = (
            "admin/js/jquery.init.js",
            "js/admin_inline.js",
        )


# ──────────────────────────────────────────────
# City
# ──────────────────────────────────────────────

@admin.register(models.City)
class CityAdmin(SortableAdminMixinCustom, AdminTranslation):
    list_display = ('name', 'slug', 'is_active')
    list_display_links = ('name',)
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


# ──────────────────────────────────────────────
# Village
# ──────────────────────────────────────────────

@admin.register(models.Village)
class VillageAdmin(SortableAdminMixinCustom, AdminTranslation):
    form = VillageAdminForm
    list_display = ('name', 'city', 'slug', 'image_preview', 'is_active')
    list_display_links = ('name',)
    list_filter = ('is_active', 'city')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [GalleryInline, CommentInline]
    fieldsets = (
        (_('Asosiy'), {
            'fields': ('is_active', 'name', 'slug', 'image', 'short_description', 'description', 'city', 'activities',),
        }),
        (_('SEO'), {
            'fields': ('seo_tags',),
        }),
        (_('Koordinatalar'), {
            'fields': ('latitude', 'longitude',),
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" style="height:50px;width:50px;object-fit:cover;border-radius:4px;"/>'
            )
        return ""
    image_preview.short_description = _("Rasm")


# ──────────────────────────────────────────────
# Gallery
# ──────────────────────────────────────────────

@admin.register(models.Gallery)
class GalleryAdmin(SortableAdminMixinCustom, admin.ModelAdmin):
    list_display = ('name', 'image_preview', 'village', 'is_active')
    list_display_links = ('name',)
    list_filter = ('is_active', 'village__city')
    search_fields = ('name', 'village__name')

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" style="height:50px;width:50px;object-fit:cover;border-radius:4px;"/>'
            )
        return ""
    image_preview.short_description = _("Rasm")


# ──────────────────────────────────────────────
# Comment
# ──────────────────────────────────────────────

@admin.register(models.Comment)
class CommentAdmin(SortableAdminMixinCustom, AdminTranslation):
    list_display = ('full_name', 'village', 'who', 'is_active')
    list_display_links = ('full_name',)
    list_filter = ('is_active', 'village__city')
    search_fields = ('full_name', 'comment', 'village__name')


# ──────────────────────────────────────────────
# MainSettings (singleton)
# ──────────────────────────────────────────────

@admin.register(models.MainSettings)
class MainSettingsAdmin(AdminTranslation):
    list_display = ('about_title', 'updated_at')
    fieldsets = (
        (_('Haqida'), {
            'fields': ('about_title', 'about_description', 'bg_image'),
        }),
    )

    def has_add_permission(self, request):
        # Only one instance allowed
        return not models.MainSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False