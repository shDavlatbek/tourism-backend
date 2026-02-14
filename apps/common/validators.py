from django.core.exceptions import ValidationError


def file_size(value):
    limit = 5 * 1024 * 1024
    if value.size > limit:
        raise ValidationError("Fayl 5 MB dan katta bo'lishi mumkin emas.")


def file_size_50(value):
    limit = 50 * 1024 * 1024
    if value.size > limit:
        raise ValidationError("Fayl 50 MB dan katta bo'lishi mumkin emas.")