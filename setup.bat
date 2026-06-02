@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  MacPDF - Gelistirme ortami kurulumu
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo HATA: Python bulunamadi.
  echo https://www.python.org adresinden Python 3.10+ kurun.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/2] Sanal ortam olusturuluyor...
  python -m venv .venv
  if errorlevel 1 (
    echo HATA: Sanal ortam olusturulamadi.
    pause
    exit /b 1
  )
) else (
  echo [1/2] Sanal ortam zaten mevcut.
)

echo [2/2] Bagimliliklar kuruluyor...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt
if errorlevel 1 (
  echo HATA: Bagimlilik kurulumu basarisiz.
  pause
  exit /b 1
)

echo.
echo ========================================
echo  Kurulum tamamlandi
echo ========================================
echo.
echo  Uygulamayi calistir:  calistir.bat
echo  Kurulum EXE uret:     build_setup.bat
echo.
pause
