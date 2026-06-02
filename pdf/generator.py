from __future__ import annotations

import os

from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from models.catalog import Catalog, Product, ShopSettings
from models.currency import format_price_display
from pdf.catalog_embed import embed_catalog_in_pdf
from pdf.image_cache import fit_image_cached
from pdf.layout import (
    CONTENT_W,
    MARGIN,
    PAGE_H,
    PAGE_W,
    PageLayout,
    clamp_products_per_page,
    compute_layout,
)

FONT_BODY = "Helvetica"
FONT_TITLE = "Helvetica-Bold"

_win_fonts = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
_arial = os.path.join(_win_fonts, "arial.ttf")
_arial_bold = os.path.join(_win_fonts, "arialbd.ttf")
if os.path.isfile(_arial):
    pdfmetrics.registerFont(TTFont("AppArial", _arial))
    FONT_BODY = "AppArial"
if os.path.isfile(_arial_bold):
    pdfmetrics.registerFont(TTFont("AppArialBold", _arial_bold))
    FONT_TITLE = "AppArialBold"

BG = colors.HexColor("#1A1A1C")
CARD = colors.HexColor("#222224")
BORDER = colors.HexColor("#3D3D42")
TEXT = colors.HexColor("#F2F2F4")
TEXT_MUTED = colors.HexColor("#9A9AA3")
ACCENT = colors.HexColor("#D62839")
ACCENT_SOFT = colors.HexColor("#2E181C")

IMG_AREA_RATIO = 0.60
TEXT_AREA_RATIO = 0.38
DESC_PRICE_GAP = 18 * 72 / 96
LABEL_AMOUNT_GAP = 6 * 72 / 96
PRICE_LABEL_SIZE = 9.0


def _fit_image(path: str, max_w: float, max_h: float) -> tuple[ImageReader, float, float] | None:
    return fit_image_cached(path, max_w, max_h)


def _draw_page_bg(c: canvas.Canvas) -> None:
    c.setFillColor(BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)


def _draw_hline(c: canvas.Canvas, y: float, accent: bool = False, *, product_divider: bool = False) -> None:
    if accent:
        c.setStrokeColor(ACCENT)
        c.setLineWidth(0.6)
    elif product_divider:
        c.setStrokeColor(TEXT_MUTED)
        c.setLineWidth(0.55)
    else:
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.4)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)


def _draw_footer(c: canvas.Canvas, settings: ShopSettings, page_num: int, total: int) -> None:
    from pdf.layout import FOOTER_H
    from reportlab.lib.units import mm

    y = MARGIN
    _draw_hline(c, y + FOOTER_H)
    c.setFillColor(TEXT_MUTED)
    c.setFont(FONT_BODY, 7)
    c.drawString(MARGIN, y + 2.5 * mm, settings.website.upper())
    c.drawCentredString(PAGE_W / 2, y + 2.5 * mm, f"— {page_num:02d} —")
    c.drawRightString(PAGE_W - MARGIN, y + 2.5 * mm, settings.phone)


def _draw_header(c: canvas.Canvas, settings: ShopSettings) -> float:
    from pdf.layout import HEADER_H
    from reportlab.lib.units import mm

    top = PAGE_H - MARGIN
    c.setFillColor(ACCENT)
    c.setFont(FONT_TITLE, 18)
    c.drawString(MARGIN, top - 7 * mm, settings.shop_name.upper())
    c.setFillColor(TEXT_MUTED)
    c.setFont(FONT_BODY, 8)
    c.drawRightString(PAGE_W - MARGIN, top - 6 * mm, settings.catalog_subtitle.upper())
    line_y = top - HEADER_H
    _draw_hline(c, line_y, accent=True)
    return line_y - 5 * mm


def _font_ascent_descent(font: str, size: float) -> tuple[float, float]:
    from reportlab.pdfbase.pdfmetrics import getAscent, getDescent

    return getAscent(font, size), getDescent(font, size)


def _wrap_text(text: str, font: str, size: float, max_w: float, max_lines: int = 2) -> list[str]:
    from reportlab.pdfbase.pdfmetrics import stringWidth

    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if stringWidth(trial, font, size) <= max_w:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines[:max_lines]


