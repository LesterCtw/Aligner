from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
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
from aligner.app_messages import (
    alignment_success_message,
    export_success_message,
    load_success_message,
    show_slice_message,
)
from aligner.export import export_preview_stack
from aligner.image_view import ImageView
from aligner.io import load_raw_stack, spacing_to_nm
from aligner.models import AlignedStack, ProjectConfig, RawStack
from aligner.preview import (
    ThresholdPreviewVolume,
    generate_orthogonal_previews,
    generate_threshold_preview_volume,
)
from aligner.project_summary import format_project_summary
from aligner.threshold import (
    ThresholdControlState,
    compute_threshold_statistics,
    format_threshold_summary,
)
from aligner.vtk_preview import ThresholdIsoSurfacePreview


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
        self.threshold_preview_volume: ThresholdPreviewVolume | None = None
        self.threshold_state = ThresholdControlState.unavailable()
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
        self.threshold_iso_surface_preview = ThresholdIsoSurfacePreview()

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

        self.xy_preview_label = QLabel("XY")
        self.xz_preview_label = QLabel("XZ")
        self.yz_preview_label = QLabel("YZ")

        previews = QGridLayout()
        previews.addWidget(self.xy_preview_label, 0, 0)
        previews.addWidget(self.xz_preview_label, 0, 1)
        previews.addWidget(self.yz_preview_label, 0, 2)
        previews.addWidget(self.xy_preview, 1, 0)
        previews.addWidget(self.xz_preview, 1, 1)
        previews.addWidget(self.yz_preview, 1, 2)

        self.orthogonal_preview_panel = QWidget()
        self.orthogonal_preview_panel.setObjectName("orthogonalPreviewPanel")
        supporting_previews = QVBoxLayout()
        supporting_previews.addWidget(self.viewer, stretch=1)
        supporting_previews.addLayout(previews)
        self.orthogonal_preview_panel.setLayout(supporting_previews)

        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setMinimum(0)
        self.timeline.setMaximum(0)
        self.timeline.valueChanged.connect(self.show_slice)

        self.right_preview_layout = QVBoxLayout()
        self.right_preview_layout.addWidget(self.threshold_iso_surface_preview, stretch=2)
        self.right_preview_layout.addWidget(self.threshold_summary)
        self.right_preview_layout.addLayout(threshold_controls)
        self.right_preview_layout.addWidget(self.orthogonal_preview_panel, stretch=1)
        self.right_preview_layout.addWidget(self.timeline)

        root = QHBoxLayout()
        root.addWidget(self.left_panel)
        root.addLayout(self.right_preview_layout, stretch=1)

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
            self.threshold_preview_volume = None
            self._reset_threshold_controls()
            self.threshold_iso_surface_preview.clear_preview()
            self.timeline.setMaximum(0)
            self.run_button.setEnabled(False)
            self.export_button.setEnabled(False)
            self.left_panel.setText(f"Project settings\n\nLoad failed:\n{error}")
            self.statusBar().showMessage(f"Load failed: {error}")
            return

        self.config.input_folder = str(folder)
        self.aligned_stack = None
        self._prepare_threshold_controls()
        self._prepare_raw_stack_iso_surface_preview()
        self.timeline.setMaximum(max(0, len(self.raw_stack.slices) - 1))
        self.timeline.setValue(0)
        self.run_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self._update_stack_summary()
        self.show_slice(0)
        self.statusBar().showMessage(load_success_message(len(self.raw_stack.slices)))

    def run_alignment(self) -> None:
        if self.raw_stack is None:
            self.statusBar().showMessage("Alignment failed: no Raw Stack loaded")
            return

        self.aligned_stack = run_constrained_raft_alignment(
            self.raw_stack,
            max_pair_distance=self.config.max_pair_distance,
        )
        self._prepare_active_stack_iso_surface_preview()
        self.show_slice(self.timeline.value())
        self.statusBar().showMessage(alignment_success_message())

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

        self.statusBar().showMessage(export_success_message(self.aligned_stack, folder))

    def show_slice(self, slice_index: int) -> None:
        if self.raw_stack is None:
            return

        stack = self.aligned_stack if self.aligned_stack is not None else self.raw_stack
        previews = generate_orthogonal_previews(stack, slice_index=slice_index)
        self.viewer.show_array(previews.xy)
        self.xy_preview.show_array(previews.xy)
        self.xz_preview.show_array(previews.xz)
        self.yz_preview.show_array(previews.yz)
        self.statusBar().showMessage(
            show_slice_message(
                aligned=self.aligned_stack is not None,
                slice_index=slice_index,
                slice_count=len(self.raw_stack.slices),
            )
        )

    def apply_threshold(self) -> None:
        applied_threshold = self.threshold_state.apply_pending()
        if applied_threshold is None:
            return

        self._render_active_stack_iso_surface_preview()
        self.statusBar().showMessage(f"Applied threshold {applied_threshold}")

    def _prepare_threshold_controls(self) -> None:
        if self.raw_stack is None:
            self._reset_threshold_controls()
            return

        statistics = compute_threshold_statistics(self.raw_stack.data)
        self.threshold_state = ThresholdControlState.from_statistics(statistics)
        threshold = self.threshold_state.pending_threshold
        if threshold is None:
            return
        max_intensity = int(statistics.intensity_values[-1])

        self._syncing_threshold_controls = True
        try:
            self.threshold_slider.setRange(0, max_intensity)
            self.threshold_value.setRange(0, max_intensity)
            self.threshold_slider.setValue(threshold)
            self.threshold_value.setValue(threshold)
        finally:
            self._syncing_threshold_controls = False

        self.threshold_slider.setEnabled(True)
        self.threshold_value.setEnabled(True)
        self.apply_threshold_button.setEnabled(True)
        self.threshold_summary.setText(format_threshold_summary(statistics))

    def _reset_threshold_controls(self) -> None:
        self.threshold_state = ThresholdControlState.unavailable()

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

    def _prepare_raw_stack_iso_surface_preview(self) -> None:
        if self.raw_stack is None:
            self.threshold_preview_volume = None
            self.threshold_iso_surface_preview.clear_preview()
            return

        self.threshold_preview_volume = generate_threshold_preview_volume(self.raw_stack)
        self._render_active_stack_iso_surface_preview()

    def _prepare_active_stack_iso_surface_preview(self) -> None:
        stack = self._active_preview_stack()
        if stack is None:
            self.threshold_preview_volume = None
            self.threshold_iso_surface_preview.clear_preview()
            return

        self.threshold_preview_volume = generate_threshold_preview_volume(stack)
        self._render_active_stack_iso_surface_preview()

    def _render_active_stack_iso_surface_preview(self) -> None:
        if self.threshold_preview_volume is None or self.applied_threshold is None:
            return

        self.threshold_iso_surface_preview.show_iso_surface(
            self.threshold_preview_volume,
            threshold=self.applied_threshold,
            source_label=self._active_preview_source_label(),
        )

    def _active_preview_stack(self) -> RawStack | AlignedStack | None:
        if self.aligned_stack is not None:
            return self.aligned_stack
        return self.raw_stack

    def _active_preview_source_label(self) -> str:
        if self.aligned_stack is not None:
            return "Aligned Stack"
        return "Raw Stack"

    def _set_pending_threshold_from_slider(self, value: int) -> None:
        if self._syncing_threshold_controls:
            return

        self.threshold_state.set_pending(value)
        self._syncing_threshold_controls = True
        try:
            self.threshold_value.setValue(value)
        finally:
            self._syncing_threshold_controls = False

    def _set_pending_threshold_from_input(self, value: int) -> None:
        if self._syncing_threshold_controls:
            return

        self.threshold_state.set_pending(value)
        self._syncing_threshold_controls = True
        try:
            self.threshold_slider.setValue(value)
        finally:
            self._syncing_threshold_controls = False

    def _update_stack_summary(self) -> None:
        if self.raw_stack is None:
            return

        self.left_panel.setText(
            format_project_summary(
                self.raw_stack,
                input_folder=self.config.input_folder,
            )
        )

    @property
    def threshold_statistics(self):
        return self.threshold_state.statistics

    @property
    def pending_threshold(self) -> int | None:
        return self.threshold_state.pending_threshold

    @property
    def applied_threshold(self) -> int | None:
        return self.threshold_state.applied_threshold

    @property
    def applied_threshold_rebuilds(self) -> list[int]:
        return self.threshold_state.applied_threshold_rebuilds


def run_gui() -> int:
    app = QApplication([])
    icon = load_application_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    window = MainWindow()
    window.show()
    return app.exec()
