from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkFiltersSources import vtkCubeSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer

import vtkmodules.vtkRenderingOpenGL2  # noqa: F401  # Required VTK rendering backend.


class ThresholdIsoSurfacePreview(QWidget):
    """VTK-backed shell for the main Threshold Iso-surface Preview."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("thresholdIsoSurfacePreview")
        self.setMinimumSize(420, 280)

        label = QLabel("Threshold Iso-surface Preview")
        label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)

        self._vtk_widget: QVTKRenderWindowInteractor | None = None
        self._renderer: vtkRenderer | None = None
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


def _is_offscreen_qt() -> bool:
    app = QApplication.instance()
    return os.environ.get("QT_QPA_PLATFORM") == "offscreen" or (
        app is not None and app.platformName() == "offscreen"
    )
