@echo off
setlocal enabledelayedexpansion

REM Stellt sicher, dass wir im Projektordner arbeiten.
cd /d "%~dp0"

REM Pruefen, ob Python verfuegbar ist
where python >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python wurde nicht gefunden. Bitte Python installieren und erneut starten.
    pause
    exit /b 1
)

REM Pruefen, ob die virtuelle Umgebung existiert
if not exist ".venv" (
    echo [INFO] Virtuelle Umgebung wird erstellt...
    python -m venv .venv
    if errorlevel 1 (
        echo [FEHLER] Konnte die virtuelle Umgebung nicht erstellen.
        pause
        exit /b 1
    )

    call .venv\Scripts\activate
    if errorlevel 1 (
        echo [FEHLER] Konnte die virtuelle Umgebung nicht aktivieren.
        pause
        exit /b 1
    )

    echo [INFO] Pip wird aktualisiert...
    python -m pip install --upgrade pip
    if errorlevel 1 (
        echo [FEHLER] Konnte pip nicht aktualisieren.
        pause
        exit /b 1
    )

    echo [INFO] Installiere PyTorch mit CUDA Support...
    pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
    if errorlevel 1 (
        echo [FEHLER] Konnte PyTorch nicht installieren.
        pause
        exit /b 1
    )

    echo [INFO] Installiere Projekt-Abhaengigkeiten...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [FEHLER] Konnte Abhaengigkeiten nicht installieren.
        pause
        exit /b 1
    )
) else (
    call .venv\Scripts\activate
    if errorlevel 1 (
        echo [FEHLER] Konnte die virtuelle Umgebung nicht aktivieren.
        pause
        exit /b 1
    )

    REM Pruefen, ob PyQt6 vorhanden ist und bei Bedarf Abhaengigkeiten nachinstallieren.
    python -c "import importlib.util; import sys; sys.exit(0 if importlib.util.find_spec('PyQt6') else 1)" >nul 2>&1
    if errorlevel 1 (
        echo [INFO] PyQt6 fehlt. Installiere Projekt-Abhaengigkeiten...
        pip install -r requirements.txt
        if errorlevel 1 (
            echo [FEHLER] Konnte Abhaengigkeiten nicht installieren.
            pause
            exit /b 1
        )
    )
)

REM Ordnerstruktur anlegen, falls nicht vorhanden
mkdir input output backup models logs 2>nul

REM Hauptprogramm starten
REM Sorgt fuer einen stabilen Importpfad, egal von wo das Skript gestartet wird.
set "PYTHONPATH=%~dp0"
python -m src.main
if errorlevel 1 (
    echo [FEHLER] Die Anwendung wurde mit einem Fehler beendet.
    pause
)
