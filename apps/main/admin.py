from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from mptt.admin import DraggableMPTTAdmin
from modeltranslation.admin import TranslationTabularInline, TranslationStackedInline
from modeltranslation import settings as mt_settings

from apps.common.mixins import AdminTranslation
from . import models


# ──────────────────────────────────────────────
# Inlines
# ──────────────────────────────────────────────

class GalleryInline(TranslationStackedInline):
    model = models.Gallery
    extra = 1
    fields = ('image', 'name', 'is_active')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" style="height:50px;width:50px;object-fit:cover;border-radius:4px;" />'
            )
        return ""
    image_preview.short_description = _("Ko'rish")


class CommentInline(TranslationStackedInline):
    model = models.Comment
    extra = 0
    fields = ('full_name', 'who', 'comment', 'is_active')

    class Media:
        js = (
            "admin/js/jquery.init.js",
            "modeltranslation/js/force_jquery.js",
            mt_settings.JQUERY_UI_URL,
            "modeltranslation/js/tabbed_translation_fields.js",
        )
        css = {
            "all": (
                "modeltranslation/css/tabbed_translation_fields.css",
                "css/admin_translation.css",
            ),
        }


# ──────────────────────────────────────────────
# City
# ──────────────────────────────────────────────

@admin.register(models.City)
class CityAdmin(AdminTranslation, DraggableMPTTAdmin):
    list_display = ('tree_actions', 'indented_title', 'slug', 'is_active')
    list_display_links = ('indented_title',)
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    exclude = ('parent',)

    class Media:
        css = {
            'screen': ('css/admin_menu.css',),
        }
        
# ──────────────────────────────────────────────
# Village
# ──────────────────────────────────────────────

@admin.register(models.Village)
class VillageAdmin(AdminTranslation, DraggableMPTTAdmin):
    list_display = ('tree_actions', 'indented_title', 'city', 'slug', 'is_active')
    list_display_links = ('indented_title',)
    list_filter = ('is_active', 'city')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    exclude = ('parent',)
    inlines = [GalleryInline, CommentInline]
    fieldsets = (
        (_('Asosiy'), {
            'fields': ('name', 'slug', 'short_description', 'description', 'city', 'is_active'),
        }),
        (_('Koordinatalar'), {
            'fields': ('latitude', 'longitude'),
        }),
    )

    class Media:
        css = {
            'screen': ('css/admin_menu.css',),
        }


# ──────────────────────────────────────────────
# Gallery
# ──────────────────────────────────────────────

@admin.register(models.Gallery)
class GalleryAdmin(DraggableMPTTAdmin):
    list_display = ('tree_actions', 'indented_title', 'image_preview', 'village', 'is_active')
    list_display_links = ('indented_title',)
    list_filter = ('is_active', 'village__city')
    search_fields = ('name', 'village__name')
    exclude = ('parent',)

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
class CommentAdmin(AdminTranslation, DraggableMPTTAdmin):
    list_display = ('tree_actions', 'indented_title', 'village', 'who', 'is_active')
    list_display_links = ('indented_title',)
    list_filter = ('is_active', 'village__city')
    search_fields = ('full_name', 'comment', 'village__name')
    exclude = ('parent',)


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