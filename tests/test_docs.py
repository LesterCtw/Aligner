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
    assert "full threshold iso-surface extraction is not implemented yet" in readme.lower()
    assert "VTK + Qt" in context
    assert "Status: Accepted" in adr
    assert "Threshold Iso-surface Preview" in adr
    assert "opacity-based volume rendering" in adr
    assert "heavier dependency" in adr
