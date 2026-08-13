# Dependency and License Audit

查核日期：2026-08-13。這是工程盤點，不是法律意見。

## 稽核範圍

| Profile | 來源 | 套件數 | `NOASSERTION` |
|---|---|---:|---:|
| Windows Python 3.12 dev + Docling | 全新 venv 實際安裝 | 118 | 16 |
| Windows Python 3.12 OCR | pip resolver dry-run，未安裝 | 80 | 9 |

- SPDX 2.3 SBOM：`sbom/windows-py312-dev-docling.spdx.json`
- SPDX 2.3 SBOM：`sbom/windows-py312-ocr.spdx.json`
- 重建工具：`scripts/generate_sbom.py`
- SBOM 的 `licenseDeclared` 只反映 package metadata；`licenseConcluded` 一律保守標為
  `NOASSERTION`，待人工查看 wheel 內 LICENSE/NOTICE 與原生 library。

## 已驗證版本與邊界

- `docling 2.119.0`、`docling-core 2.91.0`、`docling-parse 7.12.1`、
  `docling-ibm-models 3.14.0`。
- Docling extra 使用 `pypdfium2 5.12.1`；未安裝 PyMuPDF、PyMuPDF4LLM 或 pdf2docx。
- 核心與 Docling profile 未安裝 PaddleOCR/PaddlePaddle；OCR 維持獨立 optional extra。
- OCR resolver 結果為 `paddleocr 3.7.0`、`paddlepaddle 3.3.1`、`paddlex 3.7.2`。

Docling package metadata 宣告 MIT；PaddleOCR 與 PaddlePaddle 官方專案宣告 Apache-2.0。
模型權重仍必須依 `config/ocr-models.yaml` 個別確認來源、checksum 與 weights license。

## 必須人工複核

| 項目 | 發現 | 結論 |
|---|---|---|
| 專案本身 | 擁有者已選定 MIT；根目錄 `LICENSE` 與 PEP 639 metadata 已加入 | 已解除；不代表第三方與模型授權已完成複核 |
| `crc32c 2.8` | OCR transitive dependency，metadata 為 LGPL-2.1-or-later，另含 BSD/custom code | OCR 商用散布前確認 notice、source offer 與動態連結義務 |
| `python-bidi 0.6.11` | metadata 無 SPDX；wheel 同時附 GPLv3、LGPLv3 與 third-party 清單 | 授權結論不明，OCR 發布 blocker |
| `pypdfium2 5.12.1` | metadata 為 BSD-3-Clause、Apache-2.0 與 dependency licenses 的複合描述 | 保留 wheel notices，人工確認 PDFium 第三方清單 |
| NumPy/Pandas/SciPy 等 | metadata 內含完整或非正規化授權文字 | SBOM 保留 `NOASSERTION`，發布包需彙整 notices |
| Docling/RapidOCR 模型 | 首次執行會下載模型，權重不在 Python package SBOM 內 | 建立獨立 model BOM 後才能離線打包或重分發 |

## 發布判定

- 核心 + Docling MVP：技術路徑與專案 MIT License 已完成，但人工 notice review 未完成，
  仍不可標示 release-ready。
- PaddleOCR optional extra：mocked coverage 完成；在 `python-bidi`、`crc32c` 與模型授權完成
  人工／法務複核前，不納入正式發布包。
