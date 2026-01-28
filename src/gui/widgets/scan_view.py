"""Scan-Ansicht fuer Dokumentbilder."""

from __future__ import annotations

from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QImage, QPen, QPixmap
from PyQt6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QWidget,
)


class ScanView(QWidget):
    """Zeigt das aktuelle Dokument und optionale Overlays an."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Szene und View fuer die Bilddarstellung vorbereiten.
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setRenderHints(self.view.renderHints())
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._box_items: list[QGraphicsRectItem] = []
        self._image_buffer: bytes | None = None

    def show_image(self, image_path: str) -> None:
        """Laedt ein Bild und skaliert es auf die Breite der Ansicht."""
        if not image_path:
            return

        pil_image = Image.open(image_path).convert("RGBA")
        self._image_buffer = pil_image.tobytes("raw", "RGBA")
        width, height = pil_image.size
        qimage = QImage(
            self._image_buffer,
            width,
            height,
            QImage.Format.Format_RGBA8888,
        )
        pixmap = QPixmap.fromImage(qimage)

        self.scene.clear()
        self._box_items.clear()
        self._pixmap_item = self.scene.addPixmap(pixmap)
        self._fit_width()

    def draw_boxes(self, boxes: list) -> None:
        """Zeichnet halbtransparente Rechtecke ueber dem Dokument."""
        for item in self._box_items:
            self.scene.removeItem(item)
        self._box_items.clear()

        if not boxes:
            return

        pen = QPen(QColor(57, 255, 20))
        pen.setWidth(2)
        brush = QBrush(QColor(57, 255, 20, 80))

        for box in boxes:
            x, y, width, height = box
            rect = QGraphicsRectItem(x, y, width, height)
            rect.setPen(pen)
            rect.setBrush(brush)
            rect.setZValue(10)
            self.scene.addItem(rect)
            self._box_items.append(rect)

    def resizeEvent(self, event) -> None:
        """Passt die Skalierung bei Groessenanpassungen an."""
        super().resizeEvent(event)
        self._fit_width()

    def _fit_width(self) -> None:
        """Skaliert das aktuelle Bild auf die volle Breite."""
        if self._pixmap_item is None:
            return

        pixmap = self._pixmap_item.pixmap()
        if pixmap.isNull():
            return

        view_width = max(1, self.view.viewport().width())
        scale_factor = view_width / pixmap.width()
        self.view.resetTransform()
        self.view.scale(scale_factor, scale_factor)
