from modeltranslation.translator import TranslationOptions, register
from . import models


@register(models.City)
class CityTranslation(TranslationOptions):
    fields = ('name', 'short_description')

@register(models.Village)
class VillageTranslation(TranslationOptions):
    fields = ('name', 'short_description', 'description')

@register(models.Comment)
class CommentTranslation(TranslationOptions):
    fields = ('comment', 'full_name', 'who')

@register(models.Gallery)
class GalleryTranslation(TranslationOptions):
    fields = ('name',)

@register(models.MainSettings)
class MainSettingsTranslation(TranslationOptions):
    fields = ('about_title', 'about_description')