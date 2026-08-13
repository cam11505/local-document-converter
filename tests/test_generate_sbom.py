from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "generate_sbom.py"


def test_generate_sbom_from_pip_report(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    output = tmp_path / "sbom.json"
    report.write_text(
        json.dumps(
            {
                "install": [
                    {
                        "metadata": {
                            "name": "Example_App",
                            "version": "1.0",
                            "license_expression": "MIT",
                            "requires_dist": ["Example-Dependency>=2"],
                        },
                        "download_info": {
                            "url": "https://example.invalid/example_app.whl",
                            "archive_info": {"hashes": {"sha256": "a" * 64}},
                        },
                    },
                    {
                        "metadata": {
                            "name": "Example-Dependency",
                            "version": "2.0",
                        },
                        "download_info": {},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--pip-report",
            str(report),
            "--profile",
            "test",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    sbom = json.loads(output.read_text(encoding="utf-8"))
    assert result.stdout.startswith("Wrote 2 packages")
    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert [package["name"] for package in sbom["packages"]] == [
        "Example_App",
        "Example-Dependency",
    ]
    assert sbom["packages"][0]["licenseDeclared"] == "MIT"
    assert sbom["packages"][1]["licenseDeclared"] == "NOASSERTION"
    assert {
        "spdxElementId": "SPDXRef-Package-example-app",
        "relationshipType": "DEPENDS_ON",
        "relatedSpdxElement": "SPDXRef-Package-example-dependency",
    } in sbom["relationships"]


def test_spdx_expression_in_legacy_license_field_is_preserved() -> None:
    from scripts.generate_sbom import generate_sbom

    sbom = generate_sbom(
        [({"name": "copyleft", "version": "1", "license": "LGPL-2.1-or-later"}, None, None)],
        profile="test",
    )

    assert sbom["packages"][0]["licenseDeclared"] == "LGPL-2.1-or-later"


def test_ambiguous_legacy_license_is_not_claimed_as_spdx() -> None:
    from scripts.generate_sbom import generate_sbom

    sbom = generate_sbom(
        [({"name": "ambiguous", "version": "1", "license": "Apache"}, None, None)],
        profile="test",
    )

    assert sbom["packages"][0]["licenseDeclared"] == "NOASSERTION"
