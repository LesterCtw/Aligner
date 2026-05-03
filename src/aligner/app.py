from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from aligner.alignment import run_constrained_raft_alignment
from aligner.app_icon import load_application_icon
from aligner.export import export_preview_stack
from aligner.io import load_raw_stack, spacing_to_nm
from aligner.models import AlignedStack, ProjectConfig, RawStack
from aligner.preview import generate_orthogonal_previews
from aligner.threshold import ThresholdStatistics, compute_threshold_statistics


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
        icon = load_application_icon()
        if not icon.isNull():
            self.setWindowIcon(icon)
        self.resize(1200, 760)
        self.config = ProjectConfig()
        self.raw_stack: RawStack | None = None
        self.aligned_stack: AlignedStack | None = None
        self.threshold_statistics: ThresholdStatistics | None = None
        self.pending_threshold: int | None = None
        self.applied_threshold: int | None = None
        self.applied_threshold_rebuilds: list[int] = []
        self._syncing_threshold_controls = False

        toolbar = QToolBar("Main")
        open_button = QPushButton("Open Folder")
        open_button.clicked.connect(self.open_folder)
        toolbar.addWidget(open_button)
        toolbar.addWidget(QLabel("Slice spacing"))
        self.spacing_value = QDoubleSpinBox()
        self.spacing_value.setRange(0.001, 1_000_000.0)
        self.spacing_value.setDecimals(3)
        self.spacing_value.setValue(self.config.slice_spacing_nm)
        toolbar.addWidget(self.spacing_value)
        self.spacing_unit = QComboBox()
        self.spacing_unit.addItems(["nm", "um"])
        toolbar.addWidget(self.spacing_unit)
        toolbar.addWidget(QLabel("XY pixel size"))
        self.xy_pixel_size_value = QDoubleSpinBox()
        self.xy_pixel_size_value.setRange(0.0, 1_000_000.0)
        self.xy_pixel_size_value.setDecimals(3)
        self.xy_pixel_size_value.setValue(self.config.xy_pixel_size_nm)
        self.xy_pixel_size_value.setSuffix(" nm")
        toolbar.addWidget(self.xy_pixel_size_value)
        self.run_button = QPushButton("Run Alignment")
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self.run_alignment)
        toolbar.addWidget(self.run_button)
        self.export_button = QPushButton("Export Preview Stack")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_preview_stack)
        toolbar.addWidget(self.export_button)
        self.addToolBar(toolbar)

        self.left_panel = QLabel("Project settings\n\nNo folder loaded")
        self.left_panel.setMinimumWidth(300)
        self.left_panel.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.left_panel.setWordWrap(True)

        self.viewer = ImageView("2D Slice Viewer")
        self.xy_preview = ImageView("Raw XY")
        self.xz_preview = ImageView("Raw XZ")
        self.yz_preview = ImageView("Raw YZ")

        self.threshold_summary = QLabel("Threshold histogram unavailable")
        self.threshold_summary.setWordWrap(True)
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setEnabled(False)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(0)
        self.threshold_slider.valueChanged.connect(self._set_pending_threshold_from_slider)
        self.threshold_value = QSpinBox()
        self.threshold_value.setEnabled(False)
        self.threshold_value.setMinimum(0)
        self.threshold_value.setMaximum(0)
        self.threshold_value.valueChanged.connect(self._set_pending_threshold_from_input)
        self.threshold_value.lineEdit().returnPressed.connect(self.apply_threshold)
        self.apply_threshold_button = QPushButton("Apply")
        self.apply_threshold_button.setEnabled(False)
        self.apply_threshold_button.clicked.connect(self.apply_threshold)

        threshold_controls = QHBoxLayout()
        threshold_controls.addWidget(QLabel("Threshold"))
        threshold_controls.addWidget(self.threshold_slider, stretch=1)
        threshold_controls.addWidget(self.threshold_value)
        threshold_controls.addWidget(self.apply_threshold_button)

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
        root.addWidget(self.threshold_summary)
        root.addLayout(threshold_controls)
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
            self.config.slice_spacing_nm = spacing_to_nm(
                self.spacing_value.value(),
                self.spacing_unit.currentText(),
            )
            self.config.xy_pixel_size_nm = self.xy_pixel_size_value.value()
            self.raw_stack = load_raw_stack(
                folder,
                slice_spacing_nm=self.config.slice_spacing_nm,
                xy_pixel_size_nm=self.config.xy_pixel_size_nm,
            )
        except (OSError, ValueError) as error:
            self.raw_stack = None
            self.aligned_stack = None
            self._reset_threshold_controls()
            self.timeline.setMaximum(0)
            self.run_button.setEnabled(False)
            self.export_button.setEnabled(False)
            self.left_panel.setText(f"Project settings\n\nLoad failed:\n{error}")
            self.statusBar().showMessage(f"Load failed: {error}")
            return

        self.config.input_folder = str(folder)
        self.aligned_stack = None
        self._prepare_threshold_controls()
        self.timeline.setMaximum(max(0, len(self.raw_stack.slices) - 1))
        self.timeline.setValue(0)
        self.run_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self._update_stack_summary()
        self.show_slice(0)
        self.statusBar().showMessage(f"Loaded {len(self.raw_stack.slices)} raw slices")

    def run_alignment(self) -> None:
        if self.raw_stack is None:
            self.statusBar().showMessage("Alignment failed: no Raw Stack loaded")
            return

        self.aligned_stack = run_constrained_raft_alignment(
            self.raw_stack,
            max_pair_distance=self.config.max_pair_distance,
        )
        self.show_slice(self.timeline.value())
        self.statusBar().showMessage("Generated constrained RAFT Aligned Stack")

    def export_preview_stack(self) -> None:
        if self.raw_stack is None:
            self.statusBar().showMessage("Export failed: no Raw Stack loaded")
            return

        folder = QFileDialog.getExistingDirectory(self, "Export Preview Stack")
        if not folder:
            return
        self.export_to_folder(Path(folder))

    def export_to_folder(self, folder: Path) -> None:
        if self.raw_stack is None:
            self.statusBar().showMessage("Export failed: no Raw Stack loaded")
            return

        stack = self.aligned_stack if self.aligned_stack is not None else self.raw_stack
        try:
            export_preview_stack(stack, folder)
        except (OSError, ValueError) as error:
            self.statusBar().showMessage(f"Export failed: {error}")
            return

        export_label = "identity"
        if self.aligned_stack is not None:
            export_label = (
                "constrained RAFT"
                if self.aligned_stack.alignment_status == "constrained_raft"
                else "phase-only"
            )
        self.statusBar().showMessage(f"Exported {export_label} Preview Stack to {folder}")

    def show_slice(self, slice_index: int) -> None:
        if self.raw_stack is None:
            return

        stack = self.aligned_stack if self.aligned_stack is not None else self.raw_stack
        previews = generate_orthogonal_previews(stack, slice_index=slice_index)
        self.viewer.show_array(previews.xy)
        self.xy_preview.show_array(previews.xy)
        self.xz_preview.show_array(previews.xz)
        self.yz_preview.show_array(previews.yz)
        stack_label = "aligned" if self.aligned_stack is not None else "raw"
        self.statusBar().showMessage(
            f"Showing {stack_label} slice {slice_index + 1} of {len(self.raw_stack.slices)}"
        )

    def apply_threshold(self) -> None:
        if self.pending_threshold is None:
            return

        self.applied_threshold = self.pending_threshold
        self.applied_threshold_rebuilds.append(self.applied_threshold)
        self.statusBar().showMessage(f"Applied threshold {self.applied_threshold}")

    def _prepare_threshold_controls(self) -> None:
        if self.raw_stack is None:
            self._reset_threshold_controls()
            return

        self.threshold_statistics = compute_threshold_statistics(self.raw_stack.data)
        threshold = self.threshold_statistics.otsu_threshold
        max_intensity = int(self.threshold_statistics.intensity_values[-1])

        self._syncing_threshold_controls = True
        try:
            self.threshold_slider.setRange(0, max_intensity)
            self.threshold_value.setRange(0, max_intensity)
            self.threshold_slider.setValue(threshold)
            self.threshold_value.setValue(threshold)
        finally:
            self._syncing_threshold_controls = False

        self.pending_threshold = threshold
        self.applied_threshold = threshold
        self.applied_threshold_rebuilds = [threshold]
        self.threshold_slider.setEnabled(True)
        self.threshold_value.setEnabled(True)
        self.apply_threshold_button.setEnabled(True)
        self.threshold_summary.setText(self._format_threshold_summary(self.threshold_statistics))

    def _reset_threshold_controls(self) -> None:
        self.threshold_statistics = None
        self.pending_threshold = None
        self.applied_threshold = None
        self.applied_threshold_rebuilds = []

        self._syncing_threshold_controls = True
        try:
            self.threshold_slider.setRange(0, 0)
            self.threshold_value.setRange(0, 0)
            self.threshold_slider.setValue(0)
            self.threshold_value.setValue(0)
        finally:
            self._syncing_threshold_controls = False

        self.threshold_slider.setEnabled(False)
        self.threshold_value.setEnabled(False)
        self.apply_threshold_button.setEnabled(False)
        self.threshold_summary.setText("Threshold histogram unavailable")

    def _set_pending_threshold_from_slider(self, value: int) -> None:
        if self._syncing_threshold_controls:
            return

        self.pending_threshold = value
        self._syncing_threshold_controls = True
        try:
            self.threshold_value.setValue(value)
        finally:
            self._syncing_threshold_controls = False

    def _set_pending_threshold_from_input(self, value: int) -> None:
        if self._syncing_threshold_controls:
            return

        self.pending_threshold = value
        self._syncing_threshold_controls = True
        try:
            self.threshold_slider.setValue(value)
        finally:
            self._syncing_threshold_controls = False

    def _format_threshold_summary(self, statistics: ThresholdStatistics) -> str:
        occupied = np.flatnonzero(statistics.histogram_counts)
        min_intensity = int(statistics.intensity_values[occupied[0]])
        max_intensity = int(statistics.intensity_values[occupied[-1]])
        voxel_count = int(statistics.histogram_counts.sum())
        return (
            f"Histogram: {voxel_count} voxels, intensity {min_intensity:g}-{max_intensity:g}; "
            f"Otsu threshold: {statistics.otsu_threshold:g}"
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
            f"Slice spacing: {self.raw_stack.slice_spacing_nm:g} nm\n"
            f"XY pixel size: {self.raw_stack.xy_pixel_size_nm:g} nm\n\n"
            "Natural file order:\n"
            + "\n".join(preview_names)
        )


def run_gui() -> int:
    app = QApplication([])
    icon = load_application_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    window = MainWindow()
    window.show()
    return app.exec()
