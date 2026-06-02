"""Katalog içeriği özeti — önizleme önbelleği için."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from models.catalog import Catalog


def catalog_fingerprint(catalog: Catalog) -> str:
    data: dict[str, Any] = catalog.to_dict()
    settings = data.setdefault("settings", {})
    logo = (settings.get("logo_path") or "").strip()
    if logo and os.path.isfile(logo):
        settings["_logo_mtime_ns"] = os.stat(logo).st_mtime_ns
    for product in data.get("products", []):
        path = (product.get("image_path") or "").strip()
        if path and os.path.isfile(path):
            product["_img_mtime_ns"] = os.stat(path).st_mtime_ns
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
