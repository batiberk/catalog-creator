"""MacPDF ile oluşturulmuş eski PDF'lerden (gömülü veri olmadan) katalog çıkarma."""

from __future__ import annotations

import os
import re

from pypdf import PdfReader

from models.catalog import Catalog, Product, ShopSettings
from pdf.image_extract import assign_images_to_catalog, extract_product_images_from_pdf

_PRICE_RE = re.compile(r"^([₺$€])\s*(.+)$")
_PRODUCT_RE = re.compile(
    r"(?<!\d)(\d{2})\n(.+?)\nFİYAT\n([₺$€]\s*[^\n]+)",
    re.DOTALL,
)
_SYMBOL_TO_CODE = {"₺": "TRY", "$": "USD", "€": "EUR"}


def _parse_price(price_line: str) -> tuple[str, str]:
    line = price_line.strip()
    m = _PRICE_RE.match(line)
    if not m:
        return line, "TRY"
    symbol, amount = m.group(1), m.group(2).strip()
    return amount, _SYMBOL_TO_CODE.get(symbol, "TRY")


def _parse_product_block(index: str, body: str, price_line: str) -> Product:
    lines = [ln.strip() for ln in body.strip().split("\n") if ln.strip()]
    name = lines[0] if lines else f"Ürün {index}"
    description = " ".join(lines[1:]) if len(lines) > 1 else ""
    price, currency = _parse_price(price_line.strip())
    return Product(
        name=name,
        description=description,
        price=price,
        price_currency=currency,
    )


def _parse_cover_settings(lines: list[str]) -> ShopSettings:
    settings = ShopSettings()
    content = [ln.strip() for ln in lines if ln.strip() and not ln.startswith("—")]
    if content:
        settings.cover_title = content[0]
    if len(content) > 1:
        settings.cover_subtitle = content[1]
    if len(content) > 2:
        settings.shop_name = content[2]
    for ln in lines:
        if ln.upper().startswith("WWW.") or "." in ln and " " not in ln:
            settings.website = ln.replace("WWW.", "www.").lower()
            if not settings.website.startswith("www."):
                settings.website = ln
        if ln.startswith("+") or ln.replace(" ", "").replace("-", "").isdigit():
            settings.phone = ln
    return settings


def catalog_from_legacy_pdf(
    pdf_path: str,
    import_assets_dir: str | None = None,
) -> tuple[Catalog, int]:
    reader = PdfReader(pdf_path)
    if len(reader.pages) < 1:
        raise ValueError("PDF boş.")

    if import_assets_dir:
        os.makedirs(import_assets_dir, exist_ok=True)

    all_text_pages: list[str] = []
    for page in reader.pages:
        all_text_pages.append(page.extract_text() or "")

    full = "\n".join(all_text_pages)
    if "FİYAT" not in full and "FIYAT" not in full.upper():
        raise ValueError("MacPDF katalog düzeni tanınamadı.")

    settings = ShopSettings()
    if all_text_pages:
        cover_lines = [ln for ln in all_text_pages[0].split("\n") if ln.strip()]
        settings = _parse_cover_settings(cover_lines)

    for page_text in all_text_pages[1:]:
        for ln in page_text.split("\n"):
            if "KATALO" in ln.upper():
                settings.catalog_subtitle = ln.strip()
                break

    products: list[Product] = []

    for page_text in all_text_pages[1:]:
        for m in _PRODUCT_RE.finditer(page_text):
            products.append(_parse_product_block(m.group(1), m.group(2), m.group(3)))

    if not products:
        raise ValueError("Ürün bulunamadı.")

    catalog = Catalog(settings=settings, products=products)
    missing_images = 0
    if import_assets_dir:
        extracted = extract_product_images_from_pdf(reader, import_assets_dir)
        missing_images = assign_images_to_catalog(catalog, extracted)
    else:
        missing_images = len(products)

    return catalog, missing_images
