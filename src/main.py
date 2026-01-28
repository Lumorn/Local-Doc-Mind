from pathlib import Path

import yaml


def load_settings(config_path: Path) -> dict:
    """Lade die Konfiguration aus einer YAML-Datei."""
    # Wenn die Datei fehlt, geben wir eine leere Konfiguration zurueck.
    if not config_path.exists():
        print(f"Konfigurationsdatei nicht gefunden: {config_path}")
        return {}

    with config_path.open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file) or {}


def main() -> None:
    # Standardpfad zur Konfiguration ermitteln.
    config_path = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"
    settings = load_settings(config_path)

    # Ein kurzer Statushinweis fuer den Start.
    app_name = settings.get("app", {}).get("name", "Local-Doc-Mind")
    app_version = settings.get("app", {}).get("version", "0.1.0")
    print(f"{app_name} v{app_version} wird gestartet...")
    print("System initialized.")


if __name__ == "__main__":
    main()
