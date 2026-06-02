"""MacPDF katalog verisini PDF eki olarak gömme / geri okuma."""

from __future__ import annotations

import json
import os
from typing import Any

from pypdf import PdfReader, PdfWriter

from models.catalog import Catalog, Product
from pdf.image_extract import assign_images_to_catalog, extract_product_images_from_pdf
from pdf.legacy_import import catalog_from_legacy_pdf

MACPDF_PROJECT_FILE = "macpdf-project.json"
MACPDF_IMG_PREFIX = "macpdf/images/"
MACPDF_VERSION = 1


class PdfImportError(Exception):
    """PDF içinde düzenlenebilir MacPDF verisi yok."""


def _attachment_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, list) and value and isinstance(value[0], bytes):
        return value[0]
    raise PdfImportError("Ek dosya okunamadı.")


def _prepare_embed_payload(catalog: Catalog) -> tuple[dict[str, Any], list[tuple[str, bytes]]]:
    data = catalog.to_dict()
    data["macpdf_version"] = MACPDF_VERSION
    attachments: list[tuple[str, bytes]] = []

    for i, product in enumerate(data.get("products", [])):
        path = (product.get("image_path") or "").strip()
        if not path or not os.path.isfile(path):
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
            ext = ".jpg"
        embed_name = f"{MACPDF_IMG_PREFIX}{i + 1:04d}{ext}"
        with open(path, "rb") as f:
            attachments.append((embed_name, f.read()))
        product["image_embed"] = embed_name

    return data, attachments


def _supplement_embed_images_from_pages(
    pdf_path: str,
    data: dict[str, Any],
    image_attachments: list[tuple[str, bytes]],
) -> list[tuple[str, bytes]]:
    """Kaynak dosya yoksa PDF sayfalarındaki görselleri ek dosyaya ekler."""
    existing = {name for name, _ in image_attachments}
    products = data.get("products", [])
    need_count = sum(1 for p in products if not p.get("image_embed"))
    if need_count == 0:
        return image_attachments

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        reader = PdfReader(pdf_path)
        paths = extract_product_images_from_pdf(reader, tmp)
        path_iter = iter(paths)
        for i, product in enumerate(products):
            if product.get("image_embed"):
                continue
            try:
                path = next(path_iter)
            except StopIteration:
                break
            ext = os.path.splitext(path)[1].lower() or ".jpg"
            embed_name = f"{MACPDF_IMG_PREFIX}{i + 1:04d}{ext}"
            if embed_name in existing:
                continue
            with open(path, "rb") as f:
                blob = f.read()
            image_attachments.append((embed_name, blob))
            product["image_embed"] = embed_name
            existing.add(embed_name)
    return image_attachments


def embed_catalog_in_pdf(pdf_path: str, catalog: Catalog) -> None:
    """Oluşturulmuş PDF dosyasına proje JSON'u ve ürün görsellerini ekler."""
    payload, image_attachments = _prepare_embed_payload(catalog)
    image_attachments = _supplement_embed_images_from_pages(pdf_path, payload, image_attachments)
    json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    if reader.metadata:
        writer.add_metadata(reader.metadata)

    writer.add_attachment(MACPDF_PROJECT_FILE, json_bytes)
    for name, blob in image_attachments:
        writer.add_attachment(name, blob)

    temp_path = f"{pdf_path}.macpdf.tmp"
    with open(temp_path, "wb") as f:
        writer.write(f)
    os.replace(temp_path, pdf_path)


def _extract_attachments(reader: PdfReader, dest_dir: str) -> dict[str, str]:
    """Ek dosyaları diske yazar; embed adı -> yerel yol."""
    os.makedirs(dest_dir, exist_ok=True)
    mapping: dict[str, str] = {}
    for name, value in reader.attachments.items():
        if name == MACPDF_PROJECT_FILE:
            continue
        if not name.startswith(MACPDF_IMG_PREFIX):
            continue
        blob = _attachment_bytes(value)
        local_name = name.replace("/", os.sep).replace("\\", os.sep)
        local_path = os.path.join(dest_dir, os.path.basename(local_name))
        with open(local_path, "wb") as f:
            f.write(blob)
        mapping[name] = local_path
    return mapping


def _resolve_path(pdf_dir: str, path: str) -> str:
    if not path:
        return ""
    if os.path.isfile(path):
        return path
    candidate = os.path.join(pdf_dir, path)
    if os.path.isfile(candidate):
        return candidate
    candidate = os.path.join(pdf_dir, os.path.basename(path))
    if os.path.isfile(candidate):
        return candidate
    return path


def catalog_from_pdf(
    pdf_path: str,
    import_assets_dir: str | None = None,
) -> tuple[Catalog, int, bool]:
    """
    PDF'den katalog yükler.
    Dönüş: (catalog, eksik_görsel_sayısı, eski_pdf_mi)
    """
    if not os.path.isfile(pdf_path):
        raise PdfImportError("Dosya bulunamadı.")

    reader = PdfReader(pdf_path)
    if MACPDF_PROJECT_FILE not in reader.attachments:
        try:
            if import_assets_dir is None:
                import_assets_dir = os.path.join(
                    os.path.dirname(os.path.abspath(pdf_path)),
                    f".{os.path.splitext(os.path.basename(pdf_path))[0]}_macpdf_assets",
                )
            catalog, missing = catalog_from_legacy_pdf(pdf_path, import_assets_dir)
            return catalog, missing, True
        except ValueError as e:
            raise PdfImportError(
                "Bu PDF'de düzenlenebilir veri yok ve otomatik okuma başarısız.\n"
                f"({e})\n\n"
                "MacPDF ile oluşturulmuş bir katalog PDF'i seçtiğinizden emin olun,\n"
                "veya elinizde .macpdf.json proje dosyası varsa Proje Aç kullanın."
            ) from e

    raw = _attachment_bytes(reader.attachments[MACPDF_PROJECT_FILE])
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise PdfImportError("Proje verisi bozuk.") from e

    pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
    if import_assets_dir is None:
        stem = os.path.splitext(os.path.basename(pdf_path))[0]
        import_assets_dir = os.path.join(
            os.path.dirname(pdf_path),
            f".{stem}_macpdf_assets",
        )
    image_map = _extract_attachments(reader, import_assets_dir)

    products = data.get("products", [])
    for product in products:
        embed_key = product.pop("image_embed", None)
        if embed_key and embed_key in image_map:
            product["image_path"] = image_map[embed_key]
        else:
            product["image_path"] = _resolve_path(pdf_dir, product.get("image_path", ""))
            if product.get("image_path") and not os.path.isfile(product["image_path"]):
                product["image_path"] = ""

    catalog = Catalog.from_dict(data)
    if catalog.settings.logo_path:
        catalog.settings.logo_path = _resolve_path(pdf_dir, catalog.settings.logo_path)
        if not os.path.isfile(catalog.settings.logo_path):
            catalog.settings.logo_path = ""

    # Gömülü ek veya eski yollar yoksa: PDF sayfalarından fotoğrafları çıkar
    os.makedirs(import_assets_dir, exist_ok=True)
    extracted = extract_product_images_from_pdf(reader, import_assets_dir)
    missing_images = assign_images_to_catalog(catalog, extracted)

    return catalog, missing_images, False


def import_assets_dir_for_pdf(pdf_path: str, base_dir: str) -> str:
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    path = os.path.join(base_dir, "pdf_imports", stem)
    os.makedirs(path, exist_ok=True)
    return path
