from __future__ import annotations

import os

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from aligner.app import MainWindow  # noqa: E402
from aligner.preview import ThresholdPreviewVolume  # noqa: E402
from aligner.vtk_preview import ThresholdIsoSurfacePreview  # noqa: E402


def get_qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_app_environment_imports_vtk_qt_integration() -> None:
    from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

    assert QVTKRenderWindowInteractor is not None


def test_main_window_shows_vtk_preview_shell_above_supporting_orthogonal_preview() -> None:
    get_qapp()

    window = MainWindow()
    try:
        vtk_preview = window.findChild(
            ThresholdIsoSurfacePreview,
            "thresholdIsoSurfacePreview",
        )
        orthogonal_panel = window.findChild(QWidget, "orthogonalPreviewPanel")

        assert vtk_preview is not None
        assert orthogonal_panel is not None
        assert vtk_preview.supported_camera_interactions() == frozenset(
            {"rotate", "zoom", "pan"}
        )
        assert window.viewer.parentWidget() is orthogonal_panel
        assert window.right_preview_layout.indexOf(vtk_preview) < window.right_preview_layout.indexOf(
            orthogonal_panel
        )
    finally:
        window.close()


def test_supporting_orthogonal_preview_labels_are_stack_neutral() -> None:
    get_qapp()

    window = MainWindow()
    try:
        assert window.xy_preview_label.text() == "XY"
        assert window.xz_preview_label.text() == "XZ"
        assert window.yz_preview_label.text() == "YZ"
    finally:
        window.close()


def test_vtk_preview_accepts_threshold_iso_surface_volume() -> None:
    get_qapp()
    preview = ThresholdIsoSurfacePreview()
    volume = ThresholdPreviewVolume(
        data=np.zeros((2, 3, 4), dtype=np.uint8),
        spacing_nm=(5.0, 5.0, 20.0),
        source_shape=(2, 3, 4),
    )
    try:
        preview.show_iso_surface(volume, threshold=25, source_label="Raw Stack")

        assert preview.current_source_label() == "Raw Stack"
        assert preview.current_threshold() == 25
        assert preview.current_spacing_nm() == (5.0, 5.0, 20.0)
        assert preview.current_data_shape() == (2, 3, 4)
    finally:
        preview.close()
