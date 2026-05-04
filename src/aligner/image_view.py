from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel


def array_to_display_uint8(array: np.ndarray) -> np.ndarray:
    if array.dtype == np.uint8:
        return np.ascontiguousarray(array)

    min_value = float(np.min(array))
    max_value = float(np.max(array))
    if max_value <= min_value:
        return np.zeros(array.shape, dtype=np.uint8)

    scaled = (array.astype(np.float32) - min_value) * (255.0 / (max_value - min_value))
    return np.ascontiguousarray(np.clip(scaled, 0, 255).astype(np.uint8))


def _array_to_pixmap(array: np.ndarray) -> QPixmap:
    display = array_to_display_uint8(array)
    height, width = display.shape
    image = QImage(
        display.data,
        width,
        height,
        display.strides[0],
        QImage.Format.Format_Grayscale8,
    ).copy()
    return QPixmap.fromImage(image)


class ImageView(QLabel):
    def __init__(self, title: str) -> None:
        super().__init__(title)
        self._title = title
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(180, 140)
        self.setStyleSheet("background: #202124; color: #f1f3f4;")

    def show_array(self, array: np.ndarray) -> None:
        pixmap = _array_to_pixmap(array)
        self.setPixmap(
            pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