def _title_lines(name: str, max_w: float, base_size: float, max_lines: int = 2) -> tuple[list[str], float]:
    clean = " ".join((name or "Ürün adı").split())
    size = base_size
    min_size = max(8.5, base_size * 0.58)
    lines = _wrap_text(clean, FONT_TITLE, size, max_w, max_lines=max_lines)
    while size > min_size:
        normalized = " ".join(" ".join(lines).split())
        if normalized == clean:
            break
        size -= 0.5
        lines = _wrap_text(clean, FONT_TITLE, size, max_w, max_lines=max_lines)
    return lines, size


def _title_right_overflow(name: str, max_w: float, base_size: float) -> float:
    """Başlık 2 satıra ve güvenli puntoya rağmen sığmıyorsa taşan genişliği döndür."""
    from reportlab.pdfbase.pdfmetrics import stringWidth

    lines, size = _title_lines(name, max_w, base_size, max_lines=2)
    if not lines:
        return 0.0
    widest = max(stringWidth(line, FONT_TITLE, size) for line in lines)
    return max(0.0, widest - max_w)


def _draw_image_frame(
    c: canvas.Canvas,
    layout: PageLayout,
    x: float,
    y: float,
    w: float,
    img_h: float,
    index: int,
    image_path: str,
    align_left: bool,
) -> tuple[float, float]:
    from reportlab.lib.units import mm

    pad = 0.8 * mm
    inner_w, inner_h = w - 2 * pad, img_h - 2 * pad
    result = _fit_image(image_path, inner_w, inner_h)
    if result:
        reader, dw, dh = result
        is_portrait = dh > dw * 1.1
        is_landscape = dw > dh * 1.1
        if is_portrait and layout.products_per_page == 1:
            ix = x + pad + (inner_w - dw) / 2
        elif is_portrait:
            ix = x + pad if align_left else x + pad + (inner_w - dw)
        else:
            ix = x + pad + (inner_w - dw) / 2
        # Yatay görsellerde üstten hizala; üstteki anlamsız boşluğu kaldır.
        if is_landscape:
            iy = y + pad + (inner_h - dh)
        else:
            iy = y + pad + (inner_h - dh) / 2
        corner_radius = 2.6 * mm
        clip_path = c.beginPath()
        clip_path.roundRect(ix, iy, dw, dh, corner_radius)
        c.saveState()
        c.clipPath(clip_path, stroke=0, fill=0)
        c.drawImage(reader, ix, iy, width=dw, height=dh, preserveAspectRatio=True, mask="auto")
        c.restoreState()
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.7)
        c.roundRect(ix, iy, dw, dh, corner_radius, fill=0, stroke=1)
        return ix, ix + dw
    else:
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.6)
        c.roundRect(x + pad, y + pad, inner_w, inner_h, 2.2 * mm, fill=0, stroke=1)
        c.setFillColor(TEXT_MUTED)
        c.setFont(FONT_BODY, 6 if layout.products_per_page >= 4 else 7)
        c.drawCentredString(x + w / 2, y + img_h / 2, "Fotoğraf yükleyin")
        return x + pad, x + pad + inner_w


