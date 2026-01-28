@echo off
setlocal enabledelayedexpansion

REM Prüfen, ob die virtuelle Umgebung existiert
if not exist ".venv" (
    echo [INFO] Virtuelle Umgebung wird erstellt...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Konnte die virtuelle Umgebung nicht erstellen.
        pause
        exit /b 1
    )

    echo [INFO] Pip wird aktualisiert...
    .venv\Scripts\python.exe -m pip install --upgrade pip
    if errorlevel 1 (
        echo [ERROR] Konnte pip nicht aktualisieren.
        pause
        exit /b 1
    )

    echo [INFO] Abhaengigkeiten werden installiert...
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Konnte Abhaengigkeiten nicht installieren.
        pause
        exit /b 1
    )
)

REM Virtuelle Umgebung aktivieren
call .venv\Scripts\activate
if errorlevel 1 (
    echo [ERROR] Konnte die virtuelle Umgebung nicht aktivieren.
    pause
    exit /b 1
)

REM Hauptprogramm starten
python src\main.py

REM Fenster offen halten, damit Fehlermeldungen sichtbar bleiben
pause
