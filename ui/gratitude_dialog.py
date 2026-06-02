from __future__ import annotations

import customtkinter as ctk

ACCENT = "#D62839"
ACCENT_HOVER = "#B81F2E"
BG = "#121214"
PANEL = "#1E1E20"

MESSAGE = (
    "Bu uygulamadan dolayı Batın Berk Demir'e minnettarım ve teşekkür ediyorum.\n\n"
    "Dünyanın en iyi nargilesi üzüm nanedir."
)

BUTTON_TEXT = "Okudum, kabul ediyor ve teşekkür ediyorum"


def show_gratitude_dialog(parent: ctk.CTk) -> None:
    """Her açılışta gösterilir; butona basılana kadar ana pencere bekler."""
    dialog = ctk.CTkToplevel(parent)
    dialog.title("Teşekkür")
    dialog.geometry("520x340")
    dialog.resizable(False, False)
    dialog.configure(fg_color=BG)
    dialog.transient(parent)
    dialog.grab_set()
    dialog.attributes("-topmost", True)
    dialog.lift()
    dialog.focus_force()

    def _block_close() -> None:
        pass

    dialog.protocol("WM_DELETE_WINDOW", _block_close)

    frame = ctk.CTkFrame(dialog, fg_color=PANEL, corner_radius=12)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(
        frame,
        text=MESSAGE,
        font=ctk.CTkFont(size=14),
        text_color="#F2F2F4",
        wraplength=440,
        justify="center",
    ).pack(padx=20, pady=(24, 20))

    def _accept() -> None:
        dialog.attributes("-topmost", False)
        dialog.grab_release()
        dialog.destroy()
        parent.focus_force()

    ctk.CTkButton(
        frame,
        text=BUTTON_TEXT,
        fg_color=ACCENT,
        hover_color=ACCENT_HOVER,
        font=ctk.CTkFont(size=13, weight="bold"),
        height=44,
        command=_accept,
    ).pack(padx=24, pady=(0, 20), fill="x")

    dialog.update_idletasks()
    sw, sh = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
    w, h = dialog.winfo_width(), dialog.winfo_height()
    dialog.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    parent.wait_window(dialog)