def _draw_product_text(
    c: canvas.Canvas,
    layout: PageLayout,
    product: Product,
    x: float,
    img_y: float,
    row_top: float,
    row_bottom: float,
    w: float,
) -> None:
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth

    # Divider çizgilerine yapışmayı engellemek için metni satır içine sabit padding ile yerleştir.
    text_top = row_top - 8 * mm
    min_price_y = row_bottom + 6 * mm

    y = text_top
    center_mode = layout.products_per_page == 1
    c.setFillColor(TEXT)
    name = (product.name or "Ürün adı").strip()
    title_lines, title_size = _title_lines(name, w, layout.title_size, max_lines=2)
    if not title_lines:
        title_lines = ["Ürün adı"]
    c.setFont(FONT_TITLE, title_size)
    # Başlık 2 satıra düştüğünde satırlar biraz nefes alsın.
    title_step = 5.0 * mm if layout.products_per_page >= 3 else 6.0 * mm
    for line in title_lines:
        if center_mode:
            c.drawCentredString(x + (w / 2), y, line)
        else:
            c.drawString(x, y, line)
        y -= title_step

    desc = (product.description or product.subtitle or "").strip()
    max_desc_lines = 1 if layout.products_per_page >= 4 else 2
    desc_lines = _wrap_text(desc, FONT_BODY, layout.body_size, w, max_lines=max_desc_lines) if desc else []
    if desc_lines:
        c.setFillColor(TEXT_MUTED)
        c.setFont(FONT_BODY, layout.body_size)
        line_step = 3.5 * mm if layout.products_per_page >= 3 else 4 * mm
        for i, line in enumerate(desc_lines):
            if center_mode:
                c.drawCentredString(x + (w / 2), y, line)
            else:
                c.drawString(x, y, line)
            y -= line_step
        last_desc_baseline = y
        price_label_y = last_desc_baseline - 3 - DESC_PRICE_GAP
    else:
        price_label_y = y - DESC_PRICE_GAP

    asc_label, desc_label = _font_ascent_descent(FONT_BODY, PRICE_LABEL_SIZE)
    asc_price, _desc_price = _font_ascent_descent(FONT_TITLE, layout.price_amount_size)

    price_amount_y = price_label_y + desc_label - LABEL_AMOUNT_GAP - asc_price

    if price_amount_y < min_price_y:
        price_amount_y = min_price_y
        price_label_y = price_amount_y + asc_price + LABEL_AMOUNT_GAP - desc_label

    price_text = format_price_display(product.price, product.price_currency)

    c.setFillColor(TEXT_MUTED)
    c.setFont(FONT_BODY, PRICE_LABEL_SIZE)
    if center_mode:
        c.drawCentredString(x + (w / 2), price_label_y, "FİYAT")
    else:
        c.drawString(x, price_label_y, "FİYAT")

    c.setFillColor(ACCENT)
    c.setFont(FONT_TITLE, layout.price_amount_size)
    if center_mode:
        c.drawCentredString(x + (w / 2), price_amount_y, price_text)
    else:
        c.drawString(x, price_amount_y, price_text)


def _draw_product_row(
    c: canvas.Canvas,
    layout: PageLayout,
    product: Product,
    index: int,
    y_bottom: float,
    image_on_left: bool,
) -> None:
    from reportlab.lib.units import mm

    if layout.products_per_page == 1:
        # Tekli sayfada metni görselin altına taşı.
        text_block_h = max(42 * mm, layout.row_h * 0.24)
        image_gap = 2.5 * mm
        img_h_draw = max(40 * mm, min(layout.img_h, layout.row_h - text_block_h - image_gap))
        img_y = y_bottom + text_block_h + image_gap
        img_x = MARGIN
        img_w = CONTENT_W
        _draw_image_frame(c, layout, img_x, img_y, img_w, img_h_draw, index, product.image_path, True)
        text_row_top = y_bottom + text_block_h
        _draw_product_text(c, layout, product, MARGIN, img_y, text_row_top, y_bottom, CONTENT_W)
        return

    # Metin görsele yapışmasın: küçük ama belirgin bir yatay boşluk.
    gap = 2.2 * mm
    img_ratio = 0.64 if layout.products_per_page <= 2 else IMG_AREA_RATIO
    text_ratio = 0.34 if layout.products_per_page <= 2 else TEXT_AREA_RATIO
    img_w = CONTENT_W * img_ratio
    text_w = min(CONTENT_W * text_ratio, CONTENT_W - img_w - gap)
    # 1-2 ürün görünümünde yatay fotoğrafların üstünde anlamsız boşluk kalmaması için
    # görsel kutusunu satırın üstünden başlat.
    img_h_draw = layout.img_h
    if layout.products_per_page <= 2:
        img_y = y_bottom + (layout.row_h - layout.img_h)
    else:
        img_y = y_bottom + (layout.row_h - layout.img_h) / 2
    row_top = y_bottom + layout.row_h

    if image_on_left:
        img_x = MARGIN
    else:
        text_x = MARGIN
        img_x = MARGIN + text_w + gap
        # Başlık görsel alanına taşıyorsa görseli satır içinde bir miktar aşağı kaydır.
        title_overflow = _title_right_overflow(product.name or "Ürün adı", text_w, layout.title_size)
        if title_overflow > 0:
            # Uzun başlık sağa taşıyorsa görseli daha görünür şekilde aşağı al.
            min_shift = 2.4 * mm
            desired_shift = min(max(min_shift, title_overflow + (1.8 * mm)), layout.row_h * 0.34)
            # Yeterli aşağı kayma alanı yoksa görseli biraz küçültüp aşağı indir.
            shrink_cap = max(0.0, layout.img_h - (30 * mm))
            shift_down = min(desired_shift, shrink_cap)
            img_y += shift_down
            img_h_draw = max(30 * mm, layout.img_h - shift_down)
        img_left, img_right = _draw_image_frame(
            c, layout, img_x, img_y, img_w, img_h_draw, index, product.image_path, image_on_left
        )
        text_w = max(60, img_left - gap - text_x)

    if image_on_left:
        img_left, img_right = _draw_image_frame(
            c, layout, img_x, img_y, img_w, img_h_draw, index, product.image_path, image_on_left
        )
        text_x = img_right + gap
        text_w = max(60, (PAGE_W - MARGIN) - text_x)

    _draw_product_text(c, layout, product, text_x, img_y, row_top, y_bottom, text_w)


