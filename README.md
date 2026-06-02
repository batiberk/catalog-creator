# MacPDF — Satış Katalog Oluşturucu

MacPDF, farklı sektörlerde kullanılabilen bir Windows masaüstü uygulamasıdır.  
Ürün görselleri, açıklamalar ve fiyatlarla profesyonel satış katalogları oluşturur; hem dikey hem yatay görselleri destekler.

## Öne Çıkan Özellikler

- **Sektör bağımsız kullanım:** Nargileye özel değildir; tüm ürün katalogları için uygundur.
- **Esnek sayfa düzeni:** Sayfa başına `1-4` ürün seçimi.
- **Dikey + yatay görsel desteği:** Farklı oranlardaki ürün fotoğraflarını otomatik yerleştirir.
- **Kapak yönetimi:** Katalog başlığı, alt başlık, firma adı ve logo.
- **Ürün bilgileri:** Ürün adı, kısa açıklama, fiyat ve para birimi.
- **Para birimi desteği:** `TRY`, `USD`, `EUR`.
- **PDF önizleme:** Uygulama içinden anlık PDF önizleme ve sayfa gezintisi.
- **Alt bilgi alanı:** Web sitesi, telefon ve sayfa numarası.
- **Proje kaydet/aç:** `.macpdf.json` formatında proje dosyası.
- **PDF’den içe aktarma:** Daha önce oluşturulmuş PDF’den katalogu açıp düzenleyebilme (uyumluluk modu dahil).
- **Tema:** Koyu arayüz ve kurumsal katalog görünümü.

## Teknoloji

- Python
- CustomTkinter (masaüstü arayüz)
- ReportLab (PDF üretimi)
- Pillow (görsel işlemleri)
- PyMuPDF / pypdf (PDF okuma ve aktarım)

## Kurulum (Geliştirme)

Python `3.10+` önerilir.

```powershell
cd c:\Users\PC\Desktop\projects\macpdf
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Çalıştırma

```powershell
python main.py
```

Alternatif:

```powershell
.\calistir.bat
```

## Derleme ve Dağıtım

- **Setup (önerilen):** `build_setup.bat` -> `dist\MacPDF-Setup.exe`
- **Portable:** `build.bat` -> `dist\MacPDF-Portable.zip`

Kurulum detayları için: [KURULUM.md](KURULUM.md)

## Kullanım Akışı

1. **Dükkan & Kapak** alanında firma bilgilerini ve kapak metinlerini girin.
2. **Ürünler** sekmesinde ürünleri ekleyin (görsel + açıklama + fiyat + para birimi).
3. Sayfa başına ürün adedini seçin (`1-4`).
4. Önizleme ile kontrol edin.
5. **PDF Oluştur** ile çıktıyı alın.

## Notlar

- Fiyat alanına `2450` veya `2.450` gibi değerler girilebilir; PDF’de uygun formatta gösterilir.
- Eski PDF’lerden yapılan içe aktarımlarda bazı alanlar eksik gelebilir; düzenleyip yeniden PDF üretmeniz önerilir.
