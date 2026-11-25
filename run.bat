@echo off
title Translator - Desktop English-to-Sinhala Subtitle AI
cd /d "%~dp0"

set "PYTHON_EXE=C:\Users\maili\AppData\Local\Programs\Python\Python312\python.exe"

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" main.py %*
) else (
    python main.py %*
)

pause

