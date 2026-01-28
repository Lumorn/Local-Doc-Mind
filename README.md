# Local-Doc-Mind

Local-Doc-Mind ist ein lokales, KI-gestuetztes Dokumenten-Sortiersystem mit Cognitive Layer (ContextMemory + ReasoningEngine). Dieses Repository enthaelt das initiale Projekt-Skelett, die Konfiguration sowie ein Startskript fuer Windows.

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
│   └── gui/
│       ├── __init__.py
│       ├── main_window.py
│       ├── workers.py
│       └── widgets/
│           ├── __init__.py
│           └── scan_view.py
│   └── intelligence/
│       ├── __init__.py
│       ├── vision_engine.py
│       ├── analyzer.py
│       ├── splitter.py
│       ├── naming.py
│       ├── memory.py
│       └── reasoning_engine.py
│   └── utils/
│       ├── __init__.py
│       └── image_processing.py
├── requirements.txt
└── start.bat
```

## Schnellstart (Windows)

1. Stelle sicher, dass Python installiert ist.
2. Starte `start.bat` per Doppelklick oder ueber die Kommandozeile.
3. Das Skript prueft Python, legt bei Bedarf eine virtuelle Umgebung in `.venv` an, installiert PyTorch mit CUDA 12.4, installiert danach die Projektabhaengigkeiten (inkl. PyQt6 fuer die GUI) und startet `src/main.py`.

## Konfiguration

Die zentrale Konfiguration liegt in `config/settings.yaml`. Dort sind die Offload-Optionen fuer Windows, Pfade und die Modell-Repos fuer OCR und LLM hinterlegt.

## Abhaengigkeiten (Windows)

`requirements.txt` enthaelt nur die Projektpakete (inklusive PyQt6 fuer die GUI) ohne CUDA-Index-URLs und ohne `flash-attn`. Die CUDA-Variante von PyTorch wird ausschliesslich ueber das Bootstrapper-Skript installiert, damit Windows-Installationen stabil bleiben.

## KI-Speichermanagement

Der `ModelManager` in `src/core/model_manager.py` laedt DeepSeek-OCR-2 nur bei Bedarf, nutzt 4-bit-Quantisierung und waehlt die Attention-Implementierung dynamisch aus. Ist `flash_attn` verfuegbar, wird `flash_attention_2` verwendet, andernfalls faellt der Manager auf `eager` zurueck und gibt eine Warnung fuer Windows-Kompatibilitaet aus. Fuer die Cognitive Layer wird das strikte Model-Swapping zwischen OCR und LLM erzwungen, inklusive sofortigem VRAM-Cleanup (gc + `torch.cuda.empty_cache()`), waehrend das MiniLM-Embedding-Modell dauerhaft auf der CPU verbleibt und die ChromaDB-Memory-Schicht versorgt.

Die LLM-Schicht nutzt Qwen2.5-7B-Instruct in 4-bit-Quantisierung, wodurch das Modell sauber mit dem OCR-Gewicht getauscht werden kann. Dadurch bleibt der VRAM-Bedarf stabil, waehrend das Embedding-Modell permanent auf der CPU aktiv ist.

## Bildaufbereitung

Die PDF-Aufbereitung in `src/utils/image_processing.py` rendert jede Seite mit einer 3x-Matrix (ca. 250-300 DPI), um auch kleingedruckte Texte fuer DeepSeek-OCR-2 lesbar zu machen. Die Seiten werden als `PIL.Image` an die OCR-Pipeline uebergeben.

## Vision-Engine

`src/intelligence/vision_engine.py` kapselt den Zugriff auf DeepSeek-OCR-2. Die Klasse `VisionEngine` nutzt den `ModelManager`, bereitet den Prompt fuer Markdown-Extraktion vor und faengt CUDA-OOMs ab, indem der Cache bereinigt und die Inferenz erneut angestossen wird.

## Dokumentenpipeline (OCR-Orchestrator)

Die Klasse `DocumentPipeline` in `src/core/pipeline.py` implementiert eine OCR-orientierte Verarbeitung: PDF-Validierung, sofortiges Backup mit SHA256-Check, OCR via DeepSeek-OCR-2, Abruf des Langzeitkontexts aus ChromaDB, LLM-basierte Analyse fuer Dateiname und Zielordner sowie das anschliessende Lernen der Entscheidung im Gedaechtnis. Das Ergebnis wird mockhaft als Dateibewegung in den Zielordner umgesetzt.

## Einstiegspunkt

`src/main.py` initialisiert die Qt-GUI, laedt die Konfiguration, startet den ModelManager und verbindet Watcher, Pipeline sowie GUI-Callbacks. Beim Schliessen werden alle Threads sauber beendet. Beim direkten Start von `src/main.py` wird der Projektpfad automatisch in `sys.path` eingetragen, damit die `src.*`-Module auch ohne explizite PYTHONPATH-Anpassung gefunden werden.

## Intelligence-Module

Die Module unter `src/intelligence/` liefern die Kern-Intelligenz: OCR-Analyse mit DeepSeek-OCR-2 (gekapselt in `vision_engine.py`), ein Stapel-Scanner zum Erkennen von Dokumentgrenzen, das `ContextMemory` fuer persistenten Namenskontext (ChromaDB + MiniLM) sowie der `ReasoningEngine`, der Qwen2.5 fuer Zusammenfassung, Dateinamen und Zielordner nutzt. Die Memory-Schicht formatiert aehnliche Dokumente als LLM-tauglichen Kontext und speichert neue Entscheidungen als Vektoren. Der Reasoning-Output wird robust geparst, um JSON in Markdown-Fences zu bereinigen, und liefert bei Bedarf Fallback-Antworten.

## GUI-Dashboard

Das GUI-Paket unter `src/gui/` liefert ein modernes Dashboard mit Dateibaum, Scan-Ansicht und Matrix-Logfenster. Die `PipelineWorker`-Klasse verbindet die Processing-Pipeline ueber Qt-Signale mit der Benutzeroberflaeche, waehrend `ScanView` halbtransparente Bounding-Boxen fuer visuelle KI-Overlays zeichnet.
