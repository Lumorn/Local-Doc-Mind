"""Hilfsfunktionen fuer die Bildaufbereitung."""

from __future__ import annotations

from typing import TYPE_CHECKING

import fitz
from PIL import Image

if TYPE_CHECKING:
    from fitz import Page


def pdf_page_to_image(page: "Page") -> Image.Image:
    """Konvertiert eine PDF-Seite in ein PIL-Image mit hoher Aufloesung."""
    # Zoom-Faktor 3 fuer ca. 200-300 DPI, damit Tabellen schaerf bleiben.
    matrix = fitz.Matrix(3, 3)
    pixmap = page.get_pixmap(matrix=matrix)
    try:
        mode = "RGB" if pixmap.alpha == 0 else "RGBA"
        image = Image.frombytes(mode, (pixmap.width, pixmap.height), pixmap.samples)
    finally:
        # Pixmap sofort freigeben, um Speicher zu sparen.
        del pixmap
    return image
