import base64
import io
from PIL import Image


def encode_and_compress_image(image_path, max_size=4096, quality=95) -> tuple[str, str]:
    """Resize, compress and base64-encode an image. Returns (b64_str, "jpeg")."""
    with Image.open(image_path) as img:
        img = img.convert("RGB")  # ensure JPEG-compatible
        img.thumbnail((max_size, max_size))

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        buffer.seek(0)

        return base64.b64encode(buffer.read()).decode("utf-8"), "jpeg"
