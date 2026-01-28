# Changelog

Alle nennenswerten Aenderungen an diesem Projekt werden in dieser Datei dokumentiert.

## [0.1.6] - 2025-10-04
### Geaendert
- `requirements.txt` bereinigt: feste Transformer-Version, Windows-taugliche Pakete und ohne CUDA-Index-URLs bzw. `flash-attn`.
- `start.bat` als Smart-Bootstrapper fuer Python-Check, CUDA-PyTorch-Installation, Abhaengigkeiten und Start.
- `config/settings.yaml` auf Offload-Optionen und neue Modellstruktur fuer OCR/LLM umgestellt.

## [0.1.5] - 2025-10-03
### Hinzugefuegt
- Langzeit-Kontextmodul `ContextManager` mit `.ai_context.md` pro Ordner.
- Vollstaendiger Pipeline-Workflow mit Split-Scan, OCR, Kontextabruf, Benennung und finaler Ablage.
- Neuer GUI-Einstiegspunkt, der Config, ModelManager, Watcher und Pipeline sauber verbindet.

## [0.1.4] - 2025-10-02
### Hinzugefuegt
- GUI-Dashboard mit Dateibaum, Scan-Ansicht und Matrix-Logfenster.
- `PipelineWorker` fuer die Qt-Thread-Integration inkl. Signal-Bridge.
- Callback-Unterstuetzung in der Processing-Pipeline fuer GUI-Updates.

## [0.1.3] - 2025-10-01
### Hinzugefuegt
- Neue Intelligence-Module fuer OCR-Analyse, Stapel-Splitting und RAG-basierte Dateibenennung.
- Erweiterungen am ModelManager fuer eine konsistente Nutzung ueber die neuen Module hinweg.

## [0.1.2] - 2025-09-29
### Hinzugefuegt
- Dateiueberwachung mit Debouncing fuer fertige PDF-Dateien im Eingangsordner.
- Processing-Pipeline mit Backup-First-Strategie, SHA256-Integritaetscheck und Verschiebung in einen Processing-Ordner.

## [0.1.1] - 2025-09-28
### Hinzugefuegt
- ModelManager fuer Lazy-Loading, VRAM-Checks und 4-bit-Quantisierung der Modelle.
- Neues Core-Paket `src/core` als Ablage fuer zentrale Logik.
- Abhaengigkeit `sentence-transformers` fuer Embedding-Modelle.

## [0.1.0] - 2025-09-27
### Hinzugefuegt
- Initiales Projekt-Skelett mit Standardordnern fuer Konfiguration, Ein-/Ausgabe, Logs, Modelle und Backups.
- `requirements.txt` mit den benoetigten Abhaengigkeiten fuer GUI, Filesystem, Verarbeitung und KI-Stack.
- `config/settings.yaml` als zentrale Konfiguration.
- Windows-Launcher `start.bat` fuer Setup und Start.
- Minimaler App-Einstiegspunkt `src/main.py` zum Laden der Konfiguration.
