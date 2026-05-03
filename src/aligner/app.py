from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from aligner.io import load_raw_stack
from aligner.models import ProjectConfig, RawStack
from aligner.preview import generate_orthogonal_previews


def _array_to_display_uint8(array: np.ndarray) -> np.ndarray:
    if array.dtype == np.uint8:
        return np.ascontiguousarray(array)

    min_value = float(np.min(array))
    max_value = float(np.max(array))
    if max_value <= min_value:
        return np.zeros(array.shape, dtype=np.uint8)

    scaled = (array.astype(np.float32) - min_value) * (255.0 / (max_value - min_value))
    return np.ascontiguousarray(np.clip(scaled, 0, 255).astype(np.uint8))


def _array_to_pixmap(array: np.ndarray) -> QPixmap:
    display = _array_to_display_uint8(array)
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Aligner")
        self.resize(1200, 760)
        self.config = ProjectConfig()
        self.raw_stack: RawStack | None = None

        toolbar = QToolBar("Main")
        open_button = QPushButton("Open Folder")
        open_button.clicked.connect(self.open_folder)
        toolbar.addWidget(open_button)
        run_button = QPushButton("Run Alignment")
        run_button.setEnabled(False)
        toolbar.addWidget(run_button)
        export_button = QPushButton("Export Preview Stack")
        export_button.setEnabled(False)
        toolbar.addWidget(export_button)
        self.addToolBar(toolbar)

        self.left_panel = QLabel("Project settings\n\nNo folder loaded")
        self.left_panel.setMinimumWidth(300)
        self.left_panel.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.left_panel.setWordWrap(True)

        self.viewer = ImageView("2D Slice Viewer")
        self.xy_preview = ImageView("Raw XY")
        self.xz_preview = ImageView("Raw XZ")
        self.yz_preview = ImageView("Raw YZ")

        previews = QGridLayout()
        previews.addWidget(QLabel("Raw XY"), 0, 0)
        previews.addWidget(QLabel("Raw XZ"), 0, 1)
        previews.addWidget(QLabel("Raw YZ"), 0, 2)
        previews.addWidget(self.xy_preview, 1, 0)
        previews.addWidget(self.xz_preview, 1, 1)
        previews.addWidget(self.yz_preview, 1, 2)

        side_by_side = QHBoxLayout()
        side_by_side.addWidget(self.left_panel)
        side_by_side.addWidget(self.viewer, stretch=1)

        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setMinimum(0)
        self.timeline.setMaximum(0)
        self.timeline.valueChanged.connect(self.show_slice)

        root = QVBoxLayout()
        root.addLayout(side_by_side, stretch=1)
        root.addLayout(previews)
        root.addWidget(self.timeline)

        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

    def open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Open Raw Stack Folder")
        if not folder:
            return
        self.load_folder(Path(folder))

    def load_folder(self, folder: Path) -> None:
        try:
            self.raw_stack = load_raw_stack(folder, slice_spacing_nm=self.config.slice_spacing_nm)
        except (OSError, ValueError) as error:
            self.raw_stack = None
            self.timeline.setMaximum(0)
            self.left_panel.setText(f"Project settings\n\nLoad failed:\n{error}")
            self.statusBar().showMessage(f"Load failed: {error}")
            return

        self.config.input_folder = str(folder)
        self.timeline.setMaximum(max(0, len(self.raw_stack.slices) - 1))
        self.timeline.setValue(0)
        self._update_stack_summary()
        self.show_slice(0)
        self.statusBar().showMessage(f"Loaded {len(self.raw_stack.slices)} raw slices")

    def show_slice(self, slice_index: int) -> None:
        if self.raw_stack is None:
            return

        previews = generate_orthogonal_previews(self.raw_stack, slice_index=slice_index)
        self.viewer.show_array(previews.xy)
        self.xy_preview.show_array(previews.xy)
        self.xz_preview.show_array(previews.xz)
        self.yz_preview.show_array(previews.yz)
        self.statusBar().showMessage(
            f"Showing raw slice {slice_index + 1} of {len(self.raw_stack.slices)}"
        )

    def _update_stack_summary(self) -> None:
        if self.raw_stack is None:
            return

        files = [record.filename for record in self.raw_stack.slices]
        preview_names = files[:8]
        if len(files) > len(preview_names):
            preview_names.append(f"... {len(files) - len(preview_names)} more")

        first = self.raw_stack.slices[0]
        self.left_panel.setText(
            "Project settings\n\n"
            f"Folder: {self.config.input_folder}\n"
            f"Slices: {len(self.raw_stack.slices)}\n"
            f"Size: {first.width} x {first.height}\n"
            f"Dtype: {first.dtype}\n"
            f"Slice spacing: {self.raw_stack.slice_spacing_nm:g} nm\n\n"
            "Natural file order:\n"
            + "\n".join(preview_names)
        )


def run_gui() -> int:
    app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
