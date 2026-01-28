# Local-Doc-Mind

Local-Doc-Mind ist ein lokales, KI-gestuetztes Dokumenten-Sortiersystem. Dieses Repository enthaelt das initiale Projekt-Skelett, die Konfiguration sowie ein Startskript fuer Windows.

## Projektstruktur

```
.
├── backup/      # Standard-Backup-Ordner
├── config/      # Konfigurationsdateien
│   └── settings.yaml
├── input/       # Standard-Eingangsordner
├── logs/        # Rotierende Logfiles (Platzhalter)
├── models/      # Speicherort fuer heruntergeladene LLMs
├── output/      # Standard-Ausgangsordner
├── src/         # Core-Logik
│   ├── __init__.py
│   ├── main.py
│   └── core/
│       ├── __init__.py
│       ├── model_manager.py
│       ├── watcher.py
│       └── pipeline.py
│   └── intelligence/
│       ├── __init__.py
│       ├── analyzer.py
│       ├── splitter.py
│       └── naming.py
├── requirements.txt
└── start.bat
```

## Schnellstart (Windows)

1. Stelle sicher, dass Python installiert ist.
2. Starte `start.bat` per Doppelklick oder ueber die Kommandozeile.
3. Das Skript legt bei Bedarf eine virtuelle Umgebung in `.venv` an, installiert Abhaengigkeiten und startet `src/main.py`.

## Konfiguration

Die zentrale Konfiguration liegt in `config/settings.yaml`. Dort sind Pfade, Modell-IDs sowie grundlegende App-Informationen hinterlegt.

## KI-Speichermanagement

Der neue `ModelManager` in `src/core/model_manager.py` laedt OCR-, Embedding- und LLM-Modelle erst bei Bedarf und entlaedt sie wieder, wenn der VRAM knapp wird. Damit werden nie alle Modelle gleichzeitig im Grafikspeicher gehalten. Die Klasse nutzt 4-bit-Quantisierung, um den Speicherverbrauch zu minimieren.

## Dateiueberwachung & Processing-Pipeline

Das Modul `src/core/watcher.py` ueberwacht den Eingangsordner rekursiv und legt nur fertig geschriebene PDF-Dateien in eine Queue. Die neue `ProcessingPipeline` in `src/core/pipeline.py` nimmt diese Aufgaben entgegen, erstellt zuerst ein datiertes Backup (mit SHA256-Integritaetscheck) und verschiebt die Datei danach in einen internen Processing-Ordner. So bleibt der Input-Ordner sauber, bevor eine KI die Datei verarbeitet.

## Intelligence-Module

Die neuen Module unter `src/intelligence/` liefern die Kern-Intelligenz: OCR-Analyse mit DeepSeek-OCR-2, ein Stapel-Scanner zum Erkennen von Dokumentgrenzen sowie eine RAG-gestuetzte Namensvergabe auf Basis von ChromaDB und einem Reasoning-LLM.
