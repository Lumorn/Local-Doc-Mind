"""Hilfsfunktionen fuer Abhaengigkeitspruefungen und -installation."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

_MODULE_ALIASES = {
    "PyMuPDF": "fitz",
    "Pillow": "PIL",
    "pyyaml": "yaml",
    "sentence-transformers": "sentence_transformers",
}


def _normalize_requirement(requirement: str) -> str:
    """Extrahiert den Paketnamen aus einer Requirements-Zeile."""
    cleaned = requirement.split("#", 1)[0].strip()
    cleaned = cleaned.split(";", 1)[0].strip()
    if not cleaned:
        return ""
    name_part = re.split(r"[<=>~!]", cleaned, maxsplit=1)[0]
    name_part = name_part.split("[", 1)[0].strip()
    return name_part


def _module_name_for_package(package_name: str) -> str:
    """Gibt den Modulnamen zur Abhaengigkeit zurueck."""
    if not package_name:
        return ""
    return _MODULE_ALIASES.get(package_name, package_name)


def _missing_modules_from_requirements(requirements_path: Path) -> list[str]:
    """Prueft Requirements und liefert fehlende Modulnamen zurueck."""
    missing = []
    for line in requirements_path.read_text(encoding="utf-8").splitlines():
        package_name = _normalize_requirement(line)
        if not package_name:
            continue
        module_name = _module_name_for_package(package_name)
        if module_name and importlib.util.find_spec(module_name) is None:
            missing.append(module_name)
    return missing


def ensure_requirements(requirements_path: Path) -> None:
    """Installiert fehlende Abhaengigkeiten aus der Requirements-Datei."""
    missing = _missing_modules_from_requirements(requirements_path)
    if not missing:
        return
    print(
        "Fehlende Abhaengigkeiten erkannt: "
        f"{', '.join(sorted(set(missing)))}. Installation wird gestartet..."
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
        check=True,
    )


def ensure_packages(packages: Iterable[str]) -> None:
    """Installiert einzelne Pakete, falls deren Module fehlen."""
    missing = [
        package
        for package in packages
        if importlib.util.find_spec(_module_name_for_package(package)) is None
    ]
    if not missing:
        return
    print(
        "Fehlende Zusatzpakete erkannt: "
        f"{', '.join(sorted(set(missing)))}. Installation wird gestartet..."
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", *sorted(set(missing))],
        check=True,
    )
