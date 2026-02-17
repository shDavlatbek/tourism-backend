from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.common.mixins import SlugifyMixin
from apps.common.utils import generate_upload_path
from apps.common.validators import file_size


# ──────────────────────────────────────────────
# City
# ──────────────────────────────────────────────

class City(SlugifyMixin, BaseModel):
    name = models.CharField(max_length=255, verbose_name=_("Nomi"))
    short_description = models.TextField(blank=True, default="", verbose_name=_("Qisqa tavsif"))
    slug = models.SlugField(max_length=255, unique=True, blank=True, allow_unicode=True, verbose_name=_("Slug"))
    order = models.PositiveIntegerField(default=0, db_index=True, verbose_name=_("Tartib"))

    class Meta:
        ordering = ['order']
        verbose_name = _("Shahar")
        verbose_name_plural = _("Shaharlar")

    def __str__(self):
        return self.name


# ──────────────────────────────────────────────
# Village
# ──────────────────────────────────────────────

class Village(SlugifyMixin, BaseModel):
    name = models.CharField(max_length=255, verbose_name=_("Nomi"))
    slug = models.SlugField(max_length=255, unique=True, blank=True, allow_unicode=True, verbose_name=_("Slug"))
    short_description = models.TextField(blank=True, default="", verbose_name=_("Qisqa tavsif"))
    description = models.TextField(blank=True, default="", verbose_name=_("Tavsif"))
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_("Kenglik (lat)"),
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_("Uzunlik (long)"),
    )
    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name='villages', verbose_name=_("Shahar"),
    )
    order = models.PositiveIntegerField(default=0, db_index=True, verbose_name=_("Tartib"))

    class Meta:
        ordering = ['order']
        verbose_name = _("Qishloq")
        verbose_name_plural = _("Qishloqlar")

    def __str__(self):
        return self.name


# ──────────────────────────────────────────────
# Gallery (images for a village)
# ──────────────────────────────────────────────

class Gallery(BaseModel):
    image = models.ImageField(
        upload_to=generate_upload_path,
        validators=[file_size],
        verbose_name=_("Rasm"),
    )
    name = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Nomi"))
    village = models.ForeignKey(
        Village, on_delete=models.CASCADE, related_name='gallery', verbose_name=_("Qishloq"),
    )
    order = models.PositiveIntegerField(default=0, db_index=True, verbose_name=_("Tartib"))

    class Meta:
        ordering = ['order']
        verbose_name = _("Galereya")
        verbose_name_plural = _("Galereya")

    def __str__(self):
        return self.name or f"Image #{self.pk}"


# ──────────────────────────────────────────────
# Comment (for a village)
# ──────────────────────────────────────────────

class Comment(BaseModel):
    village = models.ForeignKey(
        Village, on_delete=models.CASCADE, related_name='comments', verbose_name=_("Qishloq"),
    )
    comment = models.TextField(verbose_name=_("Izoh"))
    full_name = models.CharField(max_length=255, verbose_name=_("To'liq ism"))
    who = models.CharField(
        max_length=255, blank=True, default="",
        verbose_name=_("Kim (kasbi, qishloq aholisi va h.k.)"),
    )
    order = models.PositiveIntegerField(default=0, db_index=True, verbose_name=_("Tartib"))

    class Meta:
        ordering = ['order']
        verbose_name = _("Izoh")
        verbose_name_plural = _("Izohlar")

    def __str__(self):
        return f"{self.full_name}: {self.comment[:50]}"


# ──────────────────────────────────────────────
# MainSettings (singleton)
# ──────────────────────────────────────────────

class MainSettings(BaseModel):
    about_title = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Haqida sarlavha"))
    about_description = models.TextField(blank=True, default="", verbose_name=_("Haqida tavsif"))
    bg_image = models.ImageField(
        upload_to=generate_upload_path,
        blank=True, null=True,
        validators=[file_size],
        verbose_name=_("Fon rasmi"),
    )

    class Meta:
        verbose_name = _("Asosiy sozlamalar")
        verbose_name_plural = _("Asosiy sozlamalar")

    def __str__(self):
        return self.about_title or "Asosiy sozlamalar"

    def save(self, *args, **kwargs):
        # Singleton pattern: always use pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj