from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_doc(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_context_defines_v1_domain_terms() -> None:
    context = read_doc("CONTEXT.md")

    required_terms = [
        "Preview Alignment",
        "Raw Stack",
        "Aligned Stack",
        "Stack Physical Spacing",
        "Bad Slice",
        "Alignment-Unusable",
        "RAFT Padding",
        "Aligned Crop Region",
        "Threshold Iso-surface Preview",
        "Orthogonal Preview",
    ]

    for term in required_terms:
        assert f"## {term}" in context


def test_readme_documents_v1_runtime_and_scope() -> None:
    readme = read_doc("README.md")

    required_phrases = [
        "Windows 11 + NVIDIA CUDA GPU",
        "macOS is for development and tiny smoke/mock checks only",
        "not metrology-grade 3D reconstruction",
        "stack-level robust range normalization",
        "grayscale-to-3-channel",
        "Balanced",
        "Bad Slice replacement is preview-only",
        "Threshold Iso-surface Preview",
        "Orthogonal Preview",
        "Implemented now:",
        "Not implemented yet:",
    ]

    for phrase in required_phrases:
        assert phrase in readme


def test_docs_record_vtk_qt_rendering_shell_decision() -> None:
    readme = read_doc("README.md")
    context = read_doc("CONTEXT.md")
    adr = read_doc("docs/adr/0001-vtk-qt-threshold-iso-surface-preview.md")

    assert "VTK + Qt 3D preview rendering shell" in readme
    assert "Raw Stack threshold iso-surface rendering from a display-only preview volume" in readme
    assert "Aligned Stack threshold iso-surface rendering after Run Alignment" in readme
    assert "VTK + Qt" in context
    assert "Status: Accepted" in adr
    assert "Threshold Iso-surface Preview" in adr
    assert "opacity-based volume rendering" in adr
    assert "heavier dependency" in adr


def test_readme_records_600_slice_threshold_preview_acceptance_status() -> None:
    readme = read_doc("README.md")
    normalized = " ".join(readme.split())

    assert "600-slice Threshold Iso-surface Preview acceptance" in readme
    assert "Issue #22" in readme
    assert "manual camera interaction acceptance remains pending" in normalized


def test_docs_record_windows_python_3128_pip_setup_workflow() -> None:
    readme = read_doc("README.md")
    setup_doc = read_doc("docs/windows-pip-setup.md")
    acceptance_doc = read_doc("docs/windows-cuda-acceptance.md")

    assert "Windows 11 + Python 3.12.8 pip-only setup" in readme
    assert "Python 3.12.8" in setup_doc
    assert "python -m pip install -e \".[dev]\"" in setup_doc
    assert "uv sync" not in setup_doc
    assert "uv run" not in setup_doc
    assert "Python 3.12.8" in acceptance_doc
    assert "python -m pip install -e \".[dev]\"" in acceptance_doc
    assert "uv sync" not in acceptance_doc
    assert "uv run" not in acceptance_doc
