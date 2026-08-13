# Third-Party Notices

Local Document Converter is licensed under the MIT License. Third-party packages installed
alongside it are separate works and remain under their own license terms.

The `v0.1.0` release artifact contains only the project Python package, project metadata,
and the project MIT `LICENSE`. It does not bundle third-party wheels, native libraries,
OCR/Docling model weights, fonts, or datasets. The release workflow enforces this boundary.

## Core and Docling release profile

The supported release profile uses packages distributed separately by pip, including:

- Docling — MIT.
- pypdfium2 — Apache-2.0 OR BSD-3-Clause; its official binary wheels include PDFium and
  dependency license notices. Keep those wheel-provided notices when redistributing an
  offline dependency bundle.
- python-docx — MIT.
- openpyxl — MIT/Expat.
- Pydantic and pydantic-settings — MIT.
- PyYAML — MIT.
- Typer — MIT.

The committed SPDX inventories remain the authoritative versioned package inventory. A
`NOASSERTION` entry means automated package metadata was insufficient; it is not a claim
that the package is unlicensed.

## OCR preview profile

PaddleOCR support remains optional, disabled by default, and outside the certified `v0.1.0`
release profile. Do not redistribute an OCR offline bundle or model archive under this
release until an organization-designated license reviewer approves the exact artifacts.
Relevant items include `python-bidi` (wheel classifier: LGPL; wheel includes LGPLv3/GPLv3
texts and a Rust dependency SBOM), `crc32c` (LGPL-2.1-or-later metadata plus bundled
third-party code), and each PaddleOCR model weight.

This notice is an engineering inventory, not legal advice.
