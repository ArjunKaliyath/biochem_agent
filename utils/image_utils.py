import base64
from io import BytesIO
from PIL import Image


def encode_image(image_path: str, max_size=(800, 800), quality=80) -> str:
    """Compress and encode an image to base64."""
    with Image.open(image_path) as img:
        img.thumbnail(max_size)
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True, quality=quality)
        return base64.b64encode(buf.getvalue()).decode("utf-8")