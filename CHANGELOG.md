# Changelog

本專案採用 Keep a Changelog 結構；版本號遵循 Semantic Versioning。

## [Unreleased]

## [0.1.0] - 2026-08-13

### Added

- Markdown、Excel、Docling parser 與 PaddleOCR optional fallback。
- Markdown、JSON、語意化 DOCX exporter。
- 安全 CLI、設定優先序、檔案／頁數限制、atomic output 與穩定 exit codes。
- Windows Python 3.12 SPDX 2.3 SBOM、release checklist 與 troubleshooting 文件。
- MIT License、PEP 639 package metadata 與 Windows GitHub Actions release gates。

### Changed

- Docling PDF adapter 使用 PyPDFium2 backend 並關閉選擇性的 `torch.compile`，避免 Windows
  非 ASCII 安裝路徑與 CP950 預設編碼造成 runtime 失敗。
- `docling` optional extra 鎖定至已驗證的 `2.119.x` API 邊界。

### Security

- 預設禁止覆蓋、使用同目錄 temporary file 與 atomic replace，不記錄文件全文。
- OCR 模型預設不下載、不提交至 repository，必須明確配置本機模型路徑。

## 發布範圍

- `0.1.0` 認證 core + Docling 文件轉換路徑，Release Wheel 不捆綁第三方 binary 或模型。
- PaddleOCR fallback 保留為預覽 optional extra，不納入 `0.1.0` 認證或離線重分發範圍。
