@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  MacPDF - Setup.exe olusturuluyor
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Sanal ortam olusturuluyor...
  python -m venv .venv
  if errorlevel 1 (
    echo HATA: Python bulunamadi.
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat
pip install -r requirements.txt -q
pip install pyinstaller -q

echo [1/3] Program derleniyor (PyInstaller)...
pyinstaller --noconfirm macpdf.spec
if errorlevel 1 (
  echo HATA: PyInstaller basarisiz.
  pause
  exit /b 1
)

if not exist "dist\MacPDF\MacPDF.exe" (
  echo HATA: dist\MacPDF\MacPDF.exe bulunamadi.
  pause
  exit /b 1
)

echo [2/3] Inno Setup araniyor...
set "ISCC="
set "PF86=%ProgramFiles(x86)%"
set "PF64=%ProgramFiles%"

if exist "%PF86%\Inno Setup 6\ISCC.exe" set "ISCC=%PF86%\Inno Setup 6\ISCC.exe"
if exist "%PF64%\Inno Setup 6\ISCC.exe" set "ISCC=%PF64%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
  echo.
  echo Inno Setup 6 kurulu degil.
  echo Kuruluyor (winget)...
  winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
  if exist "%PF86%\Inno Setup 6\ISCC.exe" set "ISCC=%PF86%\Inno Setup 6\ISCC.exe"
  if exist "%PF64%\Inno Setup 6\ISCC.exe" set "ISCC=%PF64%\Inno Setup 6\ISCC.exe"
  if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
)

if "%ISCC%"=="" (
  echo.
  echo HATA: Inno Setup bulunamadi.
  echo Manuel kur: https://jrsoftware.org/isinfo.php
  echo Sonra bu dosyayi tekrar calistirin.
  echo.
  echo Portable zip hazir: dist\MacPDF-Portable.zip
  powershell -NoProfile -Command "Compress-Archive -Path 'dist\MacPDF\*' -DestinationPath 'dist\MacPDF-Portable.zip' -Force"
  pause
  exit /b 1
)

echo [3/3] Setup.exe derleniyor...
"%ISCC%" "installer\MacPDF.iss"
if errorlevel 1 (
  echo HATA: Setup derlemesi basarisiz.
  pause
  exit /b 1
)

powershell -NoProfile -Command "Compress-Archive -Path 'dist\MacPDF\*' -DestinationPath 'dist\MacPDF-Portable.zip' -Force" 2>nul

echo.
echo ========================================
echo  TAMAMLANDI
echo ========================================
echo.
echo  Kurulum dosyasi:
echo    dist\MacPDF-Setup.exe
echo.
echo  Diger PC'ye bu dosyayi gonderin ve calistirin.
echo.
pause
