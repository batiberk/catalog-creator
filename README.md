# MacPDF — Nargile Katalog Oluşturucu

Telefondan çektiğiniz dikey ürün fotoğraflarıyla katalog PDF’i üreten Windows masaüstü uygulaması (koyu arayüz, PDF’de açık siyah + kırmızı tema).

## Özellikler

- **Kapak sayfası:** Özelleştirilebilir başlık ve dükkan logosu
- **Ürün sayfaları:** Sayfada **2 ürün**, katalog düzeni (üstte fotoğraf solda, altta fotoğraf sağda) + kısa açıklama + fiyat
- PDF teması: açık siyah zemin, kırmızı vurgular
- **Alt bilgi:** Web sitesi, telefon, sayfa numarası
- Projeyi `.macpdf.json` olarak kaydetme / açma

## Kurulum

Python 3.10+ gerekir.

```powershell
cd c:\Users\PC\Desktop\projects\macpdf
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Çalıştırma (geliştirme)

```powershell
python main.py
```

## Başka bilgisayara kurulum

**`build_setup.bat`** → `dist\MacPDF-Setup.exe` (kurulum sihirbazı)  
**`build.bat`** → `dist\MacPDF-Portable.zip` (taşınabilir)  
Ayrıntılar: **[KURULUM.md](KURULUM.md)**

## Kullanım

1. **Dükkan & Kapak** sekmesinde dükkan adı, katalog başlığı, kapak yazıları, logo ve iletişim bilgilerini girin.
2. **Ürünler** sekmesinde **+ Ekle** ile ürün ekleyin; dikey fotoğraf, kısa tek satır açıklama ve fiyat yeterli.
3. **PDF Oluştur** ile kataloğu kaydedin.

Fiyat alanına `2.450` yazmanız yeterli; PDF’de `₺ 2.450` olarak görünür.
