@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
title Jarvis Kurulum
echo.
echo  === JARVIS KURULUM ===
echo.
set "PY="
py -3.12 --version >nul 2>nul && set "PY=py -3.12"
if not defined PY for /f "delims=" %%P in ('where python 2^>nul') do if not defined PY set "PY=%%P"
if not defined PY (
  echo  Python 3.12 bulunamadi. https://www.python.org/downloads/ adresinden kurun ^("Add to PATH" secili olsun^), sonra yeniden calistirin.
  pause & exit /b 1
)
where ollama >nul 2>nul || (
  echo  Ollama bulunamadi. https://ollama.com/download adresinden kurun, sonra yeniden calistirin.
  pause & exit /b 1
)
if not exist config.json copy config.ornek.json config.json >nul
if not exist .venv\Scripts\python.exe %PY% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (echo  Paket kurulumu basarisiz oldu. Internet baglantisini kontrol edip tekrar calistirin.& pause & exit /b 1)
if not exist voices mkdir voices
set B=https://huggingface.co/rhasspy/piper-voices/resolve/main
if not exist voices\tr_TR-dfki-medium.onnx curl -L -o voices\tr_TR-dfki-medium.onnx %B%/tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx
if not exist voices\tr_TR-dfki-medium.onnx.json curl -L -o voices\tr_TR-dfki-medium.onnx.json %B%/tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx.json
if not exist voices\en_GB-alan-medium.onnx curl -L -o voices\en_GB-alan-medium.onnx %B%/en/en_GB/alan/medium/en_GB-alan-medium.onnx
if not exist voices\en_GB-alan-medium.onnx.json curl -L -o voices\en_GB-alan-medium.onnx.json %B%/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json
start "" /min ollama serve
timeout /t 5 >nul
ollama pull qwen3:8b
echo.
echo  KURULUM TAMAM. jarvis.bat ile baslatin ^(ayarlar: config.json^).
pause
