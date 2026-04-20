@echo off
setlocal

if not exist .venv\Scripts\python.exe (
    echo Virtual environment not found. Create it first with:
    echo   py -3.10 -m venv .venv
    exit /b 1
)

.venv\Scripts\python.exe -m streamlit run frontend\streamlit_app.py
