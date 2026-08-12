"""Generate a deterministic-shape SPDX 2.3 package inventory.

The input can be either the active Python environment or a JSON report produced by
``python -m pip install --dry-run --ignore-installed --report <path> ...``.  The
result is an audit draft: package metadata is preserved, while ambiguous or missing
license declarations remain ``NOASSERTION`` for human review.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5

_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")
_KNOWN_LICENSES = {
    "Apache 2.0": "Apache-2.0",
    "Apache License 2.0": "Apache-2.0",
    "Apache Software License": "Apache-2.0",
    "BSD-3-Clause": "BSD-3-Clause",
    "MIT": "MIT",
    "MIT License": "MIT",
    "MPL-2.0": "MPL-2.0",
}
_CLASSIFIER_LICENSES = {
    "License :: OSI Approved :: Apache Software License": "Apache-2.0",
    "License :: OSI Approved :: BSD License": "BSD-3-Clause",
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)": (
        "GPL-3.0-or-later"
    ),
}
_LEGACY_SPDX_LICENSES = {
    "0BSD",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "GPL-2.0-only",
    "GPL-2.0-or-later",
    "GPL-3.0-only",
    "GPL-3.0-or-later",
    "ISC",
    "LGPL-2.1-only",
    "LGPL-2.1-or-later",
    "LGPL-3.0-only",
    "LGPL-3.0-or-later",
    "MIT",
    "MPL-2.0",
    "PSF-2.0",
    "Unlicense",
    "Zlib",
}


def _looks_like_spdx_expression(value: str) -> bool:
    tokens = value.replace("(", " ").replace(")", " ").split()
    return bool(tokens) and all(
        token in _LEGACY_SPDX_LICENSES or token in {"AND", "OR"} for token in tokens
    )


def _normalise_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _declared_license(package_metadata: dict[str, Any]) -> tuple[str, str | None]:
    expression = package_metadata.get("license_expression") or package_metadata.get(
        "License-Expression"
    )
    if isinstance(expression, str) and expression.strip():
        return expression.strip(), None

    raw_license = package_metadata.get("license") or package_metadata.get("License")
    if isinstance(raw_license, str) and raw_license.strip():
        stripped = raw_license.strip()
        known = _KNOWN_LICENSES.get(stripped)
        if known is not None:
            return known, None
        if _looks_like_spdx_expression(stripped):
            return stripped, None
        return "NOASSERTION", f"Unnormalised package metadata license: {stripped[:200]}"

    classifiers = package_metadata.get("classifier") or package_metadata.get("Classifier") or []
    if isinstance(classifiers, str):
        classifiers = [classifiers]
    for classifier in classifiers:
        known = _CLASSIFIER_LICENSES.get(str(classifier))
        if known is not None:
            return known, None
    return "NOASSERTION", "Package metadata did not declare an SPDX-normalised license."


def _package_record(
    package_metadata: dict[str, Any],
    *,
    download_url: str | None = None,
    sha256: str | None = None,
) -> dict[str, Any]:
    name = str(package_metadata.get("name") or package_metadata.get("Name"))
    version = str(package_metadata.get("version") or package_metadata.get("Version"))
    normalised_name = _normalise_name(name)
    declared_license, license_comment = _declared_license(package_metadata)
    record: dict[str, Any] = {
        "SPDXID": f"SPDXRef-Package-{normalised_name}",
        "name": name,
        "versionInfo": version,
        "downloadLocation": download_url or "NOASSERTION",
        "filesAnalyzed": False,
        "licenseConcluded": "NOASSERTION",
        "licenseDeclared": declared_license,
        "copyrightText": "NOASSERTION",
        "externalRefs": [
            {
                "referenceCategory": "PACKAGE-MANAGER",
                "referenceType": "purl",
                "referenceLocator": (f"pkg:pypi/{quote(normalised_name)}@{quote(version)}"),
            }
        ],
    }
    if sha256:
        record["checksums"] = [{"algorithm": "SHA256", "checksumValue": sha256}]
    if license_comment:
        record["comment"] = license_comment
    return record


def _requirements(package_metadata: dict[str, Any]) -> list[str]:
    values = package_metadata.get("requires_dist") or package_metadata.get("Requires-Dist") or []
    if isinstance(values, str):
        values = [values]
    requirements: list[str] = []
    for value in values:
        match = _NAME_PATTERN.match(str(value))
        if match is not None:
            requirements.append(_normalise_name(match.group(0)))
    return requirements


def _from_environment() -> list[tuple[dict[str, Any], str | None, str | None]]:
    packages: list[tuple[dict[str, Any], str | None, str | None]] = []
    for distribution in metadata.distributions():
        package_metadata = {
            key: distribution.metadata.get_all(key) for key in distribution.metadata
        }
        flattened: dict[str, Any] = {}
        for key, values in package_metadata.items():
            if values is None:
                continue
            flattened[key] = values if len(values) > 1 else values[0]
        packages.append((flattened, None, None))
    return packages


def _from_pip_report(path: Path) -> list[tuple[dict[str, Any], str | None, str | None]]:
    report = json.loads(path.read_text(encoding="utf-8"))
    packages: list[tuple[dict[str, Any], str | None, str | None]] = []
    for item in report.get("install", []):
        package_metadata = item["metadata"]
        download_info = item.get("download_info", {})
        archive_info = download_info.get("archive_info", {})
        hashes = archive_info.get("hashes", {})
        packages.append((package_metadata, download_info.get("url"), hashes.get("sha256")))
    return packages


def generate_sbom(
    packages: list[tuple[dict[str, Any], str | None, str | None]], *, profile: str
) -> dict[str, Any]:
    unique: dict[str, tuple[dict[str, Any], str | None, str | None]] = {}
    for package_metadata, download_url, sha256 in packages:
        name = str(package_metadata.get("name") or package_metadata.get("Name"))
        unique[_normalise_name(name)] = (package_metadata, download_url, sha256)

    records = [
        _package_record(package_metadata, download_url=download_url, sha256=sha256)
        for package_metadata, download_url, sha256 in (unique[name] for name in sorted(unique))
    ]
    relationships: list[dict[str, str]] = []
    for record in records:
        relationships.append(
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": record["SPDXID"],
            }
        )
    for name in sorted(unique):
        package_metadata = unique[name][0]
        for requirement in sorted(set(_requirements(package_metadata))):
            if requirement in unique and requirement != name:
                relationships.append(
                    {
                        "spdxElementId": f"SPDXRef-Package-{name}",
                        "relationshipType": "DEPENDS_ON",
                        "relatedSpdxElement": f"SPDXRef-Package-{requirement}",
                    }
                )

    identity = "|".join(f"{record['name']}=={record['versionInfo']}" for record in records)
    namespace_id = uuid5(NAMESPACE_URL, f"local-document-converter:{profile}:{identity}")
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"local-document-converter-{profile}",
        "documentNamespace": f"https://local.invalid/spdx/{namespace_id}",
        "creationInfo": {
            "created": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "creators": ["Tool: scripts/generate_sbom.py"],
        },
        "documentDescribes": [record["SPDXID"] for record in records],
        "packages": records,
        "relationships": relationships,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--environment", action="store_true")
    source.add_argument("--pip-report", type=Path)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    packages = _from_environment() if args.environment else _from_pip_report(args.pip_report)
    sbom = generate_sbom(packages, profile=args.profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sbom, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(sbom['packages'])} packages to {args.output}")


if __name__ == "__main__":
    main()
