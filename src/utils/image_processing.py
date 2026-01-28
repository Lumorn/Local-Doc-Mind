"""Hilfsfunktionen fuer die Bildaufbereitung."""

from __future__ import annotations

from typing import List

import fitz
from PIL import Image


def pdf_to_images(pdf_path: str) -> List[Image.Image]:
    """Konvertiert ein PDF in eine Liste von PIL-Images mit hoher Aufloesung."""
    images: List[Image.Image] = []
    matrix = fitz.Matrix(3, 3)

    with fitz.open(pdf_path) as document:
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=matrix)
            try:
                mode = "RGB" if pixmap.alpha == 0 else "RGBA"
                image = Image.frombytes(mode, (pixmap.width, pixmap.height), pixmap.samples)
            finally:
                # Pixmap sofort freigeben, um Speicher zu sparen.
                del pixmap
            images.append(image)

    return images
