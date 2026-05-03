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


FORBIDDEN_PREVIEW_EXPORT_KEYS = {
    "threshold",
    "threshold_value",
    "applied_threshold",
    "camera",
    "camera_state",
    "mesh",
    "meshes",
    "surface",
    "surfaces",
    "screenshot",
    "screenshots",
    "preview_settings",
    "preview_ui_settings",
    "preview_state",
}


def assert_no_preview_state_exported(metadata: object) -> None:
    if isinstance(metadata, dict):
        exported_keys = {str(key) for key in metadata}
        assert exported_keys.isdisjoint(FORBIDDEN_PREVIEW_EXPORT_KEYS)
        for value in metadata.values():
            assert_no_preview_state_exported(value)
    elif isinstance(metadata, list):
        for item in metadata:
            assert_no_preview_state_exported(item)


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


def test_run_alignment_refreshes_3d_preview_from_aligned_stack(tmp_path: Path) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    base = np.arange(4 * 5, dtype=np.uint16).reshape(4, 5)
    tifffile.imwrite(input_folder / "slice_1.tif", base)
    tifffile.imwrite(input_folder / "slice_2.tif", np.roll(base, shift=(1, 2), axis=(0, 1)))

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)

        assert window.threshold_iso_surface_preview.current_source_label() == "Raw Stack"

        window.run_alignment()

        assert window.aligned_stack is not None
        assert window.threshold_iso_surface_preview.current_source_label() == "Aligned Stack"
        assert window.threshold_iso_surface_preview.current_data_shape() == window.aligned_stack.data.shape
        assert "3D preview: Aligned Stack" in window.statusBar().currentMessage()
    finally:
        window.close()


def test_apply_threshold_after_alignment_keeps_3d_preview_on_aligned_stack(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    base = np.arange(4 * 5, dtype=np.uint16).reshape(4, 5)
    tifffile.imwrite(input_folder / "slice_1.tif", base)
    tifffile.imwrite(input_folder / "slice_2.tif", np.roll(base, shift=(1, 2), axis=(0, 1)))

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)
        window.run_alignment()

        window.threshold_value.setValue(12)
        window.apply_threshold_button.click()

        assert window.threshold_iso_surface_preview.current_source_label() == "Aligned Stack"
        assert window.threshold_iso_surface_preview.current_threshold() == 12
        assert window.threshold_iso_surface_preview.current_data_shape() == window.aligned_stack.data.shape
    finally:
        window.close()


def test_timeline_uses_aligned_stack_when_3d_preview_source_is_aligned(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    base = np.arange(4 * 5, dtype=np.uint16).reshape(4, 5)
    tifffile.imwrite(input_folder / "slice_1.tif", base)
    tifffile.imwrite(input_folder / "slice_2.tif", np.roll(base, shift=(1, 2), axis=(0, 1)))
    tifffile.imwrite(input_folder / "slice_3.tif", np.roll(base, shift=(2, 1), axis=(0, 1)))

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)
        window.run_alignment()

        window.timeline.setValue(1)

        assert window.threshold_iso_surface_preview.current_source_label() == "Aligned Stack"
        assert "Showing aligned slice 2 of 3" in window.statusBar().currentMessage()
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


def test_raw_stack_export_ignores_threshold_iso_surface_preview_state(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    tifffile.imwrite(input_folder / "slice_1.tif", np.full((2, 3), 10, dtype=np.uint16))
    tifffile.imwrite(input_folder / "slice_2.tif", np.full((2, 3), 100, dtype=np.uint16))
    output_folder = tmp_path / "identity-export"

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)
        window.threshold_value.setValue(40)
        window.apply_threshold_button.click()

        assert window.threshold_iso_surface_preview.current_source_label() == "Raw Stack"
        assert window.threshold_iso_surface_preview.current_threshold() == 40

        window.export_to_folder(output_folder)

        assert sorted(path.name for path in output_folder.iterdir()) == [
            "metadata.json",
            "slice_0000.tif",
            "slice_0001.tif",
        ]
        metadata = json.loads((output_folder / "metadata.json").read_text(encoding="utf-8"))
        assert metadata["preview_stack"]["alignment_status"] == "identity"
        assert_no_preview_state_exported(metadata)
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


def test_aligned_stack_export_ignores_threshold_iso_surface_preview_state(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    base = np.arange(4 * 5, dtype=np.uint16).reshape(4, 5)
    tifffile.imwrite(input_folder / "slice_1.tif", base)
    tifffile.imwrite(input_folder / "slice_2.tif", np.roll(base, shift=(1, 2), axis=(0, 1)))
    output_folder = tmp_path / "aligned-export"

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)
        window.run_alignment()
        window.threshold_value.setValue(12)
        window.apply_threshold_button.click()

        assert window.threshold_iso_surface_preview.current_source_label() == "Aligned Stack"
        assert window.threshold_iso_surface_preview.current_threshold() == 12

        window.export_to_folder(output_folder)

        assert sorted(path.name for path in output_folder.iterdir()) == [
            "metadata.json",
            "slice_0000.tif",
            "slice_0001.tif",
        ]
        metadata = json.loads((output_folder / "metadata.json").read_text(encoding="utf-8"))
        assert metadata["preview_stack"]["alignment_status"] == "constrained_raft"
        assert_no_preview_state_exported(metadata)
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


def test_open_folder_flow_computes_default_threshold_after_raw_stack_load(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    tifffile.imwrite(input_folder / "slice_1.tif", np.full((2, 4), 10, dtype=np.uint8))
    tifffile.imwrite(input_folder / "slice_2.tif", np.full((2, 4), 100, dtype=np.uint8))

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)

        window.load_folder(input_folder)

        assert window.threshold_slider.isEnabled()
        assert window.threshold_value.isEnabled()
        assert window.apply_threshold_button.isEnabled()
        assert window.threshold_slider.value() == 10
        assert window.threshold_value.value() == 10
        assert window.applied_threshold == 10
        assert "Otsu threshold: 10" in window.threshold_summary.text()
    finally:
        window.close()


