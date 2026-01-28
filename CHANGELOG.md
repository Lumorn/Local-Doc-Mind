# Changelog

Alle nennenswerten Aenderungen an diesem Projekt werden in dieser Datei dokumentiert.

## [0.1.0] - 2025-09-27
### Hinzugefuegt
- Initiales Projekt-Skelett mit Standardordnern fuer Konfiguration, Ein-/Ausgabe, Logs, Modelle und Backups.
- `requirements.txt` mit den benoetigten Abhaengigkeiten fuer GUI, Filesystem, Verarbeitung und KI-Stack.
- `config/settings.yaml` als zentrale Konfiguration.
- Windows-Launcher `start.bat` fuer Setup und Start.
- Minimaler App-Einstiegspunkt `src/main.py` zum Laden der Konfiguration.

## [0.1.1] - 2025-09-28
### Hinzugefuegt
- ModelManager fuer Lazy-Loading, VRAM-Checks und 4-bit-Quantisierung der Modelle.
- Neues Core-Paket `src/core` als Ablage fuer zentrale Logik.
- Abhaengigkeit `sentence-transformers` fuer Embedding-Modelle.
