"""PDF sayfalarını önizleme görseline dönüştürme."""

from __future__ import annotations

from PIL import Image

PREVIEW_DPI = 72


def _fitz_doc(pdf_path: str):
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise ImportError(
            "PDF önizleme için PyMuPDF gerekir. Kurulum: pip install pymupdf"
        ) from e
    return fitz.open(pdf_path)


def pdf_page_count(pdf_path: str) -> int:
    doc = _fitz_doc(pdf_path)
    try:
        return len(doc)
    finally:
        doc.close()


def _page_index_to_image(doc, page_index: int, dpi: int) -> Image.Image:
    import fitz

    page = doc[page_index]
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def pdf_page_to_image(pdf_path: str, page_index: int, dpi: int = PREVIEW_DPI) -> Image.Image:
    doc = _fitz_doc(pdf_path)
    try:
        return _page_index_to_image(doc, page_index, dpi)
    finally:
        doc.close()


def pdf_build_preview_meta(
    pdf_path: str, dpi: int = PREVIEW_DPI
) -> tuple[int, Image.Image | None]:
    """Tek dosya açılışıyla sayfa sayısı ve isteğe bağlı ilk sayfa görseli."""
    doc = _fitz_doc(pdf_path)
    try:
        count = len(doc)
        first = _page_index_to_image(doc, 0, dpi) if count > 0 else None
        return count, first
    finally:
        doc.close()


def pdf_to_images(pdf_path: str, dpi: int = PREVIEW_DPI) -> list[Image.Image]:
    """Tüm sayfalar — yalnızca küçük PDF'ler için; önizlemede tek sayfa tercih edin."""
    doc = _fitz_doc(pdf_path)
    try:
        return [_page_index_to_image(doc, i, dpi) for i in range(len(doc))]
    finally:
        doc.close()
