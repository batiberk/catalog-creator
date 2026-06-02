# PyInstaller spec — Windows için tek klasör paket
# Çalıştır: pyinstaller macpdf.spec

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
root = Path(SPECPATH)

datas = []
datas += collect_data_files("customtkinter")
# Örnek PDF placeholder görselleri pakete dahil
sample_dir = root / "assets" / "sample"
if sample_dir.is_dir():
    datas.append((str(sample_dir), "assets/sample"))

hiddenimports = (
    collect_submodules("reportlab")
    + collect_submodules("pypdf")
    + collect_submodules("pymupdf")
    + [
        "fitz",
        "PIL._tkinter_finder",
        "paths",
        "pdf.image_cache",
        "pdf.catalog_fingerprint",
    ]
)

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MacPDF",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MacPDF",
)
