"""Yazılabilir veri klasörleri (Program Files kurulumunda güvenli)."""

from __future__ import annotations

import os
import shutil
import sys


def _project_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def user_data_dir() -> str:
    """Kurulumda LOCALAPPDATA\\MacPDF, geliştirmede proje klasörü."""
    if getattr(sys, "frozen", False):
        base = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "MacPDF",
        )
    else:
        base = _project_root()
    os.makedirs(base, exist_ok=True)
    return base


def sample_images_dir() -> str:
    path = os.path.join(user_data_dir(), "sample")
    os.makedirs(path, exist_ok=True)
    return path


def bundled_sample_dir() -> str | None:
    if getattr(sys, "frozen", False):
        candidate = os.path.join(sys._MEIPASS, "assets", "sample")
        if os.path.isdir(candidate):
            return candidate
    candidate = os.path.join(_project_root(), "assets", "sample")
    return candidate if os.path.isdir(candidate) else None


def ensure_sample_images() -> None:
    """Paketteki örnek görselleri kullanıcı klasörüne kopyalar (bir kez)."""
    src = bundled_sample_dir()
    if not src:
        return
    dst = sample_images_dir()
    for name in os.listdir(src):
        if not name.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        target = os.path.join(dst, name)
        if not os.path.isfile(target):
            shutil.copy2(os.path.join(src, name), target)


def default_pdf_output(name: str) -> str:
    docs = os.path.join(os.path.expanduser("~"), "Documents", "MacPDF")
    os.makedirs(docs, exist_ok=True)
    return os.path.join(docs, name)
