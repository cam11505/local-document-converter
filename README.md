# Local Document Converter

本機優先（local-first）的文件轉換器啟動包。此版本只處理文件轉換，不包含 RAG、向量資料庫、LLM 摘要或問答。

## 目標

- 輸入：PDF、DOCX、XLSX、Markdown、Image（PNG/JPG/TIFF）
- 輸出：Markdown、DOCX、JSON
- 統一中介格式：`DocumentIR`
- 主要解析：Docling
- Excel：openpyxl
- DOCX 輸出：python-docx
- OCR fallback：PaddleOCR，P1 optional，不是 MVP 的強制安裝項目
- 使用介面：先 CLI；GUI/Streamlit 暫不實作

第一條成功路徑：

```text
sample.pdf -> DoclingParser -> DocumentIR -> MarkdownExporter -> sample.md
```

## 文件索引

- `CODEX_MASTER_PROMPT.md`：整體開發任務，可直接貼給 Codex
- `CODEX_STAGE_PROMPTS.md`：Stage 1～10 的獨立提示詞
- `AGENTS.md`：專案內 agent 規則與驗收標準
- `SKILLS.md`：需要的技術能力規格，不是已安裝 skill 清單
- `PRODUCT_SPEC.md`：產品範圍與 MVP 驗收條件
- `ARCHITECTURE.md`：Document IR 與分層架構
- `WINDOWS_SETUP.md`：Windows / Python 3.12 啟動步驟
- `LICENSE_NOTES.md`：相依套件授權盤點與商用注意事項
- `tests/fixtures/README.md`：測試樣本規則

## 快速開始（Windows PowerShell）

完整說明見 `WINDOWS_SETUP.md`。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
Copy-Item config\settings.example.yaml config\settings.yaml
python -m pytest
local-doc-convert --help
```

轉換範例（完成對應 Stage 後）：

```powershell
local-doc-convert convert tests\fixtures\sample.pdf --to markdown --output work\sample.md
```

## 目前骨架狀態

- 已定義可序列化的 `DocumentIR`、block model、Parser/Exporter protocol。
- 已提供 parser/exporter registry、ConversionService 與 CLI 契約。
- Markdown parser、Markdown/JSON exporter 可作為第一批實作起點。
- Docling、Excel、DOCX、OCR adapter 保留清楚的 `NotImplementedError` 邊界，交由 Stage prompts 逐步完成。
- 骨架不宣稱已具備完整轉換能力；每一階段完成後都必須跑測試。

## 非目標

- 不做 RAG、embedding、向量搜尋、聊天、摘要或內容生成。
- 不追求 PDF -> DOCX 像素級還原。
- 不保證支援加密、損壞、含巨集或超大型文件。
- 不預設上傳文件或遙測；本機離線處理為預設。

## 建議使用方式

1. 解壓縮後，以此資料夾開啟 Codex。
2. 先讓 Codex 閱讀 `AGENTS.md`、`PRODUCT_SPEC.md`、`ARCHITECTURE.md`。
3. 貼上 `CODEX_MASTER_PROMPT.md`。
4. 依 `CODEX_STAGE_PROMPTS.md` 一次執行一個 Stage；每階段驗收後再繼續。
