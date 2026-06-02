# MacPDF — Başka Bilgisayarda Kurulum

## Kurulum dosyası (önerilen)

1. Geliştirici bilgisayarda **`build_setup.bat`** dosyasına çift tıklayın.
2. İşlem bitince oluşur: **`dist\MacPDF-Setup.exe`**
3. Bu dosyayı diğer PC’ye gönderin ve çalıştırın.
4. Sihirbazı takip edin → Başlat menüsünden **MacPDF** açılır.

> İlk kez `build_setup.bat` çalıştırıldığında [Inno Setup 6](https://jrsoftware.org/isinfo.php) yoksa `winget` ile kurulmaya çalışılır.

## Portable (kurulumsuz)

**`build.bat`** → `dist\MacPDF-Portable.zip` (zip aç, `MacPDF.exe` çalıştır).

## Geliştirme (Python gerekir)

```powershell
cd macpdf
.\calistir.bat
```

## Veriler

- Otomatik kayıt: `%LOCALAPPDATA%\MacPDF\son_proje.macpdf.json`
- Örnek görseller: `%LOCALAPPDATA%\MacPDF\sample\`
- Örnek PDF: `Belgeler\MacPDF\ornek_katalog.pdf`

## Sorun giderme

| Sorun | Çözüm |
|--------|--------|
| Windows uyarısı | **Diğer bilgi** → **Yine de çalıştır** |
| Setup oluşmuyor | Inno Setup 6 kur, `build_setup.bat` tekrar çalıştır |
| DLL hatası | [VC++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) kur |
