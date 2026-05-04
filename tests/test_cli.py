from __future__ import annotations

from aligner import cli
from aligner.raft import RaftRuntimeProbe


def test_probe_prints_shared_raft_runtime_probe(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "probe_raft_runtime",
        lambda: RaftRuntimeProbe(
            torch_installed=True,
            torchvision_installed=True,
            torch_version="2.test",
            torchvision_version="0.test",
            cuda_available=True,
            cuda_device="Fake NVIDIA GPU",
        ),
    )

    result = cli.probe()

    assert result == 0
    output = capsys.readouterr().out
    assert "Core dependencies available." in output
    assert "torch 2.test" in output
    assert "Full Windows CUDA RAFT readiness: ready" in output
