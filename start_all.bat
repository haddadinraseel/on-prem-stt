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
echo Starting backend...
start "On-Prem STT Backend" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir "%~dp0" --host 127.0.0.1 --port 8000 --no-access-log"

echo Waiting for backend to become available...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$deadline = (Get-Date).AddSeconds(60);" ^
    "while ((Get-Date) -lt $deadline) {" ^
    "  try {" ^
    "    $response = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health -TimeoutSec 5;" ^
    "    if ($response.StatusCode -eq 200) { exit 0 }" ^
    "  } catch { Start-Sleep -Seconds 1 }" ^
    "}" ^
    "exit 1"
if errorlevel 1 (
    echo.
    echo Backend did not become ready within 60 seconds.
    echo Check the backend window for the exact error before opening the frontend.
    exit /b 1
)

echo Backend is ready.
echo Starting frontend...
start "On-Prem STT Frontend" cmd /k ".venv\Scripts\python.exe -m streamlit run frontend\streamlit_app.py"

echo.
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:8501
echo.
echo If ffmpeg is not installed in PATH, setup will complete but transcription will not work until ffmpeg and ffprobe are installed.
