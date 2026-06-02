"""MacPDF — Nargile ürün kataloğu PDF oluşturucu."""

from ui.app import CatalogApp


def main() -> None:
    app = CatalogApp()
    app.mainloop()


if __name__ == "__main__":
    main()
