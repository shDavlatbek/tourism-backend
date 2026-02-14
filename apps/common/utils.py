import os
from uuid import uuid4

from django.core.files.storage import default_storage
from django.utils import timezone, dateformat


def generate_upload_path(instance, filename: str) -> str:
    """
    <app>/<model>/<Y/m/d>/<filename>   (adds -<8-char-uuid> *only* if a clash)
    """
    app_label = instance._meta.app_label
    model_name = instance._meta.model_name
    today = dateformat.format(timezone.now(), "Y/m/d")

    name, ext = os.path.splitext(filename)
    base_dir = f"{app_label}/{model_name}/{today}"

    candidate = f"{base_dir}/{name}{ext.lower()}"
    while default_storage.exists(candidate):
        candidate = f"{base_dir}/{name}-{uuid4().hex[:8]}{ext.lower()}"

    return candidate
