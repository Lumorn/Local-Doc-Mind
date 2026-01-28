"""Hilfsfunktionen fuer die Bildaufbereitung."""

from __future__ import annotations

from typing import Iterator

import fitz
from PIL import Image


def pdf_to_images(pdf_path: str) -> Iterator[Image.Image]:
    """Konvertiert ein PDF in einen Generator von PIL-Images mit hoher Aufloesung."""
    matrix = fitz.Matrix(3, 3)
    document = fitz.open(pdf_path)
    try:
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=matrix)
            try:
                mode = "RGB" if pixmap.alpha == 0 else "RGBA"
                image = Image.frombytes(mode, (pixmap.width, pixmap.height), pixmap.samples)
            finally:
                # Pixmap und Page sofort freigeben, um Speicher zu sparen.
                del pixmap
                del page
            yield image
    finally:
        # Dokument schliessen, sobald der Generator aufgebraucht ist.
        document.close()
