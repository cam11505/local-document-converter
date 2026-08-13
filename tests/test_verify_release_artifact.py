from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest
from scripts.verify_release_artifact import verify_wheel


def _write_wheel(
    path: Path, *, metadata: str = "License-Expression: MIT\n", binary: bool = False
) -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr("local_document_converter/__init__.py", "")
        archive.writestr("local_document_converter-0.1.0.dist-info/METADATA", metadata)
        archive.writestr("local_document_converter-0.1.0.dist-info/licenses/LICENSE", "MIT")
        if binary:
            archive.writestr("local_document_converter/model.onnx", b"model")


def test_release_wheel_boundary_accepts_project_only_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "project.whl"
    _write_wheel(wheel)

    names = verify_wheel(wheel)

    assert "local_document_converter/__init__.py" in names


def test_release_wheel_boundary_rejects_bundled_model(tmp_path: Path) -> None:
    wheel = tmp_path / "project.whl"
    _write_wheel(wheel, binary=True)

    with pytest.raises(ValueError, match="binary or model"):
        verify_wheel(wheel)


def test_release_wheel_boundary_requires_mit_metadata(tmp_path: Path) -> None:
    wheel = tmp_path / "project.whl"
    _write_wheel(wheel, metadata="Name: local-document-converter\n")

    with pytest.raises(ValueError, match="License-Expression: MIT"):
        verify_wheel(wheel)
