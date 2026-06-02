from __future__ import annotations

CURRENCY_OPTIONS: tuple[tuple[str, str], ...] = (
    ("TRY", "TL (₺)"),
    ("USD", "Dolar ($)"),
    ("EUR", "Euro (€)"),
)

CURRENCY_SYMBOLS: dict[str, str] = {
    "TRY": "₺",
    "USD": "$",
    "EUR": "€",
}

_CURRENCY_PREFIXES = ("₺", "$", "€", "TL", "USD", "EUR", "TRY")


def normalize_currency(code: str) -> str:
    code = (code or "TRY").strip().upper()
    return code if code in CURRENCY_SYMBOLS else "TRY"


def format_price_display(amount: str, currency: str) -> str:
    text = (amount or "").strip()
    if not text or text == "—":
        return "—"

    for prefix in _CURRENCY_PREFIXES:
        if text.upper().startswith(prefix.upper()):
            text = text[len(prefix) :].strip()
            break
        spaced = f"{prefix} "
        if text.upper().startswith(spaced.upper()):
            text = text[len(spaced) :].strip()
            break

    symbol = CURRENCY_SYMBOLS[normalize_currency(currency)]
    return f"{symbol} {text}"
