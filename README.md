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
- `THIRD_PARTY_LICENSE_NOTES.md`：相依套件授權盤點與商用注意事項；不是本專案授權
- `docs/DEPENDENCY_AUDIT.md`：Stage 10 SBOM 與人工授權 blockers
- `docs/RELEASE_CHECKLIST.md`：MVP/DoD 驗證證據與 release gate
- `docs/TROUBLESHOOTING.md`：模型下載、Windows 路徑與錯誤處理
- `docs/PERFORMANCE.md`：Windows Python 3.12 smoke baseline
- `tests/fixtures/README.md`：測試樣本規則

## 快速開始（Windows PowerShell）

完整說明見 `WINDOWS_SETUP.md`。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,docling]"
Copy-Item .env.example .env
Copy-Item config\settings.example.yaml config\settings.yaml
python -m pytest
local-doc-convert --help
```

PaddleOCR fallback 是獨立 optional extra，預設關閉且不自動下載模型：

```powershell
python -m pip install -e ".[ocr]"
# 下載 config\ocr-models.yaml 列出的模型、核對 SHA-256、解壓至本機 models 目錄，
# 再於 config\settings.yaml 設定 ocr.enabled 與兩個 model_directory。
```

只有影像的主 parser 結果文字少於 `ocr.min_text_characters`，或帶有低於
`ocr.min_primary_confidence` 的 confidence 時才觸發 fallback。OCR 未安裝、模型未配置或
執行失敗時會保留主 parser 結果並回報 warning；模型權重不納入 repository。

目前可執行的 Markdown 轉換範例：

```powershell
local-doc-convert convert tests\fixtures\sample.md --to markdown --output work\sample.md
local-doc-convert convert tests\fixtures\sample.md --to json --output work\sample.json
local-doc-convert inspect tests\fixtures\sample.md
```

PDF 解析使用 optional Docling runtime。只需核心、Markdown、Excel 功能時可安裝
`.[dev]`；需要 PDF/DOCX/Image 主解析路徑時安裝 `.[dev,docling]`。Docling 首次執行
可能初始化或下載模型，因此真實 runtime 測試預設不隨 unit tests 執行。企業／離線環境
請先閱讀 `docs/TROUBLESHOOTING.md` 與 `docs/DEPENDENCY_AUDIT.md`。

```powershell
local-doc-convert convert tests\fixtures\sample.pdf --to markdown --output work\sample.pdf.md
local-doc-convert convert tests\fixtures\sample.md --to docx --output work\sample.docx
```

真實 Docling integration tests 預設排除，避免在 unit test 階段初始化或下載模型；確認本機
模型與 runtime 已就緒後才明確啟用：

```powershell
$env:LDC_RUN_DOCLING_INTEGRATION = "1"
python -m pytest -m integration tests\test_docling_parser.py
```

### CLI 與安全邊界

三個命令都支援明確的 YAML 設定檔；`convert` 與 `inspect` 可用 `--verbose` 將
parser、exporter、耗時、檔案大小與 warning code 寫到 stderr，不會記錄文件全文。

```powershell
local-doc-convert formats --config config\settings.yaml --verbose
local-doc-convert inspect tests\fixtures\sample.md --config config\settings.yaml --verbose
local-doc-convert convert tests\fixtures\sample.md --to json --output work\sample.json --config config\settings.yaml --verbose
```

設定優先序固定為 `CLI > LDC_* environment > YAML > defaults`。輸出預設禁止覆蓋；
只有明確傳入 `--overwrite` 或較低層設定啟用時才會覆蓋。輸入與輸出不可是同一檔案，
並套用檔案大小與頁數上限、同目錄 temporary file、atomic replace 及失敗／Ctrl-C cleanup。

| Exit code | 意義 |
|---:|---|
| 0 | 成功 |
| 1 | 已知解析、匯出或輸出衝突錯誤 |
| 2 | 使用方式、設定、輸入或格式錯誤 |
| 3 | optional parser／exporter 未安裝或已停用 |
| 10 | 未預期內部錯誤 |
| 130 | 使用者中斷（Ctrl-C） |

### Markdown MVP 支援範圍

- ATX heading（`#`～`######`）、paragraph
- ordered／unordered list
- pipe table，包含 escaped pipe（`\|`）與 backslash
- 單獨一行的 image reference

目前不解析 fenced code、block quote、nested list、thematic break、Setext heading 或完整 CommonMark inline AST。偵測到這些語法時會保留為 paragraph text，並在 `DocumentIR.warnings` 回報 `markdown.unsupported_syntax`。

### Excel MVP 支援範圍

- 僅接受 `.xlsx`，使用 `openpyxl` 的 `read_only=True` 安全讀取，不保留或執行巨集。
- 每張 worksheet 依原始順序輸出一個 heading 與一個 table；sheet 名稱、索引與資料起始座標保存在 block attributes。
- `data_only=True` 為預設；公式沒有快取值時保留空白位置並回報 `excel.formula_cache_missing`。設為 `false` 可輸出公式文字。
- 日期與時間正規化為 ISO 8601；外圍全空白列／欄會裁切，內部空白列保留。
- merged cells 只保留左上角值，並以 `excel.merged_cells` warning 記錄範圍。
- `excel.max_rows_per_sheet` 與 `excel.max_columns_per_sheet` 會在資料物化前限制每張工作表大小。

### DOCX 輸出支援範圍

- heading、paragraph、ordered/unordered list、table、image 與 page break 使用原生 Word 結構。
- 套用固定 Letter/1-inch margin、Calibri semantic styles、真實 numbering definitions 與固定 DXA table geometry。
- 本機圖片存在時安全嵌入；遠端、fragment、缺失或無法辨識的圖片保留 alt/caption，並回報 `docx.image_unavailable`。
- 實際寫入仍由 `ConversionService` 使用 temporary file、atomic replace 與預設 no-overwrite。

## 目前骨架狀態

- 已定義可序列化的 `DocumentIR`、block model、Parser/Exporter protocol。
- 已提供 parser/exporter registry、ConversionService 與完整 CLI 安全契約。
- Markdown／Excel／Docling parser、Markdown/JSON/DOCX exporter、ConversionService 與 CLI 垂直切片已可使用。
- PDF 已可經 Docling 轉成 `DocumentIR` 再輸出 Markdown；DOCX 可由任一有效 `DocumentIR` 語意化輸出；PaddleOCR fallback 已實作為預設關閉的 optional extra。
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
