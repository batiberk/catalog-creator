"""Ürün görselleri için PDF üretim önbelleği."""

from __future__ import annotations

import os
from io import BytesIO

from PIL import Image as PILImage
from reportlab.lib.utils import ImageReader

# (path, mtime_ns, max_w, max_h) -> (jpeg_bytes, iw, ih)
_fit_cache: dict[tuple[str, int, int, int], tuple[bytes, float, float]] = {}


def _cache_key(path: str, max_w: float, max_h: float) -> tuple[str, int, int, int] | None:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (path, st.st_mtime_ns, round(max_w), round(max_h))


def fit_image_cached(
    path: str, max_w: float, max_h: float
) -> tuple[ImageReader, float, float] | None:
    if not path or not os.path.isfile(path):
        return None
    key = _cache_key(path, max_w, max_h)
    if key is None:
        return None

    cached = _fit_cache.get(key)
    if cached is None:
        try:
            with PILImage.open(path) as img:
                img = img.convert("RGB")
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=90)
                jpeg = buf.getvalue()
            reader = ImageReader(BytesIO(jpeg))
            iw, ih = reader.getSize()
            _fit_cache[key] = (jpeg, float(iw), float(ih))
        except OSError:
            return None
    else:
        jpeg, iw, ih = cached

    scale = min(max_w / iw, max_h / ih)
    reader = ImageReader(BytesIO(jpeg))
    return reader, iw * scale, ih * scale
