"""
Profile pictures.

Whatever the browser sends is treated as untrusted: it's decoded with Pillow,
cropped to a square, scaled down to AVATAR_SIZE and re-encoded as a fresh JPEG.
Only that re-encoded copy is stored or served, so a disguised file (a script
renamed .png, an image with hidden metadata or an enormous canvas) never reaches
other users.
"""
import base64
import binascii
import io
import re

from PIL import Image, ImageOps, UnidentifiedImageError

AVATAR_SIZE = 256
MAX_DECODED_BYTES = 2_000_000          # what we'll even try to open
MAX_SOURCE_PIXELS = 25_000_000         # guards against decompression bombs
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
_DATA_URL = re.compile(r"^data:image/(?:jpeg|png|webp);base64,([A-Za-z0-9+/=\s]+)$")

Image.MAX_IMAGE_PIXELS = MAX_SOURCE_PIXELS


class AvatarError(ValueError):
    """The upload can't be used; the message is safe to show to the person."""


def decode_data_url(data_url: str) -> bytes:
    m = _DATA_URL.match(data_url or "")
    if not m:
        raise AvatarError("Please choose a JPG, PNG or WebP image.")
    try:
        raw = base64.b64decode(re.sub(r"\s+", "", m.group(1)), validate=True)
    except (binascii.Error, ValueError):
        raise AvatarError("That image couldn't be read.")
    if not raw:
        raise AvatarError("That image is empty.")
    if len(raw) > MAX_DECODED_BYTES:
        raise AvatarError("That image is too large. Please choose a smaller one.")
    return raw


def process_avatar(raw: bytes) -> bytes:
    """Returns a square AVATAR_SIZE x AVATAR_SIZE JPEG built from the upload."""
    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.format not in ALLOWED_FORMATS:
                raise AvatarError("Please choose a JPG, PNG or WebP image.")
            w, h = img.size
            if w < 32 or h < 32:
                raise AvatarError("That image is too small. Please use one at least 32×32 pixels.")
            if w * h > MAX_SOURCE_PIXELS:
                raise AvatarError("That image is too large. Please choose a smaller one.")
            img.load()
            img = ImageOps.exif_transpose(img)  # respect the phone's rotation flag
            # Flatten any transparency onto white so it doesn't turn black as a JPEG.
            if img.mode in ("RGBA", "LA", "P"):
                rgba = img.convert("RGBA")
                bg = Image.new("RGB", rgba.size, (255, 255, 255))
                bg.paste(rgba, mask=rgba.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
            img = ImageOps.fit(img, (AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS, centering=(0.5, 0.5))
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=86, optimize=True)  # no EXIF is written
            return out.getvalue()
    except AvatarError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise AvatarError("That file doesn't look like a valid image.")


def to_data_url(jpeg: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
