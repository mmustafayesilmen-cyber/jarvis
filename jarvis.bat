@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
start "" /min ollama serve
python main.py
