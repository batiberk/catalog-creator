"""Uygulama kapanınca / ayar kaydedince otomatik proje dosyası."""

from __future__ import annotations

import os

from models.catalog import Catalog
from paths import user_data_dir


def autosave_path() -> str:
    return os.path.join(user_data_dir(), "son_proje.macpdf.json")


def load_autosave() -> Catalog | None:
    path = autosave_path()
    if not os.path.isfile(path):
        return None
    try:
        return Catalog.load(path)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save_autosave(catalog: Catalog) -> None:
    catalog.save(autosave_path())