def _draw_cover(c: canvas.Canvas, settings: ShopSettings, total_pages: int) -> None:
    from reportlab.lib.units import mm

    _draw_page_bg(c)

    c.setFillColor(ACCENT_SOFT)
    c.rect(0, PAGE_H - 35 * mm, PAGE_W, 8 * mm, fill=1, stroke=0)

    cy = PAGE_H * 0.52
    if settings.logo_path and os.path.isfile(settings.logo_path):
        result = _fit_image(settings.logo_path, 60 * mm, 60 * mm)
        if result:
            reader, dw, dh = result
            c.drawImage(
                reader,
                (PAGE_W - dw) / 2,
                cy,
                width=dw,
                height=dh,
                preserveAspectRatio=True,
                mask="auto",
            )
            cy -= dh + 10 * mm

    c.setFillColor(ACCENT)
    c.setFont(FONT_TITLE, 28)
    c.drawCentredString(PAGE_W / 2, cy, settings.cover_title.upper())
    if settings.cover_subtitle:
        c.setFillColor(TEXT_MUTED)
        c.setFont(FONT_BODY, 10)
        c.drawCentredString(PAGE_W / 2, cy - 12 * mm, settings.cover_subtitle)

    c.setFillColor(TEXT)
    c.setFont(FONT_BODY, 9)
    c.drawCentredString(PAGE_W / 2, MARGIN + 24 * mm, settings.shop_name.upper())

    _draw_hline(c, PAGE_H - MARGIN - 4 * mm, accent=True)
    _draw_footer(c, settings, 1, total_pages)


def _product_pages(products: list[Product], per_page: int) -> list[list[Product]]:
    pages: list[list[Product]] = []
    for i in range(0, len(products), per_page):
        pages.append(products[i : i + per_page])
    return pages


def generate_pdf(catalog: Catalog, output_path: str, *, embed: bool = True) -> None:
    settings = catalog.settings
    products = catalog.products
    per_page = clamp_products_per_page(settings.products_per_page)
    settings.products_per_page = per_page
    layout = compute_layout(per_page)
    product_page_groups = _product_pages(products, per_page)

    has_cover = True
    total_pages = (1 if has_cover else 0) + len(product_page_groups) if products else 1

    c = canvas.Canvas(output_path, pagesize=(PAGE_W, PAGE_H))
    page_counter = 0

    if has_cover:
        page_counter += 1
        _draw_cover(c, settings, total_pages)
        c.showPage()

    if not products:
        _draw_page_bg(c)
        c.setFillColor(TEXT_MUTED)
        c.setFont(FONT_BODY, 12)
        c.drawCentredString(PAGE_W / 2, PAGE_H / 2, "Henüz ürün eklenmedi.")
        _draw_footer(c, settings, 1, total_pages)
        c.save()
        if embed:
            embed_catalog_in_pdf(output_path, catalog)
        return

    global_index = 0
    for group in product_page_groups:
        page_counter += 1
        _draw_page_bg(c)
        content_bottom = _draw_header(c, settings)

        for slot, product in enumerate(group):
            global_index += 1
            # Global sıra: 1 sol, 2 sağ, 3 sol, 4 sağ … (3–4 ürün/sayfada da geçerli)
            image_left = (global_index - 1) % 2 == 0
            y = content_bottom - (slot + 1) * layout.row_h - slot * layout.row_gap
            _draw_product_row(c, layout, product, global_index, y, image_left)
            if slot < len(group) - 1:
                mid = (
                    content_bottom
                    - (slot + 1) * layout.row_h
                    - slot * layout.row_gap
                    - layout.row_gap / 2
                )
                _draw_hline(c, mid, product_divider=True)

        _draw_footer(c, settings, page_counter, total_pages)
        c.showPage()

    c.save()
    if embed:
        embed_catalog_in_pdf(output_path, catalog)
