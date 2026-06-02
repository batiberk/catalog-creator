from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any
import json


@dataclass
class ShopSettings:
    shop_name: str = "MAC LOUNGE Cafe"
    catalog_subtitle: str = "ÜRÜN KATALOĞU 2025"
    cover_title: str = "Nargile Kataloğu"
    cover_subtitle: str = "Premium koleksiyon"
    logo_path: str = ""
    website: str = "www.maclounge.com"
    phone: str = "+90 555 123 45 67"
    products_per_page: int = 2


@dataclass
class Product:
    name: str = ""
    description: str = ""  # kısa tek satır
    price: str = ""
    price_currency: str = "TRY"  # TRY | USD | EUR
    image_path: str = ""
    # Eski projelerle uyumluluk
    category: str = ""
    subtitle: str = ""
    specs: str = ""


@dataclass
class Catalog:
    settings: ShopSettings = field(default_factory=ShopSettings)
    products: list[Product] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "settings": asdict(self.settings),
            "products": [asdict(p) for p in self.products],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Catalog:
        settings_data = dict(data.get("settings", {}))
        if "products_per_page" in settings_data:
            try:
                n = int(settings_data["products_per_page"])
                settings_data["products_per_page"] = max(1, min(4, n))
            except (TypeError, ValueError):
                settings_data["products_per_page"] = 2
        settings = ShopSettings(**settings_data)
        products = [Product(**p) for p in data.get("products", [])]
        return cls(settings=settings, products=products)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> Catalog:
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