def test_open_folder_flow_prepares_raw_stack_iso_surface_preview(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    tifffile.imwrite(input_folder / "slice_1.tif", np.full((2, 4), 10, dtype=np.uint8))
    tifffile.imwrite(input_folder / "slice_2.tif", np.full((2, 4), 100, dtype=np.uint8))

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)

        assert window.threshold_iso_surface_preview.current_source_label() == "Raw Stack"
        assert window.threshold_iso_surface_preview.current_threshold() == 10
        assert window.threshold_iso_surface_preview.current_spacing_nm() == (25.0, 25.0, 10.0)
    finally:
        window.close()


def test_open_folder_flow_prepares_600_slice_raw_stack_iso_surface_preview(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    for index in range(600):
        value = 10 if index < 300 else 100
        tifffile.imwrite(
            input_folder / f"slice_{index:04d}.tif",
            np.full((4, 5), value, dtype=np.uint8),
        )

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)

        window.load_folder(input_folder)

        assert window.raw_stack is not None
        assert len(window.raw_stack.slices) == 600
        assert window.threshold_preview_volume is not None
        assert window.threshold_preview_volume.source_shape == (600, 4, 5)
        assert window.threshold_preview_volume.data.shape == (600, 4, 5)
        assert window.threshold_iso_surface_preview.current_source_label() == "Raw Stack"
        assert window.threshold_iso_surface_preview.current_data_shape() == (600, 4, 5)
        assert window.threshold_slider.isEnabled()
        assert window.threshold_value.isEnabled()
        assert "Otsu threshold" in window.threshold_summary.text()
        assert "Loaded 600 raw slices; 3D preview: Raw Stack" in window.statusBar().currentMessage()
    finally:
        window.close()


def test_open_folder_flow_reports_raw_stack_3d_preview_source(tmp_path: Path) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    tifffile.imwrite(input_folder / "slice_1.tif", np.full((2, 4), 10, dtype=np.uint8))
    tifffile.imwrite(input_folder / "slice_2.tif", np.full((2, 4), 100, dtype=np.uint8))

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)

        window.load_folder(input_folder)

        assert window.threshold_iso_surface_preview.current_source_label() == "Raw Stack"
        assert "3D preview: Raw Stack" in window.statusBar().currentMessage()
    finally:
        window.close()


def test_threshold_slider_changes_pending_threshold_without_applying(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    tifffile.imwrite(input_folder / "slice_1.tif", np.full((2, 4), 10, dtype=np.uint8))
    tifffile.imwrite(input_folder / "slice_2.tif", np.full((2, 4), 100, dtype=np.uint8))

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)

        window.threshold_slider.setValue(20)

        assert window.pending_threshold == 20
        assert window.threshold_value.value() == 20
        assert window.applied_threshold == 10
        assert window.applied_threshold_rebuilds == [10]
    finally:
        window.close()


def test_threshold_numeric_input_changes_pending_threshold_without_applying(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    tifffile.imwrite(input_folder / "slice_1.tif", np.full((2, 4), 10, dtype=np.uint8))
    tifffile.imwrite(input_folder / "slice_2.tif", np.full((2, 4), 100, dtype=np.uint8))

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)

        window.threshold_value.setValue(30)

        assert window.pending_threshold == 30
        assert window.threshold_slider.value() == 30
        assert window.applied_threshold == 10
        assert window.applied_threshold_rebuilds == [10]
    finally:
        window.close()


def test_apply_threshold_commits_pending_threshold_for_preview_rebuild(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    tifffile.imwrite(input_folder / "slice_1.tif", np.full((2, 4), 10, dtype=np.uint8))
    tifffile.imwrite(input_folder / "slice_2.tif", np.full((2, 4), 100, dtype=np.uint8))

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)
        window.threshold_slider.setValue(40)

        window.apply_threshold_button.click()

        assert window.pending_threshold == 40
        assert window.applied_threshold == 40
        assert window.applied_threshold_rebuilds == [10, 40]
    finally:
        window.close()


def test_applied_threshold_rebuilds_raw_stack_iso_surface_preview(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    tifffile.imwrite(input_folder / "slice_1.tif", np.full((2, 4), 10, dtype=np.uint8))
    tifffile.imwrite(input_folder / "slice_2.tif", np.full((2, 4), 100, dtype=np.uint8))

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)

        window.threshold_slider.setValue(40)

        assert window.threshold_iso_surface_preview.current_threshold() == 10

        window.apply_threshold_button.click()

        assert window.threshold_iso_surface_preview.current_source_label() == "Raw Stack"
        assert window.threshold_iso_surface_preview.current_threshold() == 40
    finally:
        window.close()


def test_enter_in_threshold_numeric_input_applies_pending_threshold(
    tmp_path: Path,
) -> None:
    get_qapp()
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    tifffile.imwrite(input_folder / "slice_1.tif", np.full((2, 4), 10, dtype=np.uint8))
    tifffile.imwrite(input_folder / "slice_2.tif", np.full((2, 4), 100, dtype=np.uint8))

    window = MainWindow()
    try:
        window.xy_pixel_size_value.setValue(25.0)
        window.load_folder(input_folder)
        window.threshold_value.setValue(50)

        window.threshold_value.lineEdit().returnPressed.emit()

        assert window.pending_threshold == 50
        assert window.applied_threshold == 50
        assert window.applied_threshold_rebuilds == [10, 50]
    finally:
        window.close()
