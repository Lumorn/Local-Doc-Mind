# Changelog

Alle nennenswerten Aenderungen an diesem Projekt werden in dieser Datei dokumentiert.

## [0.1.16] - 2025-10-14
### Geaendert
- Einstiegspunkt fuegt den Projektpfad in `sys.path` ein, damit direkte Starts von `src/main.py` die Module korrekt finden.

## [0.1.15] - 2025-10-13
### Hinzugefuegt
- PyQt6 als explizite Abhaengigkeit fuer die GUI aufgenommen.
### Geaendert
- Startpunkt prueft PyQt6 vor dem GUI-Start und gibt eine klare Installationsmeldung aus.
- README dokumentiert die PyQt6-Abhaengigkeit im Schnellstart und den Windows-Abhaengigkeiten.

## [0.1.14] - 2025-10-12
### Hinzugefuegt
- ContextMemory validiert die Trefferanzahl und formatiert den Recall robust fuer das LLM.
### Geaendert
- ReasoningEngine bereinigt JSON-Ausgaben ueber eine zentrale Cleaning-Funktion.
- DocumentPipeline faengt unerwartete LLM-Antworten mit einem Fallback ab.
- ModelManager protokolliert das Zielmodell beim strikten Model-Swapping.
- README dokumentiert die LLM-Schicht und den stabilen VRAM-Swap.

## [0.1.13] - 2025-10-11
### Hinzugefuegt
- Kontext-Gedaechtnis betont die CPU-Embeddings fuer ChromaDB-Recall.
### Geaendert
- ModelManager erzwingt durchgaengiges VRAM-Cleanup beim Modellwechsel.
- README ergaenzt Details zum Memory-Embedding und Fallback-Parsing.

## [0.1.12] - 2025-10-10
### Hinzugefuegt
- ContextMemory nutzt ChromaDB fuer Vektor-Recall und formatiert aehnliche Dokumente als LLM-Kontext.
- ReasoningEngine erzwingt LLM-Swapping und bereinigt JSON-Ausgaben robust (inkl. Markdown-Fences).
### Geaendert
- DocumentPipeline verkettet OCR, Kontext-Recall, LLM-Analyse und mockhafte Dateibewegung.
- README dokumentiert das strikte Model-Swapping und die Cognitive-Layer-Details.

## [0.1.11] - 2025-10-09
### Hinzugefuegt
- Sentence-Transformers als Abhaengigkeit fuer das Memory-Embedding.
### Geaendert
- ModelManager entfernt OCR/LLM-Modelle strikt beim Wechsel, um VRAM freizugeben.
- ReasoningEngine validiert JSON-Antworten explizit vor dem Weiterreichen.
- Pipeline kommentiert die mockhafte Dateiverschiebung fuer die Cognitive Layer.
- README hebt die Cognitive Layer im Projektueberblick hervor.

## [0.1.10] - 2025-10-08
### Hinzugefuegt
- Dauerhaftes CPU-Embedding-Modell (MiniLM) fuer die Cognitive Layer.
- ChromaDB-Gedaechtnis mit Vektor-Embeddings inkl. Kontextformatierung fuer das LLM.
- Fallback-Logik im ReasoningEngine, falls JSON-Parsing fehlschlaegt.
### Geaendert
- ModelManager erzwingt striktes OCR/LLM-Swapping mit sofortigem VRAM-Cleanup.
- DocumentPipeline speichert und nutzt historisches Gedachtnis fuer die Ablageentscheidung.

## [0.1.9] - 2025-10-07
### Hinzugefuegt
- Striktes Model-Swapping fuer OCR und LLM im ModelManager inkl. 4-bit Qwen2.5-Loading.
- Neues ContextMemory auf Basis von ChromaDB fuer konsistente Dateinamen.
- ReasoningEngine fuer JSON-basierte Zusammenfassung, Dateinamen und Zielordner.
### Geaendert
- DocumentPipeline um Memory-Recall, LLM-Reasoning und Dateiverschiebung erweitert.

## [0.1.8] - 2025-10-06
### Hinzugefuegt
- DeepSeek-OCR-2 ModelManager mit dynamischer Flash-Attention-Auswahl und 4-bit-Quantisierung.
- OCR-VisionEngine mit PDF-zu-Image-Pipeline, Prompt-Steuerung und CUDA-OOM-Retry.
- Neue DocumentPipeline mit Backup-Strategie, SHA256-Validierung und Markdown-Output.
- Hochaufloesende PDF-Image-Konvertierung (3x-Matrix) fuer bessere OCR-Ergebnisse.

## [0.1.7] - 2025-10-05
### Hinzugefuegt
- DeepSeek-OCR-2 Wrapper `vision_engine.py` mit hochaufgeloester PDF-zu-Image-Verarbeitung und CUDA-OOM-Retry.
- Neue `DocumentPipeline` fuer PDF-Validierung, Backup-Strategie, OCR-Orchestrierung und Markdown-Output.
- Wiederverwendbare Bild-Hilfsfunktion `pdf_page_to_image` fuer konsistente DPI/Zoom-Settings.

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
