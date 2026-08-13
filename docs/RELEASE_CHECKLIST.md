# Stage 10 Release Checklist

查核日期：2026-08-13。狀態：**MVP 技術候選完成，但不可正式發布**。

## Product Spec / DoD 證據

- [x] Python `>=3.12,<3.13`，全新 Windows Python 3.12.13 venv 安裝成功。
- [x] README 的 `.[dev,docling]` 安裝命令可重現。
- [x] `sample.pdf -> DocumentIR -> Markdown` 真實 integration 與 CLI smoke 成功。
- [x] mocked unit tests 與 fixture/golden coverage 存在，真實 integration 預設 gated。
- [x] `ruff check .`、`mypy src`、預設 `pytest` 需於提交前全部通過。
- [x] Docling integration：2 passed；壞 PDF 不會產生假成功。
- [x] `pip check`：無破損 requirements。
- [x] 核心安全契約：no-overwrite、atomic replace、temporary cleanup、穩定 exit codes。
- [x] verbose log 只含檔名（需 opt-in）、大小、adapter、耗時、warning code，不含全文。
- [x] 檔案大小 100 MiB 與頁數 500 的預設限制已有測試。
- [x] dev+Docling 與 OCR 兩個 profile 已產生 SPDX 2.3 SBOM。
- [x] 效能、磁碟需求、模型冷啟動與 troubleshooting 已文件化。
- [x] 版本建議與 changelog 已建立；建議解除 blockers 後發布 `0.1.0`。
- [x] GitHub Actions `CI` 已定義：Windows Python 3.12、Ruff、Mypy、unit/mocked tests、CLI 與 wheel build。
- [x] 手動 `Release candidate smoke` 已定義：Docling 真實 integration、PDF CLI 與 release artifact。
- [x] Release Wheel 邊界已驗證：只含本專案 package／metadata／MIT LICENSE，不捆綁第三方 binary 或模型。

## 未完成／發布 blockers

- [x] 專案擁有者已選定 MIT，根目錄 `LICENSE` 與 PEP 639 package metadata 已同步。
- [x] `v0.1.0` artifact notices 與重分發邊界已記錄；第三方依賴由 pip 分開安裝，不打入本專案 Wheel。
- [x] OCR 明確排除於 `v0.1.0` 認證／重分發範圍；需另案完成 `python-bidi`、`crc32c` 與模型權重複核。
- [ ] 若離線打包 Docling 模型，建立 model BOM 並保存 revision、checksum、授權與 notices。
- [x] GitHub Windows runner 已重跑全新環境 cold-start smoke，含 Docling 模型初始化。
- [ ] 在預定 tag commit 上確認 GitHub Actions `CI` 與 `Release candidate smoke` 均成功。

任何 blocker 未完成時，不建立正式 release tag，不宣稱 release-ready 或 production-ready。
