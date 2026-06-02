from __future__ import annotations

from dataclasses import dataclass

from reportlab.lib.units import mm

from reportlab.lib.pagesizes import A4

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN
FOOTER_H = 12 * mm
HEADER_H = 18 * mm
TEXT_GAP = 4 * mm

BASE_IMG_W = 46 * mm
BASE_IMG_H = 64 * mm


def clamp_products_per_page(value: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = 2
    return max(1, min(4, n))


@dataclass(frozen=True)
class PageLayout:
    products_per_page: int
    img_w: float
    img_h: float
    row_h: float
    row_gap: float
    title_size: float
    body_size: float
    price_amount_size: float


def compute_layout(products_per_page: int) -> PageLayout:
    n = clamp_products_per_page(products_per_page)
    usable_top = PAGE_H - MARGIN - HEADER_H - 4 * mm
    usable_bottom = MARGIN + FOOTER_H + 4 * mm
    # 2'li düzende satırlar arasına ekstra nefes ver; alt ürün üst ayraç çizgisine yapışmasın.
    if n == 2:
        row_gap = 2.2 * mm
    elif n > 2:
        row_gap = 0.9 * mm
    else:
        row_gap = 0
    row_h = (usable_top - usable_bottom - row_gap * max(0, n - 1)) / n

    # Ürün satırında görsel alanını mümkün olduğunca büyüt.
    max_img_h = row_h - 1.5 * mm
    img_h = max(26 * mm, max_img_h * 0.985)
    img_w = img_h * (BASE_IMG_W / BASE_IMG_H)

    if n == 1:
        title_size, body_size, price_size = 22.0, 12.0, 24.0
    elif n == 2:
        title_size, body_size, price_size = 20.0, 11.5, 22.0
    elif n == 3:
        title_size, body_size, price_size = 17.0, 10.5, 18.0
    else:
        title_size, body_size, price_size = 15.0, 9.5, 16.0

    return PageLayout(
        products_per_page=n,
        img_w=img_w,
        img_h=img_h,
        row_h=row_h,
        row_gap=row_gap,
        title_size=title_size,
        body_size=body_size,
        price_amount_size=price_size,
    )
