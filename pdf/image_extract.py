"""PDF sayfalarından ürün fotoğraflarını çıkarma."""

from __future__ import annotations

import os
from io import BytesIO

from PIL import Image
from pypdf import PdfReader
from pypdf.generic import IndirectObject

from models.catalog import Catalog

# Küçük simge/çizgi hariç ürün fotoğrafları (dikey veya yatay)
_MIN_SIDE = 80
_MIN_AREA = 18_000  # ~140×130 px


def _image_size(data: bytes) -> tuple[int, int] | None:
    try:
        with Image.open(BytesIO(data)) as img:
            return img.size
    except OSError:
        return None


def _is_product_photo(width: int, height: int) -> bool:
    if width < _MIN_SIDE or height < _MIN_SIDE:
        return False
    return width * height >= _MIN_AREA


def _save_image(data: bytes, dest_dir: str, name: str) -> str | None:
    size = _image_size(data)
    if not size or not _is_product_photo(size[0], size[1]):
        return None
    ext = ".jpg"
    try:
        with Image.open(BytesIO(data)) as img:
            img = img.convert("RGB")
            path = os.path.join(dest_dir, f"{name}.jpg")
            img.save(path, "JPEG", quality=92)
            return path
    except OSError:
        path = os.path.join(dest_dir, f"{name}.bin.jpg")
        try:
            with open(path, "wb") as f:
                f.write(data)
            if _image_size(data):
                return path
        except OSError:
            pass
    return None


def _images_from_page_objects(page, dest_dir: str, prefix: str) -> list[str]:
    paths: list[str] = []
    if hasattr(page, "images"):
        for i, img in enumerate(page.images):
            try:
                saved = _save_image(img.data, dest_dir, f"{prefix}_obj{i + 1:02d}")
                if saved:
                    paths.append(saved)
            except (OSError, AttributeError):
                continue
    return paths


def _images_from_xobjects(page, dest_dir: str, prefix: str) -> list[str]:
    paths: list[str] = []
    try:
        resources = page.get("/Resources")
        if resources is None:
            return paths
        if isinstance(resources, IndirectObject):
            resources = resources.get_object()
        xobjects = resources.get("/XObject")
        if xobjects is None:
            return paths
        if isinstance(xobjects, IndirectObject):
            xobjects = xobjects.get_object()
        for i, key in enumerate(xobjects):
            obj = xobjects[key]
            if isinstance(obj, IndirectObject):
                obj = obj.get_object()
            if obj.get("/Subtype") != "/Image":
                continue
            try:
                data = obj.get_data()
            except (OSError, AttributeError):
                continue
            saved = _save_image(data, dest_dir, f"{prefix}_xo{i + 1:02d}")
            if saved:
                paths.append(saved)
    except (KeyError, TypeError, AttributeError):
        pass
    return paths


def _extract_page_product_images(page, dest_dir: str, prefix: str) -> list[str]:
    seen: set[str] = set()
    paths: list[str] = []
    for batch in (
        _images_from_page_objects(page, dest_dir, prefix),
        _images_from_xobjects(page, dest_dir, prefix),
    ):
        for p in batch:
            if p not in seen:
                seen.add(p)
                paths.append(p)
    return paths


def extract_product_images_from_pdf(reader: PdfReader, dest_dir: str) -> list[str]:
    """
    Kapak (sayfa 0) atlanır; ürün sayfalarındaki dikey fotoğraflar sırayla döner.
    """
    os.makedirs(dest_dir, exist_ok=True)
    all_paths: list[str] = []
    for page_num, page in enumerate(reader.pages):
        if page_num == 0:
            continue
        page_paths = _extract_page_product_images(page, dest_dir, f"p{page_num:02d}")
        all_paths.extend(page_paths)
    return all_paths


def assign_images_to_catalog(catalog: Catalog, image_paths: list[str]) -> int:
    """Eksik görselleri sırayla ürünlere bağlar; eksik kalan ürün sayısını döner."""
    missing = 0
    path_iter = iter(image_paths)
    for product in catalog.products:
        if product.image_path and os.path.isfile(product.image_path):
            continue
        product.image_path = ""
        assigned = False
        while True:
            try:
                candidate = next(path_iter)
            except StopIteration:
                break
            if os.path.isfile(candidate):
                product.image_path = os.path.abspath(candidate)
                assigned = True
                break
        if not assigned:
            missing += 1
    return missing
