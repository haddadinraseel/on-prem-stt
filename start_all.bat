@echo off
setlocal

cd /d "%~dp0"

if not exist .venv (
    echo Creating virtual environment...
    py -3.10 -m venv .venv
    if errorlevel 1 exit /b 1
)

if not exist .venv\Scripts\python.exe (
    echo Virtual environment is missing Python. Delete .venv and try again.
    exit /b 1
)

echo Installing Python dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip "setuptools<81.0.0" wheel
if errorlevel 1 exit /b 1

.venv\Scripts\python.exe -m pip install --no-build-isolation -r requirements.txt
if errorlevel 1 exit /b 1

echo.
echo Starting backend and frontend...
start "On-Prem STT Backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
start "On-Prem STT Frontend" cmd /k ".venv\Scripts\python.exe -m streamlit run frontend\streamlit_app.py"

echo.
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:8501
echo.
echo If ffmpeg is not installed in PATH, setup will complete but transcription will not work until ffmpeg and ffprobe are installed.
