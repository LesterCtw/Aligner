from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import tifffile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from aligner.app import MainWindow  # noqa: E402


def get_qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_export_preview_stack_action_enables_after_raw_stack_load(tmp_path: Path) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    tifffile.imwrite(input_folder / "slice_1.tif", np.zeros((2, 3), dtype=np.uint16))
    tifffile.imwrite(input_folder / "slice_2.tif", np.ones((2, 3), dtype=np.uint16))

    window = MainWindow()
    try:
        assert not window.export_button.isEnabled()

        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)

        assert window.export_button.isEnabled()
    finally:
        window.close()


def test_run_alignment_action_displays_constrained_raft_aligned_stack(tmp_path: Path) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    base = np.arange(4 * 5, dtype=np.uint16).reshape(4, 5)
    tifffile.imwrite(input_folder / "slice_1.tif", base)
    tifffile.imwrite(input_folder / "slice_2.tif", np.roll(base, shift=(1, 2), axis=(0, 1)))

    window = MainWindow()
    try:
        assert not window.run_button.isEnabled()

        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)
        window.run_button.click()

        assert window.aligned_stack is not None
        assert window.aligned_stack.alignment_status == "constrained_raft"
        np.testing.assert_array_equal(window.aligned_stack.data[1], base)
        assert "constrained RAFT Aligned Stack" in window.statusBar().currentMessage()
    finally:
        window.close()


def test_export_to_folder_reports_success_after_raw_stack_load(tmp_path: Path) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    tifffile.imwrite(input_folder / "slice_1.tif", np.zeros((2, 3), dtype=np.uint16))
    tifffile.imwrite(input_folder / "slice_2.tif", np.ones((2, 3), dtype=np.uint16))
    output_folder = tmp_path / "identity-export"

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)

        window.export_to_folder(output_folder)

        assert (output_folder / "slice_0000.tif").exists()
        assert (output_folder / "slice_0001.tif").exists()
        assert (output_folder / "metadata.json").exists()
        assert "Exported identity Preview Stack" in window.statusBar().currentMessage()
    finally:
        window.close()


def test_export_to_folder_uses_constrained_raft_aligned_stack_after_alignment(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    base = np.arange(4 * 5, dtype=np.uint16).reshape(4, 5)
    tifffile.imwrite(input_folder / "slice_1.tif", base)
    tifffile.imwrite(input_folder / "slice_2.tif", np.roll(base, shift=(1, 2), axis=(0, 1)))
    output_folder = tmp_path / "phase-export"

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)
        window.run_alignment()

        window.export_to_folder(output_folder)

        metadata = json.loads((output_folder / "metadata.json").read_text(encoding="utf-8"))
        assert metadata["preview_stack"]["alignment_status"] == "constrained_raft"
        assert "constrained RAFT Preview Stack" in window.statusBar().currentMessage()
    finally:
        window.close()


def test_open_folder_flow_uses_slice_spacing_controls(tmp_path: Path) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    tifffile.imwrite(input_folder / "slice_1.tif", np.zeros((2, 3), dtype=np.uint16))
    tifffile.imwrite(input_folder / "slice_2.tif", np.ones((2, 3), dtype=np.uint16))

    window = MainWindow()
    try:
        window.spacing_value.setValue(0.5)
        window.spacing_unit.setCurrentText("um")
        window.xy_pixel_size_value.setValue(25.0)

        window.load_folder(input_folder)

        assert window.raw_stack is not None
        assert window.raw_stack.slice_spacing_nm == 500.0
        assert [record.z_nm for record in window.raw_stack.slices] == [0.0, 500.0]
        assert "Slice spacing: 500 nm" in window.left_panel.text()
    finally:
        window.close()


def test_open_folder_flow_uses_xy_pixel_size_control_and_shows_summary(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    tifffile.imwrite(input_folder / "slice_1.tif", np.zeros((2, 3), dtype=np.uint16))

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)

        window.load_folder(input_folder)

        assert window.raw_stack is not None
        assert window.raw_stack.xy_pixel_size_nm == 25.0
        assert "XY pixel size: 25 nm" in window.left_panel.text()
    finally:
        window.close()
