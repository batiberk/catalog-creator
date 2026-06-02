"""10 ürünlük örnek katalog — MAC LOUNGE Cafe."""

from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

from models.catalog import Catalog, Product, ShopSettings
from paths import ensure_sample_images, sample_images_dir


def _placeholder_image(index: int, label: str) -> str:
    ensure_sample_images()
    img_dir = sample_images_dir()
    path = os.path.join(img_dir, f"urun_{index:02d}.jpg")
    if os.path.isfile(path):
        return path

    w, h = 360, 500
    img = Image.new("RGB", (w, h), (34, 34, 38))
    draw = ImageDraw.Draw(img)
    draw.rectangle([8, 8, w - 9, h - 9], outline=(214, 40, 57), width=3)
    arial = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf")
    try:
        font = ImageFont.truetype(arial, 22)
        small = ImageFont.truetype(arial, 14)
    except OSError:
        font = ImageFont.load_default()
        small = font
    draw.text((w // 2, h // 2 - 10), label, fill=(240, 240, 242), anchor="mm", font=font)
    draw.text((w // 2, h // 2 + 28), f"#{index:02d}", fill=(154, 154, 163), anchor="mm", font=small)
    img.save(path, "JPEG", quality=88)
    return path


def build_sample_catalog() -> Catalog:
    settings = ShopSettings(
        shop_name="MAC LOUNGE Cafe",
        catalog_subtitle="ÜRÜN KATALOĞU 2025",
        cover_title="Nargile Kataloğu",
        cover_subtitle="Premium koleksiyon",
        website="www.maclounge.com",
        phone="+90 555 123 45 67",
    )

    items = [
        ("Sultani Nargile", "El yapımı cam gövde, paslanmaz çelik şişe", "2.450"),
        ("Şark Nargile", "Klasik seri, stabil duman", "1.750"),
        ("Ruby Bowl Set", "Seramik lüle, kömürlük dahil", "890"),
        ("Ice Hose Pro", "Yıkanabilir silikon hortum", "420"),
        ("Premium Kömür 1kg", "Kokusuz, uzun yanma", "180"),
        ("Mango Madness", "Tropikal meyve aroması 50g", "320"),
        ("Double Apple", "Geleneksel çift elma 50g", "280"),
        ("Blue Mist", "Serin nane & böğürtlen", "300"),
        ("Kola Şişesi", "Soğuk içecek 330ml", "65"),
        ("Limonata Ev Yapımı", "Taze sıkım, buzlu", "95"),
    ]

    products: list[Product] = []
    for i, (name, desc, price) in enumerate(items, start=1):
        products.append(
            Product(
                name=name,
                description=desc,
                price=price,
                image_path=_placeholder_image(i, name.split()[0]),
            )
        )

    return Catalog(settings=settings, products=products)
