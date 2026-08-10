# Codex Master Prompt

將下列內容整段貼給 Codex，並以解壓縮後的專案根目錄作為工作資料夾。

---

你現在要接手此 repository，建立 **Local Document Converter**。請先完整閱讀：

- `AGENTS.md`
- `PRODUCT_SPEC.md`
- `ARCHITECTURE.md`
- `SKILLS.md`
- `LICENSE_NOTES.md`
- `CODEX_STAGE_PROMPTS.md`

## 任務結論

完成一個 Windows 本機優先、Python 3.12 的文件轉換 CLI：

```text
PDF / DOCX / XLSX / Markdown / Image
  -> Parser
  -> DocumentIR
  -> Exporter
  -> Markdown / DOCX / JSON
```

核心技術：

- PDF、DOCX、Image 主 parser：Docling
- XLSX parser：openpyxl
- DOCX exporter：python-docx
- OCR fallback：PaddleOCR，P1 optional、預設關閉、獨立安裝
- CLI：Typer
- 設定：YAML + environment variables
- 品質：pytest、ruff、mypy

## 嚴格範圍

- 暫不做 RAG、embedding、向量 DB、LLM、摘要、問答或翻譯。
- 先 CLI；不要加入 Streamlit、Web API、資料庫或雲端服務。
- 不追求 PDF -> DOCX 像素級還原。
- 不把 PyMuPDF / PyMuPDF4LLM 或依賴其 AGPL/commercial 授權的路徑作為閉源商業核心。
- 不以 pdf2docx 作為核心架構；若未來評估，先做完整傳遞依賴與授權審查。
- 不上傳文件、不執行巨集、不把文件全文寫入 log。

## 執行方式

1. 先檢查 workspace、git 狀態、Python 版本與現有骨架。
2. 不要一次完成所有 Stage。先回報骨架差距與 Stage 1 的精簡計畫。
3. 依 `CODEX_STAGE_PROMPTS.md` 從 Stage 1 順序執行；每次只完成一個 Stage。
4. 每個 Stage 必須：
   - 保留既有使用者修改。
   - 實作最小且完整的垂直切片。
   - 新增或更新測試。
   - 執行適當的 ruff、mypy、pytest。
   - 回報實際命令、結果、限制與下一 Stage。
5. 若第三方 API 與骨架假設不同，以已安裝版本的官方文件/型別為準，並把版本相容邏輯留在 adapter 內。
6. 若需要模型下載、網路、商用授權決策或會改變公開契約，先停止並提出具體問題。

## 第一個里程碑

必須優先打通並自動測試：

```text
tests/fixtures/sample.pdf
  -> DoclingParser
  -> valid DocumentIR
  -> MarkdownExporter
  -> sample.md（非空，關鍵內容符合 golden file）
```

若 repository 目前沒有可合法散布的 `sample.pdf`，請先建立一個最小、自製、無敏感內容的 fixture，並在 `tests/fixtures/README.md` 記錄產生方式與授權。

## 完成定義

- 支援格式與錯誤契約符合 `PRODUCT_SPEC.md`。
- 核心 domain 不 import 第三方 parsing/export libraries。
- Parser/Exporter 經 registry 注入；CLI 不直接操作 adapter。
- JSON IR 有明確 `schema_version` 且可 round-trip。
- 原子輸出、預設不覆蓋、中文/空白路徑測試通過。
- 預設 unit tests 不連網、不下載模型。
- `python -m ruff check .`、`python -m mypy src`、`python -m pytest` 通過。
- OCR 未安裝或停用時，不影響核心 MVP。
- README 命令能在乾淨 Windows Python 3.12 venv 重現。

現在請只做以下事情：讀取上述文件、檢查現況、列出 Stage 1 的具體變更與驗收，然後直接完成 Stage 1。不要開始 Stage 2。

---
