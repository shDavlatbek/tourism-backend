"""
Management command to import tourism villages data from Excel + images from mat/ folder.

Usage:
    python manage.py import_villages
    python manage.py import_villages --excel path/to/file.xlsx --mat path/to/mat
    python manage.py import_villages --flush  (delete all existing data first)
"""

import io
import os
import re
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

import openpyxl
from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_SUPPORT = True
except ImportError:
    HEIF_SUPPORT = False

from apps.main.models import City, Village, Gallery


# ── 12 Uzbekistan regions (uz names) ────────────────────────────────
ALL_REGIONS = [
    "Andijon",
    "Buxoro",
    "Farg'ona",
    "Jizzax",
    "Namangan",
    "Navoiy",
    "Qashqadaryo",
    "Samarqand",
    "Sirdaryo",
    "Surxondaryo",
    "Toshkent",
    "Xorazm",
]

# ── Mapping: Excel region name → mat/ folder name ──────────────────
REGION_FOLDER_MAP = {
    "Andijon":      "Andijon",
    "Buxoro":       "Bukhara",
    "Farg'ona":     "Fergana",
    "Jizzax":       "JIZZAX",
    "Namangan":     "Namangan",
    "Navoiy":       "Navoiy",
    "Qashqadaryo":  "Qashqadaryo",
    "Samarqand":    "Samarkand",
    "Surxondaryo":  "Surxondaryo",
    "Toshkent":     "Tashkent region",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}


