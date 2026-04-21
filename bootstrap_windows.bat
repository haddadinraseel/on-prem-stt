@echo off
setlocal

if not exist .venv (
    py -3.10 -m venv .venv
)

.venv\Scripts\python.exe -m pip install --upgrade pip "setuptools<81.0.0" wheel
.venv\Scripts\python.exe -m pip install --no-build-isolation -r requirements.txt

echo.
echo Installation finished.
echo If ffmpeg is installed and available in PATH, you can start the app with:
echo   .\start_all.bat
