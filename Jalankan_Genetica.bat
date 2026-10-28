@echo off
setlocal
cd /d "%~dp0"
title GENETICA - Aplikasi Penjadwalan Kuliah

echo ==========================================
echo      GENETICA - UTS ALGORITMA GENETIKA
echo ==========================================
echo.
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Menyiapkan Python virtual environment...
  py -m venv .venv
  if errorlevel 1 (
    echo Perintah py gagal. Mencoba python...
    python -m venv .venv
    if errorlevel 1 goto :error
  )
)
echo [2/3] Memasang paket aplikasi (perlu internet saat pertama kali)...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error
echo.
echo [3/3] Membuka aplikasi. Tekan CTRL+C untuk menghentikan.
echo Alamat: http://localhost:8501
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
pause
exit /b 0
:error
echo.
echo Ada kegagalan. Pastikan Python 3.10+ sudah terpasang dan internet aktif.
pause
exit /b 1
