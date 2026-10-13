@echo off
title Minecraft Texturepack Upscaler
cd /d "%~dp0"
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ein Fehler ist aufgetreten oder erforderliche Pakete fehlen.
    echo Installiere Abhaengigkeiten mit: pip install -r requirements.txt
    pause
)
