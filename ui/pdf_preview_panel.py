"""Ana pencerede sağ tarafta PDF önizleme paneli."""

from __future__ import annotations

import os
import queue
import threading
from collections import OrderedDict
from typing import Any, Callable

import customtkinter as ctk
from PIL import Image

from models.catalog import Catalog
from pdf.catalog_fingerprint import catalog_fingerprint
from pdf.generator import generate_pdf
from pdf.layout import clamp_products_per_page
from pdf.preview_render import PREVIEW_DPI, pdf_build_preview_meta, pdf_page_to_image
from paths import user_data_dir

BG_PANEL = "#1E1E20"
CARD_BG = "#141416"
TEXT_MUTED = "#9A9AA3"
ACCENT = "#D62839"
ACCENT_HOVER = "#B81F2E"
_PAGE_CACHE_MAX = 6


class PdfPreviewPanel(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, get_catalog: Callable[[], Catalog]) -> None:
        super().__init__(master, fg_color=BG_PANEL, width=620)
        self._get_catalog = get_catalog
        self._preview_path = os.path.join(user_data_dir(), "_preview_temp.pdf")
        self._page_count = 0
        self._current_page = 0
        self._page_cache: OrderedDict[int, Image.Image] = OrderedDict()
        self._display_cache: dict[tuple[int, int, int], ctk.CTkImage] = {}
        self._resize_job: str | None = None
        self._generation = 0
        self._queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._pending_refresh = False
        self._busy = False
        self._loaded = False
        self._stale = False
        self._last_fingerprint: str | None = None

        self.pack_propagate(False)
        self._build()
        self.after(100, self._process_queue)

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(14, 4))

        ctk.CTkLabel(
            header,
            text="PDF Önizleme",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(side="left")

        self._btn_reload = ctk.CTkButton(
            header,
            text="Önizle",
            width=72,
            height=26,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            command=self.refresh,
        )
        self._btn_reload.pack(side="right")

        self._info_label = ctk.CTkLabel(
            self,
            text="",
            anchor="w",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11),
            wraplength=580,
            justify="left",
        )
        self._info_label.pack(fill="x", padx=14, pady=(0, 6))

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=14, pady=4)

        self._btn_prev = ctk.CTkButton(nav, text="◀", width=36, command=self._prev_page)
        self._btn_prev.pack(side="left")

        self._page_label = ctk.CTkLabel(nav, text="—", font=ctk.CTkFont(size=12, weight="bold"))
        self._page_label.pack(side="left", expand=True)

        self._btn_next = ctk.CTkButton(nav, text="▶", width=36, command=self._next_page)
        self._btn_next.pack(side="right")

        self._status_label = ctk.CTkLabel(
            self,
            text="Önizleme oluşturulmadı",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11),
        )
        self._status_label.pack(padx=14, pady=(0, 6))

        self._canvas_frame = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=8, cursor="hand2")
        self._canvas_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self._page_image_label = ctk.CTkLabel(
            self._canvas_frame,
            text="Önizlemeyi oluşturmak için\ntıklayın",
            text_color=TEXT_MUTED,
            cursor="hand2",
        )
        self._page_image_label.pack(expand=True, padx=8, pady=8)

        self._canvas_frame.bind("<Configure>", self._on_resize)
        self._canvas_frame.bind("<Button-1>", self._on_preview_click)
        self._page_image_label.bind("<Button-1>", self._on_preview_click)

        self._btn_prev.configure(state="disabled")
        self._btn_next.configure(state="disabled")
        self._info_label.configure(
            text=(
                "Önizleme, «Önizle» butonuna veya alana tıklayınca oluşur. "
                "«Yenile»ye basmadan otomatik güncellenmez."
            )
        )

    @staticmethod
    def _snapshot_catalog(catalog: Catalog) -> Catalog:
        return Catalog.from_dict(catalog.to_dict())

    def _cache_page_image(self, index: int, img: Image.Image) -> None:
        if index in self._page_cache:
            self._page_cache.move_to_end(index)
        else:
            self._page_cache[index] = img
        while len(self._page_cache) > _PAGE_CACHE_MAX:
            evicted, _ = self._page_cache.popitem(last=False)
            self._display_cache = {
                k: v for k, v in self._display_cache.items() if k[0] != evicted
            }

    def _clear_caches(self) -> None:
        self._page_cache.clear()
        self._display_cache.clear()

    def _process_queue(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                kind = msg[0]
                if kind == "pdf_ready":
                    first = msg[4] if len(msg) > 4 else None
                    fp = msg[5] if len(msg) > 5 else None
                    self._on_pdf_ready(msg[1], msg[2], msg[3], first, fp)
                elif kind == "page_ready":
                    self._on_page_ready(msg[1], msg[2], msg[3])
                elif kind == "error":
                    self._on_error(msg[1])
        except queue.Empty:
            pass
        self.after(80, self._process_queue)

    def _on_resize(self, _event=None) -> None:
        if not self._loaded or self._current_page not in self._page_cache:
            return
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(150, lambda: self._display_image(self._current_page))

    def _on_preview_click(self, _event=None) -> None:
        if self._busy:
            return
        self.refresh()

    def mark_stale(self) -> None:
        if not self._loaded:
            return
        self._stale = True
        self._status_label.configure(text="Güncel değil — «Yenile»ye basın")

    def refresh(self) -> None:
        if self._busy:
            return
        self._stale = False
        self._kick_refresh()

    def _kick_refresh(self) -> None:
        self._busy = True
        self._pending_refresh = True
        self._generation += 1
        self._clear_caches()
        self._btn_reload.configure(state="disabled")
        self._btn_prev.configure(state="disabled")
        self._btn_next.configure(state="disabled")
        self._status_label.configure(text="PDF hazırlanıyor…")
        self._page_image_label.configure(image=None, text="Lütfen bekleyin…")
        self._start_worker_if_idle()

    def _start_worker_if_idle(self) -> None:
        if not self._pending_refresh:
            return
        self._pending_refresh = False
        gen = self._generation

        try:
            catalog = self._snapshot_catalog(self._get_catalog())
        except Exception as e:
            self._on_error(str(e))
            return

        per_page = clamp_products_per_page(catalog.settings.products_per_page)
        catalog.settings.products_per_page = per_page
        fingerprint = catalog_fingerprint(catalog)

        if (
            self._loaded
            and fingerprint == self._last_fingerprint
            and os.path.isfile(self._preview_path)
        ):
            self._reuse_cached_pdf(gen, catalog)
            return

        threading.Thread(
            target=self._build_pdf_worker,
            args=(gen, catalog, self._preview_path, fingerprint),
            daemon=True,
        ).start()

    def _reuse_cached_pdf(self, generation: int, catalog: Catalog) -> None:
        def worker() -> None:
            try:
                count, first = pdf_build_preview_meta(self._preview_path, PREVIEW_DPI)
                self._queue.put(("pdf_ready", generation, count, catalog, first))
            except ImportError:
                self._queue.put(("error", "PyMuPDF gerekli.\npip install pymupdf"))
            except Exception as e:
                self._queue.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _build_pdf_worker(
        self, generation: int, catalog: Catalog, pdf_path: str, fingerprint: str
    ) -> None:
        try:
            generate_pdf(catalog, pdf_path, embed=False)
            count, first = pdf_build_preview_meta(pdf_path, PREVIEW_DPI)
            self._queue.put(("pdf_ready", generation, count, catalog, first, fingerprint))
        except ImportError:
            self._queue.put(("error", "PyMuPDF gerekli.\npip install pymupdf"))
        except Exception as e:
            self._queue.put(("error", str(e)))

    def _on_pdf_ready(
        self,
        generation: int,
        page_count: int,
        catalog: Catalog,
        first_page: Image.Image | None,
        fingerprint: str | None = None,
    ) -> None:
        if generation != self._generation:
            self._start_worker_if_idle()
            return

        if fingerprint is not None:
            self._last_fingerprint = fingerprint

        self._loaded = True
        self._stale = False
        self._btn_reload.configure(
            text="Yenile",
            fg_color="#3A3A42",
            hover_color="#4A4A54",
        )

        self._page_count = page_count
        n = len(catalog.products)
        per_page = catalog.settings.products_per_page
        self._info_label.configure(
            text=f"{n} ürün · sayfada {per_page} · {page_count} sayfa"
        )
        self._current_page = min(self._current_page, max(0, page_count - 1))
        if page_count == 0:
            self._on_error("PDF sayfası oluşturulamadı.")
            return

        if first_page is not None:
            self._cache_page_image(0, first_page)

        if self._current_page in self._page_cache:
            self._display_image(self._current_page)
            self._busy = False
            self._btn_reload.configure(state="normal")
            self._status_label.configure(text="Güncel")
            return

        self._status_label.configure(text="İlk sayfa yükleniyor…")
        self._load_page(self._current_page, generation, final=True)

    def _on_error(self, message: str) -> None:
        self._busy = False
        self._pending_refresh = False
        self._btn_reload.configure(state="normal")
        self._status_label.configure(text="Hata")
        self._page_image_label.configure(image=None, text=message)
        self._page_label.configure(text="—")
        self._btn_prev.configure(state="disabled")
        self._btn_next.configure(state="disabled")
        self._start_worker_if_idle()

    def _load_page(self, index: int, generation: int, *, final: bool = False) -> None:
        if index < 0 or index >= self._page_count:
            self._on_error("Geçersiz sayfa.")
            return
        if index in self._page_cache:
            self._display_image(index)
            if final:
                self._btn_reload.configure(state="normal")
                self._status_label.configure(text="Güncel")
                self._busy = False
            return

        def worker() -> None:
            try:
                img = pdf_page_to_image(self._preview_path, index, dpi=PREVIEW_DPI)
                self._queue.put(("page_ready", generation, index, img))
            except Exception as e:
                self._queue.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_page_ready(self, generation: int, index: int, img: Image.Image) -> None:
        if generation != self._generation:
            return
        self._cache_page_image(index, img)
        if index == self._current_page:
            self._display_image(index)
        self._busy = False
        self._pending_refresh = False
        self._btn_reload.configure(state="normal")
        self._status_label.configure(text="Güncel")

    def _display_image(self, index: int) -> None:
        pil_img = self._page_cache.get(index)
        if pil_img is None:
            return

        avail_w = max(200, self._canvas_frame.winfo_width() - 24)
        avail_h = max(240, self._canvas_frame.winfo_height() - 24)
        scale = min(avail_w / pil_img.width, avail_h / pil_img.height) * 0.88
        disp_w = max(1, int(pil_img.width * scale))
        disp_h = max(1, int(pil_img.height * scale))

        display_key = (index, disp_w, disp_h)
        ctk_img = self._display_cache.get(display_key)
        if ctk_img is None:
            resized = pil_img.resize((disp_w, disp_h), Image.Resampling.BILINEAR)
            ctk_img = ctk.CTkImage(light_image=resized, dark_image=resized, size=(disp_w, disp_h))
            self._display_cache[display_key] = ctk_img

        self._page_image_label.configure(image=ctk_img, text="")
        self._page_image_label.image = ctk_img

        self._page_label.configure(text=f"{index + 1} / {self._page_count}")
        self._btn_prev.configure(state="normal" if index > 0 else "disabled")
        self._btn_next.configure(state="normal" if index < self._page_count - 1 else "disabled")

    def _prev_page(self) -> None:
        if not self._loaded or self._current_page <= 0:
            return
        self._current_page -= 1
        self._status_label.configure(text="Sayfa yükleniyor…")
        self._load_page(self._current_page, self._generation)

    def _next_page(self) -> None:
        if not self._loaded or self._current_page >= self._page_count - 1:
            return
        self._current_page += 1
        self._status_label.configure(text="Sayfa yükleniyor…")
        self._load_page(self._current_page, self._generation)
