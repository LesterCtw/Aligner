from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from vtkmodules.util.numpy_support import numpy_to_vtk
from vtkmodules.vtkCommonDataModel import vtkImageData
from vtkmodules.vtkFiltersCore import vtkFlyingEdges3D
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkFiltersSources import vtkCubeSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer

from aligner.preview import ThresholdPreviewVolume

import vtkmodules.vtkRenderingOpenGL2  # noqa: F401  # Required VTK rendering backend.


class ThresholdIsoSurfacePreview(QWidget):
    """VTK-backed shell for the main Threshold Iso-surface Preview."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("thresholdIsoSurfacePreview")
        self.setMinimumSize(420, 280)
        self._current_source_label: str | None = None
        self._current_threshold: int | None = None
        self._current_spacing_nm: tuple[float, float, float] | None = None
        self._current_data_shape: tuple[int, int, int] | None = None

        self._label = QLabel("Threshold Iso-surface Preview")
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self._vtk_widget: QVTKRenderWindowInteractor | None = None
        self._renderer: vtkRenderer | None = None
        self._placeholder_actor: vtkActor | None = None
        if _is_offscreen_qt():
            placeholder = QLabel("VTK preview shell")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("background: #14171a; color: #f1f3f4;")
            layout.addWidget(placeholder, stretch=1)
        else:
            self._vtk_widget = QVTKRenderWindowInteractor(self)
            self._renderer = vtkRenderer()
            self._renderer.SetBackground(0.08, 0.09, 0.10)
            self._vtk_widget.GetRenderWindow().AddRenderer(self._renderer)

            interactor = self._vtk_widget.GetRenderWindow().GetInteractor()
            interactor.SetInteractorStyle(vtkInteractorStyleTrackballCamera())

            self._add_placeholder_actor()
            self._renderer.ResetCamera()
            self._vtk_widget.Initialize()
            layout.addWidget(self._vtk_widget, stretch=1)

        self.setLayout(layout)

    def supported_camera_interactions(self) -> frozenset[str]:
        return frozenset({"rotate", "zoom", "pan"})

    def show_iso_surface(
        self,
        volume: ThresholdPreviewVolume,
        *,
        threshold: int,
        source_label: str,
    ) -> None:
        self._current_source_label = source_label
        self._current_threshold = threshold
        self._current_spacing_nm = volume.spacing_nm
        self._current_data_shape = volume.data.shape
        self._label.setText(f"Threshold Iso-surface Preview - {source_label}")
        self._render_iso_surface(volume, threshold)

    def clear_preview(self) -> None:
        self._current_source_label = None
        self._current_threshold = None
        self._current_spacing_nm = None
        self._current_data_shape = None
        self._label.setText("Threshold Iso-surface Preview")
        if self._renderer is not None:
            self._renderer.RemoveAllViewProps()
            self._add_placeholder_actor()
            self._renderer.ResetCamera()
            if self._vtk_widget is not None:
                self._vtk_widget.GetRenderWindow().Render()

    def current_source_label(self) -> str | None:
        return self._current_source_label

    def current_threshold(self) -> int | None:
        return self._current_threshold

    def current_spacing_nm(self) -> tuple[float, float, float] | None:
        return self._current_spacing_nm

    def current_data_shape(self) -> tuple[int, int, int] | None:
        return self._current_data_shape

    def _add_placeholder_actor(self) -> None:
        if self._renderer is None:
            return

        source = vtkCubeSource()
        source.SetXLength(1.0)
        source.SetYLength(1.0)
        source.SetZLength(0.45)

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(source.GetOutputPort())

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.35, 0.70, 0.95)
        actor.GetProperty().SetOpacity(0.85)

        self._renderer.AddActor(actor)
        self._placeholder_actor = actor

    def _render_iso_surface(self, volume: ThresholdPreviewVolume, threshold: int) -> None:
        if self._renderer is None or self._vtk_widget is None:
            return

        image = vtkImageData()
        z_slices, height, width = volume.data.shape
        image.SetDimensions(width, height, z_slices)
        image.SetSpacing(*volume.spacing_nm)

        scalars = numpy_to_vtk(
            num_array=volume.data.reshape(-1),
            deep=True,
        )
        scalars.SetName("intensity")
        image.GetPointData().SetScalars(scalars)

        iso_surface = vtkFlyingEdges3D()
        iso_surface.SetInputData(image)
        iso_surface.SetValue(0, float(threshold))

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(iso_surface.GetOutputPort())
        mapper.ScalarVisibilityOff()

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.35, 0.70, 0.95)
        actor.GetProperty().SetOpacity(0.90)

        self._renderer.RemoveAllViewProps()
        self._renderer.AddActor(actor)
        self._renderer.ResetCamera()
        self._vtk_widget.GetRenderWindow().Render()


def _is_offscreen_qt() -> bool:
    app = QApplication.instance()
    return os.environ.get("QT_QPA_PLATFORM") == "offscreen" or (
        app is not None and app.platformName() == "offscreen"
    )