def _normalize(name: str) -> str:
    """
    Normalize a name for fuzzy matching:
    lowercase, strip whitespace, remove common suffixes, collapse non-alnum.
    """
    s = name.lower().strip()
    # remove common suffixes like "turizm qishlog'i", "turizm mahallasi"
    for suffix in ["turizm qishlog'i", "turizm mahallasi", "turizm qishlog'i", "etno turizm qishlog'i"]:
        s = s.replace(suffix, "")
    s = s.strip()
    # collapse non-alphanumeric to single space
    s = re.sub(r"[^a-z0-9\u0400-\u04ff\u00e0-\u024f'ʼ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_location(loc_str: str):
    """
    Parse location string into (lat, lng) or (None, None).
    Handles formats like:
      '40.546597, 72.608740'
      '39°39'59"N, 67°02'02"E'
      'Denov tumani, "Sina" MFY'  → (None, None)
    """
    if not loc_str or not isinstance(loc_str, str):
        return None, None

    # Try simple decimal: "40.546597, 72.608740"
    decimal_match = re.match(
        r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", loc_str
    )
    if decimal_match:
        lat, lng = float(decimal_match.group(1)), float(decimal_match.group(2))
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return lat, lng

    # Try DMS: 39°39'59"N, 67°02'02"E
    dms_pattern = r"""(\d+)[°]\s*(\d+)[''′]\s*(\d+(?:\.\d+)?)[""″]?\s*([NSns])"""
    parts = re.findall(dms_pattern, loc_str)
    if len(parts) == 2:
        def dms_to_decimal(d, m, s, direction):
            dec = float(d) + float(m) / 60 + float(s) / 3600
            if direction.upper() in ("S", "W"):
                dec = -dec
            return dec

        lat = dms_to_decimal(*parts[0])
        lng = dms_to_decimal(*parts[1])
        return lat, lng

    return None, None


def _convert_to_jpg(image_path: Path) -> tuple[bytes, str]:
    """
    Read an image file and return (jpeg_bytes, filename_with_jpg_ext).
    Converts HEIC/HEIF to JPEG. For JPEG/PNG, re-saves as JPEG for consistency.
    """
    img = Image.open(image_path)
    img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    new_name = image_path.stem + ".jpg"
    return buf.getvalue(), new_name


def _find_village_folder(region_dir: Path, village_name: str):
    """
    Find the best matching subdirectory in region_dir for a village name.
    Uses normalized fuzzy matching.
    """
    if not region_dir.is_dir():
        return None

    target = _normalize(village_name)
    best_match = None
    best_score = 0

    for sub in region_dir.iterdir():
        if not sub.is_dir():
            continue
        folder_norm = _normalize(sub.name)

        # Exact match
        if folder_norm == target:
            return sub

        # Check if one contains the other
        if target in folder_norm or folder_norm in target:
            score = len(folder_norm) + len(target)
            if score > best_score:
                best_score = score
                best_match = sub

    return best_match


def _get_image_files(folder: Path) -> list[Path]:
    """
    Collect all image files from a folder (non-recursive), sorted by name.
    """
    if not folder or not folder.is_dir():
        return []
    return sorted(
        f
        for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )


class Command(BaseCommand):
    help = "Import tourism villages from Excel + images from mat/ folder"

    def add_arguments(self, parser):
        parser.add_argument(
            "--excel",
            default=str(settings.BASE_DIR / "Uzbekistan_Tourism_Villages_3lang_FULL (2).xlsx"),
            help="Path to the Excel file",
        )
        parser.add_argument(
            "--mat",
            default=str(settings.BASE_DIR / "mat"),
            help="Path to the mat/ folder with images",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing City, Village, Gallery data before importing",
        )

    def handle(self, *args, **options):
        excel_path = Path(options["excel"])
        mat_path = Path(options["mat"])

        if not excel_path.exists():
            self.stderr.write(self.style.ERROR(f"Excel file not found: {excel_path}"))
            return

        if options["flush"]:
            self.stdout.write("Flushing existing data...")
            Gallery.objects.all().delete()
            Village.objects.all().delete()
            City.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("  Flushed."))

        # ── Step 1: Create 12 regions ───────────────────────────────
        self.stdout.write("\n── Creating 12 regions ──")
        city_map = {}
        for idx, region_name in enumerate(ALL_REGIONS, start=1):
            city, created = City.objects.get_or_create(
                name_uz=region_name,
                defaults={"name": region_name, "order": idx},
            )
            city_map[region_name] = city
            status = "CREATED" if created else "EXISTS"
            self.stdout.write(f"  [{status}] {region_name} (id={city.pk})")

        # ── Step 2: Parse Excel ─────────────────────────────────────
        self.stdout.write("\n── Importing villages from Excel ──")
        wb = openpyxl.load_workbook(str(excel_path), read_only=True)
        ws = wb["Tourism_Villages_3lang"]

        village_count = 0
        gallery_count = 0

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            region = row[0]
            village_name = row[1]
            if not region or not village_name:
                continue

            desc_uz = row[2] or ""
            desc_ru = row[3] or ""
            desc_en = row[4] or ""
            act_uz = row[5] or ""
            act_ru = row[6] or ""
            act_en = row[7] or ""
            location = row[8] or ""

            # Parse activities into structured list
            activities = []
            act_uz_list = [a.strip() for a in act_uz.split(";") if a.strip()]
            act_ru_list = [a.strip() for a in act_ru.split(";") if a.strip()]
            act_en_list = [a.strip() for a in act_en.split(";") if a.strip()]
            max_len = max(len(act_uz_list), len(act_ru_list), len(act_en_list))
            for i in range(max_len):
                activities.append({
                    "uz": act_uz_list[i] if i < len(act_uz_list) else "",
                    "ru": act_ru_list[i] if i < len(act_ru_list) else "",
                    "en": act_en_list[i] if i < len(act_en_list) else "",
                })

            lat, lng = _parse_location(location)

            # Normalize apostrophes (Excel may use Unicode RIGHT SINGLE QUOTATION MARK)
            region = region.replace("\u2018", "'").replace("\u2019", "'").replace("\u02bc", "'")

            # Find city
            city = city_map.get(region)
            if not city:
                self.stderr.write(self.style.WARNING(
                    f"  Row {row_idx}: Unknown region '{region}', skipping."
                ))
                continue

            # Create village
            village, created = Village.objects.get_or_create(
                name_uz=village_name,
                city=city,
                defaults={
                    "name": village_name,
                    "description_uz": desc_uz,
                    "description_ru": desc_ru,
                    "description_en": desc_en,
                    "latitude": lat,
                    "longitude": lng,
                    "activities": activities,
                    "order": row_idx - 1,
                },
            )

            if not created:
                # Update fields if village already exists
                village.description_uz = desc_uz
                village.description_ru = desc_ru
                village.description_en = desc_en
                village.latitude = lat
                village.longitude = lng
                village.activities = activities
                village.save()

            village_count += 1
            status = "CREATED" if created else "UPDATED"
            self.stdout.write(f"  [{status}] {region} → {village_name}")

            # ── Step 3: Import images ───────────────────────────────
            region_folder_name = REGION_FOLDER_MAP.get(region)
            if not region_folder_name:
                continue

            region_dir = mat_path / region_folder_name
            village_folder = _find_village_folder(region_dir, village_name)
            images = _get_image_files(village_folder)

            if not images:
                self.stdout.write(
                    self.style.WARNING(f"    No images found for '{village_name}'")
                )
                continue

            # Clear existing gallery for this village to avoid duplicates on re-run
            old_gallery_count = village.gallery.count()
            if old_gallery_count:
                village.gallery.all().delete()
                self.stdout.write(f"    Cleared {old_gallery_count} old gallery images")

            for img_idx, img_path in enumerate(images):
                try:
                    jpg_bytes, jpg_name = _convert_to_jpg(img_path)
                    content = ContentFile(jpg_bytes, name=jpg_name)

                    if img_idx == 0 and not village.image:
                        # First image → village main image
                        village.image.save(jpg_name, content, save=True)
                        self.stdout.write(f"    → Main image: {img_path.name}")
                    else:
                        # Remaining → gallery
                        Gallery.objects.create(
                            village=village,
                            image=content,
                            name=img_path.stem,
                            order=img_idx,
                        )
                        gallery_count += 1
                        self.stdout.write(f"    → Gallery #{img_idx}: {img_path.name}")

                except Exception as e:
                    self.stderr.write(self.style.ERROR(
                        f"    ✗ Error processing {img_path.name}: {e}"
                    ))

        wb.close()

        # ── Summary ─────────────────────────────────────────────────
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(
            f"Done! Cities: {City.objects.count()}, "
            f"Villages: {village_count}, "
            f"Gallery images: {gallery_count}"
        ))
