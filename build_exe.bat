@echo off
title Erstelle TexturepackUpscaler.exe
cd /d "%~dp0"
echo ========================================================
echo Erstelle Standalone Windows-Executable (PyInstaller)...
echo ========================================================
python -m PyInstaller --noconfirm --onedir --windowed --name "TexturepackUpscaler" --add-data "core;core" --add-data "gui;gui" main.py
echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================================
    echo Erfolgreich fertiggestellt!
    echo Die ausfuehrbare Datei befindet sich in: dist\TexturepackUpscaler\
    echo ========================================================
) else (
    echo Fehler beim Erstellen der Executable.
)
pause
