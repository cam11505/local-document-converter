"""Verify that a release wheel contains only project code and approved metadata."""

from __future__ import annotations

import argparse
import re
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

_BINARY_OR_MODEL_SUFFIXES = {
    ".bin",
    ".dll",
    ".dylib",
    ".model",
    ".onnx",
    ".pt",
    ".pth",
    ".pyd",
    ".safetensors",
    ".so",
}
_PROJECT_PREFIX = "local_document_converter/"
_DIST_INFO_PATTERN = re.compile(r"local_document_converter-[^/]+\.dist-info/")


def verify_wheel(path: Path) -> list[str]:
    """Return archive members after enforcing the release artifact boundary."""
    with ZipFile(path) as archive:
        names = archive.namelist()
        metadata_name = next((name for name in names if name.endswith(".dist-info/METADATA")), None)
        if metadata_name is None:
            raise ValueError("wheel does not contain dist-info/METADATA")
        metadata = archive.read(metadata_name).decode("utf-8")

    if "License-Expression: MIT" not in metadata:
        raise ValueError("wheel metadata does not declare License-Expression: MIT")
    if not any(name.endswith(".dist-info/licenses/LICENSE") for name in names):
        raise ValueError("wheel does not contain the project LICENSE")

    unexpected = [
        name
        for name in names
        if not name.startswith(_PROJECT_PREFIX) and _DIST_INFO_PATTERN.match(name) is None
    ]
    if unexpected:
        raise ValueError(f"wheel contains unexpected top-level members: {unexpected}")

    bundled_binaries = [
        name for name in names if PurePosixPath(name).suffix.lower() in _BINARY_OR_MODEL_SUFFIXES
    ]
    if bundled_binaries:
        raise ValueError(f"wheel bundles binary or model artifacts: {bundled_binaries}")
    return names


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    names = verify_wheel(args.wheel)
    print(f"Verified {args.wheel.name}: {len(names)} entries, no bundled binary/model artifacts")


if __name__ == "__main__":
    main()
