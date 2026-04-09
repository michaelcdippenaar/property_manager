import io
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from PIL import Image as PilImage

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

from apps.properties.models import PropertyPhoto


class Command(BaseCommand):
    help = "Generate thumbnails for PropertyPhoto records that don't have one yet."

    def handle(self, *args, **options):
        qs = PropertyPhoto.objects.filter(thumbnail='')
        total = qs.count()
        self.stdout.write(f"Found {total} photos without thumbnails.")

        done = 0
        for photo in qs.iterator():
            try:
                photo.photo.open('rb')
                img = PilImage.open(photo.photo)
                img = img.convert("RGB")
                img.thumbnail((400, 400), PilImage.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=72, optimize=True)
                buf.seek(0)

                import os
                base = os.path.splitext(os.path.basename(photo.photo.name))[0]
                photo.thumbnail.save(f"{base}_thumb.jpg", ContentFile(buf.read()), save=True)
                done += 1
                if done % 10 == 0:
                    self.stdout.write(f"  {done}/{total}")
            except Exception as e:
                self.stderr.write(f"  Skipped photo {photo.id}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Done. Generated {done} thumbnails."))
