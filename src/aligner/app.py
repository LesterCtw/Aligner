from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Aligner")
        self.resize(1200, 760)

        toolbar = QToolBar("Main")
        toolbar.addWidget(QPushButton("Open Folder"))
        toolbar.addWidget(QPushButton("Run Alignment"))
        toolbar.addWidget(QPushButton("Export Preview Stack"))
        self.addToolBar(toolbar)

        left_panel = QLabel("Project settings\n\nNo folder loaded")
        left_panel.setMinimumWidth(260)
        left_panel.setAlignment(Qt.AlignmentFlag.AlignTop)

        viewer = QLabel("2D Slice Viewer")
        viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        viewer.setStyleSheet("background: #202124; color: #f1f3f4;")

        side_by_side = QHBoxLayout()
        side_by_side.addWidget(left_panel)
        side_by_side.addWidget(viewer, stretch=1)

        timeline = QSlider(Qt.Orientation.Horizontal)
        timeline.setMinimum(0)
        timeline.setMaximum(0)

        root = QVBoxLayout()
        root.addLayout(side_by_side, stretch=1)
        root.addWidget(timeline)

        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")


def run_gui() -> int:
    app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()

