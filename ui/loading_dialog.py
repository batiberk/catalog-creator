"""PDF / dosya işlemleri sırasında bekleme penceresi."""

from __future__ import annotations

import customtkinter as ctk

BG = "#1E1E20"
ACCENT = "#D62839"
TEXT_MUTED = "#9A9AA3"


class LoadingDialog(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk, message: str = "Lütfen bekleyin…") -> None:
        super().__init__(parent)
        self.title("MacPDF")
        self.configure(fg_color=BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = ctk.CTkFrame(self, fg_color=BG)
        frame.pack(padx=32, pady=28)

        ctk.CTkLabel(
            frame,
            text=message,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=320,
        ).pack(pady=(0, 16))

        self._progress = ctk.CTkProgressBar(frame, width=280, mode="indeterminate")
        self._progress.pack(pady=(0, 8))
        self._progress.start()

        self._hint = ctk.CTkLabel(
            frame,
            text="",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11),
            wraplength=320,
        )
        self._hint.pack()

        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

    def set_hint(self, text: str) -> None:
        self._hint.configure(text=text)
        self.update_idletasks()

    def close(self) -> None:
        try:
            self._progress.stop()
            self.grab_release()
        except Exception:
            pass
        self.destroy()
