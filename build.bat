@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo MacPDF kurulum paketi hazirlaniyor...
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Sanal ortam olusturuluyor...
  python -m venv .venv
  if errorlevel 1 (
    echo HATA: Python bulunamadi. https://www.python.org adresinden Python 3.10+ kurun.
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat
pip install -r requirements.txt -q
pip install pyinstaller -q

echo.
echo EXE derleniyor (birkaç dakika surebilir)...
pyinstaller --noconfirm macpdf.spec
if errorlevel 1 (
  echo HATA: Derleme basarisiz.
  pause
  exit /b 1
)

set OUT=dist\MacPDF
if not exist "%OUT%\MacPDF.exe" (
  echo HATA: MacPDF.exe olusturulamadi.
  pause
  exit /b 1
)

echo.
echo Paketleniyor...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\MacPDF\*' -DestinationPath 'dist\MacPDF-Portable.zip' -Force"

echo.
echo ========================================
echo  TAMAMLANDI
echo ========================================
echo.
echo  Baska bilgisayara kopyalayin:
echo    dist\MacPDF\          (tum klasor)
echo    veya
echo    dist\MacPDF-Portable.zip
echo.
echo  Calistirma: MacPDF.exe
echo  Python gerekmez.
echo.
pause
