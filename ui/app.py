from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.catalog import Catalog, Product, ShopSettings
from models.currency import CURRENCY_OPTIONS, normalize_currency
from pdf.catalog_embed import PdfImportError, catalog_from_pdf, import_assets_dir_for_pdf
from pdf.generator import generate_pdf
from paths import user_data_dir
from pdf.layout import clamp_products_per_page
from persistence import load_autosave, save_autosave
from ui.gratitude_dialog import show_gratitude_dialog
from ui.loading_dialog import LoadingDialog
from ui.pdf_preview_panel import PdfPreviewPanel

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ACCENT = "#D62839"
ACCENT_HOVER = "#B81F2E"
BG_PANEL = "#1E1E20"
CARD_BG = "#141416"
BG_APP = "#121214"
TEXT_MUTED = "#9A9AA3"


class CatalogApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MacPDF — Katalog Oluşturucu")
        self.configure(fg_color=BG_APP)
        self.minsize(1100, 600)

        self.catalog = load_autosave() or Catalog()
        self._selected_index: int | None = None
        self._product_buttons: list[ctk.CTkButton] = []
        self._drag_index: int | None = None
        self._drag_start_y: int = 0
        self._drag_active = False
        self._drop_insert_before: int | None = None
        self._drop_line: ctk.CTkFrame | None = None
        self._drag_visual_index: int | None = None
        self._ignore_next_product_click = False
        self._import_queue: queue.Queue = queue.Queue()
        self._import_loader: LoadingDialog | None = None
        self._autosave_after_id: str | None = None
        self._thumb_cache: dict[tuple[str, int, int, bool], ctk.CTkImage] = {}

        self._build_menu()
        self._build_layout()
        self._load_settings_form()
        self._refresh_product_list()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._maximize_window()
        self.after(150, lambda: show_gratitude_dialog(self))
        self.after(100, self._process_import_queue)

    def _maximize_window(self) -> None:
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")
        if sys.platform == "win32":
            try:
                self.state("zoomed")
            except tk.TclError:
                pass

    def _build_menu(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=BG_PANEL, height=44)
        bar.pack(fill="x", padx=12, pady=(12, 0))
        bar.pack_propagate(False)

        ctk.CTkButton(bar, text="Proje Aç", width=100, command=self._open_project).pack(
            side="left", padx=8, pady=6
        )
        ctk.CTkButton(bar, text="Kaydet", width=100, command=self._save_project).pack(
            side="left", padx=4, pady=6
        )
        ctk.CTkButton(
            bar,
            text="PDF'den Aç",
            width=110,
            fg_color="#3A3A42",
            hover_color="#4A4A54",
            command=self._import_from_pdf,
        ).pack(side="left", padx=4, pady=6)
        ctk.CTkButton(
            bar,
            text="PDF Oluştur",
            width=140,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(weight="bold"),
            command=self._export_pdf,
        ).pack(side="right", padx=8, pady=6)

    def _build_layout(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0, minsize=620)
        body.grid_rowconfigure(0, weight=1)

        editor = ctk.CTkFrame(body, fg_color="transparent")
        editor.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tabs = ctk.CTkTabview(editor, fg_color=BG_PANEL)
        tabs.pack(fill="both", expand=True)

        self._build_settings_tab(tabs.add("Dükkan & Kapak"))
        self._build_products_tab(tabs.add("Ürünler"))

        self._pdf_preview = PdfPreviewPanel(body, get_catalog=self._get_catalog_for_preview)
        self._pdf_preview.grid(row=0, column=1, sticky="ns")

    def _labeled_entry(self, parent: ctk.CTkFrame, label: str, default: str = "") -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, anchor="w", text_color=ACCENT).pack(fill="x", pady=(8, 2))
        entry = ctk.CTkEntry(parent, fg_color=CARD_BG)
        entry.pack(fill="x", pady=(0, 4))
        if default:
            entry.insert(0, default)
        return entry

    def _build_settings_tab(self, parent: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        s = self.catalog.settings
        self.entry_shop = self._labeled_entry(scroll, "Dükkan adı", s.shop_name)
        self.entry_catalog = self._labeled_entry(scroll, "Katalog başlığı (sayfa üstü)", s.catalog_subtitle)
        self.entry_cover_title = self._labeled_entry(scroll, "Kapak başlığı", s.cover_title)
        self.entry_cover_sub = self._labeled_entry(scroll, "Kapak alt yazısı (isteğe bağlı)", s.cover_subtitle)
        self.entry_web = self._labeled_entry(scroll, "Web sitesi", s.website)
        self.entry_phone = self._labeled_entry(scroll, "Telefon", s.phone)

        ctk.CTkLabel(
            scroll,
            text="Sayfa başına ürün sayısı",
            anchor="w",
            text_color=ACCENT,
        ).pack(fill="x", pady=(12, 4))
        self._ppp_var = ctk.StringVar(value=str(clamp_products_per_page(s.products_per_page)))
        self._ppp_segment = ctk.CTkSegmentedButton(
            scroll,
            values=["1", "2", "3", "4"],
            variable=self._ppp_var,
            command=self._on_products_per_page_change,
        )
        self._ppp_segment.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            scroll,
            text="Ürünler sırayla sol–sağ–sol–sağ yerleşir (1. sol, 2. sağ, 3. sol …).",
            anchor="w",
            text_color=TEXT_MUTED,
            wraplength=420,
        ).pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(scroll, text="Logo (kapak)", anchor="w", text_color=ACCENT).pack(fill="x", pady=(12, 2))
        logo_row = ctk.CTkFrame(scroll, fg_color="transparent")
        logo_row.pack(fill="x")
        self.label_logo = ctk.CTkLabel(logo_row, text="Logo seçilmedi", anchor="w")
        self.label_logo.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(logo_row, text="Logo Seç", width=100, fg_color=ACCENT, command=self._pick_logo).pack(
            side="right"
        )
        self.logo_preview = ctk.CTkLabel(scroll, text="")
        self.logo_preview.pack(pady=12)

        ctk.CTkButton(scroll, text="Ayarları Uygula", fg_color=ACCENT, command=self._apply_settings).pack(
            pady=16
        )

    def _mark_pdf_preview_stale(self) -> None:
        if hasattr(self, "_pdf_preview"):
            self._pdf_preview.mark_stale()

    def _build_products_tab(self, parent: ctk.CTkFrame) -> None:
        paned = ctk.CTkFrame(parent, fg_color="transparent")
        paned.pack(fill="both", expand=True)

        left = ctk.CTkFrame(paned, width=240, fg_color=BG_PANEL)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="Ürünler", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(12, 2))
        ctk.CTkLabel(
            left,
            text="Basılı tutun — kırmızı çizgi hedef sıradır",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            wraplength=210,
        ).pack(pady=(0, 8))
        btn_row = ctk.CTkFrame(left, fg_color="transparent")
        btn_row.pack(fill="x", padx=8)
        ctk.CTkButton(btn_row, text="+ Ekle", width=70, fg_color=ACCENT, command=self._add_product).pack(
            side="left", padx=2
        )
        ctk.CTkButton(btn_row, text="Sil", width=70, fg_color="#6B2A2A", hover_color="#8B3535", command=self._delete_product).pack(
            side="left", padx=2
        )

        self.product_list = ctk.CTkScrollableFrame(left, fg_color=CARD_BG)
        self.product_list.pack(fill="both", expand=True, padx=8, pady=8)

        right = ctk.CTkScrollableFrame(paned, fg_color=BG_PANEL)
        right.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            right,
            text="Ürün bilgisi (kısa — PDF’de fotoğrafın altında görünür)",
            font=ctk.CTkFont(size=13, weight="bold"),
            wraplength=400,
        ).pack(anchor="w", padx=12, pady=12)

        preview_frame = ctk.CTkFrame(right, fg_color=CARD_BG, corner_radius=8)
        preview_frame.pack(padx=12, pady=4)
        self.img_preview = ctk.CTkLabel(
            preview_frame,
            text="Dikey fotoğraf\nönizlemesi",
            width=120,
            height=170,
            fg_color="#2E181C",
        )
        self.img_preview.pack(padx=16, pady=16)
        ctk.CTkButton(
            right,
            text="Fotoğraf yükle",
            fg_color=ACCENT,
            command=self._pick_product_image,
        ).pack(padx=12, pady=4)

        form = ctk.CTkFrame(right, fg_color="transparent")
        form.pack(fill="x", padx=12, pady=8)

        self.entry_name = self._labeled_entry(form, "Ürün adı")
        self.entry_description = self._labeled_entry(form, "Kısa açıklama (tek satır)")
        self.entry_price = self._labeled_entry(form, "Fiyat (örn. 2.450 veya 24.50)")

        ctk.CTkLabel(form, text="Para birimi", anchor="w", text_color=ACCENT).pack(fill="x", pady=(8, 2))
        self._currency_labels = {code: label for code, label in CURRENCY_OPTIONS}
        self._currency_codes = {label: code for code, label in CURRENCY_OPTIONS}
        self.currency_var = ctk.StringVar(value=self._currency_labels["TRY"])
        self.currency_menu = ctk.CTkOptionMenu(
            form,
            variable=self.currency_var,
            values=[label for _, label in CURRENCY_OPTIONS],
            fg_color=CARD_BG,
        )
        self.currency_menu.pack(fill="x", pady=(0, 4))

        ctk.CTkButton(right, text="Ürünü kaydet", fg_color=ACCENT, command=self._save_current_product).pack(
            padx=12, pady=16, anchor="w"
        )

        self._refresh_product_list()

    def _autosave(self, *, flush: bool = False) -> None:
        if flush:
            if self._autosave_after_id is not None:
                self.after_cancel(self._autosave_after_id)
                self._autosave_after_id = None
            self._autosave_write()
            return
        if self._autosave_after_id is not None:
            self.after_cancel(self._autosave_after_id)
        self._autosave_after_id = self.after(1200, self._autosave_write)

    def _autosave_write(self) -> None:
        self._autosave_after_id = None
        try:
            self._apply_settings_from_form()
            self._save_product_form_silent()
            save_autosave(self.catalog)
        except OSError:
            pass

    def _on_close(self) -> None:
        self._autosave(flush=True)
        self.destroy()

    def _apply_settings(self) -> None:
        self._apply_settings_from_form()
        self._autosave(flush=True)
        self._mark_pdf_preview_stale()
        messagebox.showinfo(
            "Tamam",
            "Ayarlar kaydedildi.\nUygulamayı yeniden açtığınızda otomatik yüklenecek.",
        )

    def _pick_logo(self) -> None:
        path = filedialog.askopenfilename(
            title="Logo seç",
            filetypes=[("Görseller", "*.png *.jpg *.jpeg *.webp *.bmp")],
        )
        if path:
            self.catalog.settings.logo_path = path
            self.label_logo.configure(text=os.path.basename(path))
            self._show_image_preview(path, self.logo_preview, 100)
            self._autosave()
            self._mark_pdf_preview_stale()

    def _pick_product_image(self) -> None:
        if self._selected_index is None:
            messagebox.showwarning("Uyarı", "Önce listeden bir ürün seçin veya yeni ürün ekleyin.")
            return
        path = filedialog.askopenfilename(
            title="Ürün fotoğrafı",
            filetypes=[("Görseller", "*.png *.jpg *.jpeg *.webp *.bmp")],
        )
        if path:
            self.catalog.products[self._selected_index].image_path = path
            self._show_image_preview(path, self.img_preview, 160, vertical=True)
            self._mark_pdf_preview_stale()

    def _show_image_preview(
        self, path: str, label: ctk.CTkLabel, max_size: int, vertical: bool = False
    ) -> None:
        try:
            mtime_ns = os.stat(path).st_mtime_ns
            cache_key = (path, mtime_ns, max_size, vertical)
            cimg = self._thumb_cache.get(cache_key)
            if cimg is None:
                img = Image.open(path)
                if vertical:
                    box = (max_size, int(max_size * 1.45))
                else:
                    box = (max_size, max_size)
                img.thumbnail(box)
                cimg = ctk.CTkImage(light_image=img, dark_image=img, size=box)
                self._thumb_cache[cache_key] = cimg
                if len(self._thumb_cache) > 48:
                    self._thumb_cache.pop(next(iter(self._thumb_cache)))
            label.configure(image=cimg, text="")
            label.image = cimg
        except OSError:
            label.configure(text="Görsel yüklenemedi", image=None)

    def _style_product_button(self, btn: ctk.CTkButton, selected: bool) -> None:
        btn.configure(
            fg_color=ACCENT if selected else "#2A2A2E",
            text_color="white" if selected else "#C8C8CC",
            hover_color=ACCENT_HOVER if selected else "#35353A",
        )

    def _update_product_selection(self, old_index: int | None, new_index: int | None) -> None:
        if old_index is not None and 0 <= old_index < len(self._product_buttons):
            self._style_product_button(self._product_buttons[old_index], False)
        if new_index is not None and 0 <= new_index < len(self._product_buttons):
            self._style_product_button(self._product_buttons[new_index], True)

    def _refresh_product_list(self) -> None:
        self._end_product_drag(cancel=True)
        for w in self.product_list.winfo_children():
            if w is self._drop_line:
                continue
            w.destroy()
        self._product_buttons = []
        for i, p in enumerate(self.catalog.products):
            title = p.name or f"Ürün {i + 1}"
            btn = ctk.CTkButton(
                self.product_list,
                text=title,
                anchor="w",
            )
            btn._product_index = i
            self._style_product_button(btn, i == self._selected_index)
            btn.pack(fill="x", pady=2)
            self._bind_product_drag(btn)
            self._product_buttons.append(btn)

    def _product_index_from_event(self, event: tk.Event) -> int | None:
        w: tk.Misc | None = event.widget
        for _ in range(8):
            if w is None:
                break
            if w in self._product_buttons:
                return self._product_buttons.index(w)
            w = getattr(w, "master", None)
        return None

    def _bind_product_drag(self, btn: ctk.CTkButton) -> None:
        def on_press(event: tk.Event) -> None:
            idx = self._product_index_from_event(event)
            if idx is None:
                return
            self._drag_index = idx
            self._drag_start_y = event.y_root
            self._drag_active = False

        def on_motion(event: tk.Event) -> None:
            if self._drag_index is None or self._drag_active:
                return
            if abs(event.y_root - self._drag_start_y) < 10:
                return
            self._start_product_drag()

        def on_release(event: tk.Event) -> None:
            if self._drag_active or self._ignore_next_product_click:
                if self._ignore_next_product_click:
                    self._ignore_next_product_click = False
                return
            idx = self._product_index_from_event(event)
            if idx is not None:
                self._select_product(idx)

        for widget in (btn, getattr(btn, "_canvas", None)):
            if widget is None:
                continue
            widget.bind("<ButtonPress-1>", on_press, add="+")
            widget.bind("<B1-Motion>", on_motion, add="+")
            widget.bind("<ButtonRelease-1>", on_release, add="+")

    def _start_product_drag(self) -> None:
        if self._drag_index is None:
            return
        self._drag_active = True
        self.configure(cursor="fleur")
        self._drag_visual_index = self._drag_index
        btn = self._product_buttons[self._drag_index]
        btn.configure(fg_color="#252528", text_color=TEXT_MUTED)
        self.bind_all("<B1-Motion>", self._on_product_drag_motion)
        self.bind_all("<ButtonRelease-1>", self._on_product_drag_release)
        self._update_drop_indicator(self._drag_start_y)

    def _drop_index_from_y(self, y_root: int) -> int:
        if not self._product_buttons:
            return 0
        drag = self._drag_index
        for i, btn in enumerate(self._product_buttons):
            if i == drag:
                continue
            mid = btn.winfo_rooty() + btn.winfo_height() // 2
            if y_root < mid:
                return i
        return len(self._product_buttons)

    def _ensure_drop_line(self) -> ctk.CTkFrame:
        if self._drop_line is None or not self._drop_line.winfo_exists():
            self._drop_line = ctk.CTkFrame(
                self.product_list,
                height=4,
                fg_color=ACCENT,
                corner_radius=2,
            )
        return self._drop_line

    def _update_drop_indicator(self, y_root: int) -> None:
        insert_before = self._drop_index_from_y(y_root)
        if insert_before == self._drop_insert_before:
            return
        self._drop_insert_before = insert_before
        if not self._product_buttons:
            return
        line = self._ensure_drop_line()
        line.pack_forget()
        if insert_before < len(self._product_buttons):
            line.pack(fill="x", padx=4, pady=1, before=self._product_buttons[insert_before])
        else:
            line.pack(fill="x", padx=4, pady=1)

    def _clear_drop_indicator(self) -> None:
        if self._drop_line is not None and self._drop_line.winfo_exists():
            self._drop_line.pack_forget()
        self._drop_insert_before = None

    def _restore_drag_visual(self) -> None:
        if self._drag_visual_index is not None and 0 <= self._drag_visual_index < len(self._product_buttons):
            self._style_product_button(
                self._product_buttons[self._drag_visual_index],
                self._drag_visual_index == self._selected_index,
            )
        self._drag_visual_index = None

    def _end_product_drag(self, *, cancel: bool) -> None:
        was_active = self._drag_active
        self._drag_active = False
        self._drag_index = None
        self.configure(cursor="")
        try:
            self.unbind_all("<B1-Motion>")
            self.unbind_all("<ButtonRelease-1>")
        except tk.TclError:
            pass
        self._clear_drop_indicator()
        if was_active or cancel:
            self._restore_drag_visual()

    def _on_product_drag_motion(self, event: tk.Event) -> None:
        if self._drag_active:
            self._update_drop_indicator(event.y_root)

    def _on_product_drag_release(self, event: tk.Event) -> None:
        if not self._drag_active or self._drag_index is None:
            self._end_product_drag(cancel=True)
            return
        from_i = self._drag_index
        insert_before = self._drop_index_from_y(event.y_root)
        self._ignore_next_product_click = True
        self._end_product_drag(cancel=False)
        self._reorder_product(from_i, insert_before)

    def _move_product_button(self, from_i: int, dest: int) -> None:
        btn = self._product_buttons.pop(from_i)
        self._product_buttons.insert(dest, btn)
        btn.pack_forget()
        if self._drop_line is not None and self._drop_line.winfo_ismapped():
            self._drop_line.pack_forget()
        if dest < len(self._product_buttons) - 1:
            btn.pack(fill="x", pady=2, before=self._product_buttons[dest + 1])
        else:
            btn.pack(fill="x", pady=2)
        for i, b in enumerate(self._product_buttons):
            b._product_index = i
        for i, b in enumerate(self._product_buttons):
            self._style_product_button(b, i == self._selected_index)

    def _reorder_product(self, from_i: int, insert_before: int) -> None:
        n = len(self.catalog.products)
        if not (0 <= from_i < n):
            return
        insert_before = max(0, min(insert_before, n))
        if from_i < insert_before:
            dest = insert_before - 1
        else:
            dest = insert_before
        if dest == from_i:
            return
        self._save_product_form_silent()
        item = self.catalog.products.pop(from_i)
        self.catalog.products.insert(dest, item)
        if self._selected_index is not None:
            sel = self._selected_index
            if sel == from_i:
                self._selected_index = dest
            elif from_i < sel <= dest:
                self._selected_index = sel - 1
            elif dest <= sel < from_i:
                self._selected_index = sel + 1
        if len(self._product_buttons) == n:
            self._move_product_button(from_i, dest)
        else:
            self._refresh_product_list()
        self._autosave()
        self._mark_pdf_preview_stale()

    def _add_product(self) -> None:
        self.catalog.products.append(Product())
        self._selected_index = len(self.catalog.products) - 1
        self._refresh_product_list()
        self._load_product_form(self.catalog.products[-1])
        self._mark_pdf_preview_stale()

    def _delete_product(self) -> None:
        if self._selected_index is None:
            return
        if messagebox.askyesno("Sil", "Seçili ürünü silmek istiyor musunuz?"):
            del self.catalog.products[self._selected_index]
            self._selected_index = None
            self._clear_product_form()
            self._refresh_product_list()
            self._mark_pdf_preview_stale()

    def _select_product(self, index: int) -> None:
        if index == self._selected_index:
            return
        self._save_product_form_silent()
        old_index = self._selected_index
        self._selected_index = index
        self._update_product_selection(old_index, index)
        self._load_product_form(self.catalog.products[index])

    def _load_product_form(self, p: Product) -> None:
        self._set_entry(self.entry_name, p.name)
        self._set_entry(self.entry_description, p.description or p.subtitle)
        self._set_entry(self.entry_price, p.price)
        code = normalize_currency(p.price_currency)
        self.currency_var.set(self._currency_labels[code])
        if p.image_path and os.path.isfile(p.image_path):
            self._show_image_preview(p.image_path, self.img_preview, 160, vertical=True)
        else:
            self.img_preview.configure(image=None, text="Dikey fotoğraf\nönizlemesi")

    def _clear_product_form(self) -> None:
        for e in (self.entry_name, self.entry_description, self.entry_price):
            e.delete(0, "end")
        self.currency_var.set(self._currency_labels["TRY"])
        self.img_preview.configure(image=None, text="Dikey fotoğraf\nönizlemesi")

    @staticmethod
    def _set_entry(entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, value)

    def _save_product_form_silent(self) -> None:
        if self._selected_index is None:
            return
        p = self.catalog.products[self._selected_index]
        p.name = self.entry_name.get().strip()
        p.description = self.entry_description.get().strip()
        p.price = self.entry_price.get().strip()
        p.price_currency = normalize_currency(self._currency_codes.get(self.currency_var.get(), "TRY"))

    def _save_current_product(self) -> None:
        if self._selected_index is None:
            messagebox.showwarning("Uyarı", "Kaydetmek için bir ürün seçin.")
            return
        self._save_product_form_silent()
        self._refresh_product_list()
        self._autosave(flush=True)
        self._mark_pdf_preview_stale()
        messagebox.showinfo("Tamam", "Ürün kaydedildi.")

    def _close_import_loader(self) -> None:
        if self._import_loader and self._import_loader.winfo_exists():
            self._import_loader.close()
        self._import_loader = None

    def _process_import_queue(self) -> None:
        try:
            while True:
                msg = self._import_queue.get_nowait()
                kind = msg[0]
                if kind == "hint":
                    if self._import_loader and self._import_loader.winfo_exists():
                        self._import_loader.set_hint(msg[1])
                elif kind == "done":
                    self._close_import_loader()
                    self._on_import_finished(msg[1], msg[2])
                elif kind == "error":
                    self._close_import_loader()
                    messagebox.showerror(
                        "PDF'den açılamadı" if kind == "error" else "Hata",
                        msg[1],
                    )
        except queue.Empty:
            pass
        self.after(80, self._process_import_queue)

    def _import_from_pdf(self) -> None:
        path = filedialog.askopenfilename(
            title="Düzenlemek için PDF seç",
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return

        self._close_import_loader()
        self._import_loader = LoadingDialog(self, "PDF açılıyor…")
        self._import_loader.set_hint("Dosya okunuyor, bu biraz sürebilir.")

        def worker() -> None:
            try:
                self._import_queue.put(("hint", "Katalog verisi çıkarılıyor…"))
                assets_dir = import_assets_dir_for_pdf(path, user_data_dir())
                self._import_queue.put(("hint", "Ürünler ve görseller yükleniyor…"))
                result = catalog_from_pdf(path, assets_dir)
                self._import_queue.put(("done", path, result))
            except PdfImportError as e:
                self._import_queue.put(("error", str(e)))
            except OSError as e:
                self._import_queue.put(("error", f"PDF okunamadı:\n{e}"))
            except Exception as e:
                self._import_queue.put(("error", f"Beklenmeyen hata:\n{e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_import_finished(
        self,
        path: str,
        result: tuple[Catalog, int, bool],
    ) -> None:
        catalog, missing, legacy = result

        if self.catalog.products and not messagebox.askyesno(
            "Projeyi değiştir",
            "Mevcut proje silinip PDF'deki katalog yüklensin mi?\n\n"
            "Hayır derseniz işlem iptal edilir.",
        ):
            return

        self._selected_index = None
        self.catalog = catalog
        self._load_settings_form()
        self._refresh_product_list()
        if catalog.products:
            self._select_product(0)
        else:
            self._selected_index = None
            self._clear_product_form()
        self._autosave(flush=True)
        self._mark_pdf_preview_stale()

        msg = f"{len(catalog.products)} ürün yüklendi.\nArtık düzenleyip yeniden PDF oluşturabilirsiniz."
        if legacy:
            msg += (
                "\n\n(Eski PDF — metin ve görsellerden okundu. "
                "Bazı alanlar eksik olabilir; kaydettikten sonra yeni PDF oluşturun.)"
            )
        if missing:
            msg += f"\n\n{missing} ürünün fotoğrafı bulunamadı; yeniden yüklemeniz gerekebilir."
        messagebox.showinfo("PDF'den yüklendi", msg)

    def _open_project(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("MacPDF proje", "*.macpdf.json"), ("JSON", "*.json")]
        )
        if not path:
            return
        try:
            self.catalog = Catalog.load(path)
            self._selected_index = None
            self._load_settings_form()
            self._refresh_product_list()
            self._clear_product_form()
            self._mark_pdf_preview_stale()
            messagebox.showinfo("Tamam", "Proje yüklendi.")
        except (OSError, ValueError, KeyError, TypeError) as e:
            messagebox.showerror("Hata", f"Proje açılamadı:\n{e}")

    def _save_project(self) -> None:
        self._apply_settings_from_form()
        self._save_product_form_silent()
        path = filedialog.asksaveasfilename(
            defaultextension=".macpdf.json",
            filetypes=[("MacPDF proje", "*.macpdf.json")],
        )
        if path:
            self.catalog.save(path)
            messagebox.showinfo("Tamam", "Proje kaydedildi.")

    def _apply_settings_from_form(self) -> None:
        s = self.catalog.settings
        s.shop_name = self.entry_shop.get().strip()
        s.catalog_subtitle = self.entry_catalog.get().strip()
        s.cover_title = self.entry_cover_title.get().strip()
        s.cover_subtitle = self.entry_cover_sub.get().strip()
        s.website = self.entry_web.get().strip()
        s.phone = self.entry_phone.get().strip()
        s.products_per_page = clamp_products_per_page(int(self._ppp_var.get()))

    def _on_products_per_page_change(self, value: str) -> None:
        self.catalog.settings.products_per_page = clamp_products_per_page(int(value))
        self._autosave()
        self._mark_pdf_preview_stale()

    def _get_catalog_for_preview(self) -> Catalog:
        self._apply_settings_from_form()
        self._save_product_form_silent()
        return self.catalog

    def _load_settings_form(self) -> None:
        s = self.catalog.settings
        for entry, val in [
            (self.entry_shop, s.shop_name),
            (self.entry_catalog, s.catalog_subtitle),
            (self.entry_cover_title, s.cover_title),
            (self.entry_cover_sub, s.cover_subtitle),
            (self.entry_web, s.website),
            (self.entry_phone, s.phone),
        ]:
            self._set_entry(entry, val)
        self._ppp_var.set(str(clamp_products_per_page(s.products_per_page)))
        if s.logo_path and os.path.isfile(s.logo_path):
            self.label_logo.configure(text=os.path.basename(s.logo_path))
            self._show_image_preview(s.logo_path, self.logo_preview, 100)

    def _export_pdf(self) -> None:
        self._apply_settings_from_form()
        self._save_product_form_silent()
        if not self.catalog.products:
            if not messagebox.askyesno(
                "Ürün yok",
                "Henüz ürün eklemediniz. Sadece kapak sayfası oluşturulsun mu?",
            ):
                return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="katalog.pdf",
        )
        if not path:
            return
        try:
            generate_pdf(self.catalog, path)
            messagebox.showinfo("Başarılı", f"PDF oluşturuldu:\n{path}")
            if sys.platform == "win32":
                os.startfile(path)
        except OSError as e:
            messagebox.showerror("Hata", f"PDF oluşturulamadı:\n{e}")
