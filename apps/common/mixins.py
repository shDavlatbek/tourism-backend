from django.utils.text import slugify
from modeltranslation.admin import TabbedTranslationAdmin


class SlugifyMixin:
    """Auto-populate slug from a source field on first save."""
    slug_field = 'slug'
    slug_source = 'name'

    def save(self, *args, **kwargs):
        if not getattr(self, self.slug_field):
            source_value = getattr(self, self.slug_source)
            setattr(self, self.slug_field, slugify(source_value, allow_unicode=True))
        return super().save(*args, **kwargs)


class AdminTranslation(TabbedTranslationAdmin):
    class Media:
        css = {
            "all": ("css/admin_translation.css",),
        }