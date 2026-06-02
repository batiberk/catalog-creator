@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Sanal ortam kuruluyor...
  python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
)
.venv\Scripts\python.exe main.py
