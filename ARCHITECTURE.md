# Architecture

## 1. 架構原則

- 解析與輸出解耦：Parser 只產生 `DocumentIR`；Exporter 只消費 `DocumentIR`。
- 核心 domain 不依賴 Docling、openpyxl、python-docx 或 PaddleOCR。
- 外部套件放在 adapter 邊界，便於替換、測試與授權控管。
- 任何格式轉換都經過 `ConversionService`，CLI 不直接呼叫第三方 library。

## 2. 資料流

```text
Input file
  -> Input validation / format detection
  -> ParserRegistry
  -> Parser adapter (Docling | Excel | Markdown | OCR fallback)
  -> DocumentIR validation
  -> ExporterRegistry
  -> Exporter adapter (Markdown | JSON | DOCX)
  -> atomic output write
  -> ConversionResult + warnings
```

## 3. Document IR

`DocumentIR` 是穩定、可序列化、與第三方套件無關的中介格式。

```text
DocumentIR
├─ schema_version
├─ source (path, media_type, size, checksum optional)
├─ metadata (title, author, language, page_count, custom)
├─ blocks[]
│  ├─ HeadingBlock(level, text)
│  ├─ ParagraphBlock(text)
│  ├─ ListBlock(ordered, items)
│  ├─ TableBlock(rows, column_names optional)
│  ├─ ImageBlock(uri, alt_text, caption optional)
│  └─ PageBreakBlock
└─ warnings[]
```

共同欄位建議：`id`、`type`、`order`、`page_number`、`source_ref`、`attributes`。座標、OCR confidence 等 parser-specific 資訊只能放在明確命名的 optional 欄位或 `attributes`，不可污染主要輸出契約。

### IR 規則

- `schema_version` 固定為明確字串（初版 `1.0`），未知欄位一律拒絕。
- block `id` 不可為空且在文件內唯一；`order` 從 0 開始、連續，並須與 `blocks` 陣列順序一致。
- `page_number` 為 1-based；無頁概念時為 `null`；若 metadata 有 `page_count`，block 與 warning 頁碼不得超出範圍。
- table cell 只能是字串或 `null`；空字串與 `null` 語意不同。每列欄數必須一致，若有 `column_names`，其長度必須與資料列相同；空表允許存在。
- `attributes`、metadata `custom` 與 warning `details` 只能包含可序列化 JSON 值，拒絕非有限浮點數與第三方物件。
- 官方 JSON 使用 UTF-8 文字與穩定 key 排序，確保相同 IR 產生 deterministic output 並可完整 round-trip。
- 圖片可先保存相對參照；binary 不直接塞進 JSON。
- Parser 無法保留的資訊以 warning 回報，不可靜默丟失。

## 4. 主要介面

### Parser

```python
class Parser(Protocol):
    supported_extensions: frozenset[str]
    def parse(self, source: Path, context: ParseContext) -> DocumentIR: ...
```

### Exporter

```python
class Exporter(Protocol):
    format_name: str
    output_extension: str
    def export(self, document: DocumentIR, destination: Path, context: ExportContext) -> None: ...
```

### ConversionService

職責：驗證路徑、解析設定、選 adapter、管理暫存檔、原子輸出、蒐集 warning、回傳 `ConversionResult`。它不包含格式專用解析邏輯。

## 5. Adapter 策略

- `DoclingParser`：PDF/DOCX/Image 的主解析 adapter；集中處理 Docling model 到 IR 的映射。
- `ExcelParser`：使用 openpyxl `read_only=True` / `data_only` 設定；每張 sheet 映射為 heading + table。
- `MarkdownParser`：只支援 MVP 所需的標題、段落、清單與 pipe table；不建立完整 CommonMark AST。
- `PaddleOcrFallback`：optional capability；只有設定啟用且主 parser 判定需要時呼叫。
- `MarkdownExporter` / `JsonExporter`：純文字輸出，可做 deterministic golden test。
- `DocxExporter`：python-docx；以語意樣式為主，不追求原版面像素還原。

## 6. 設定優先序

```text
CLI options > environment variables > config/settings.yaml > built-in defaults
```

敏感資訊只透過環境變數；本專案目前不需 API key。設定 model cache 路徑時不得把使用者絕對路徑提交到 Git。

## 7. 例外與錯誤碼

- `UnsupportedFormatError`：輸入或輸出格式不支援。
- `InputValidationError`：檔案不存在、不可讀、大小超限。
- `ParserUnavailableError`：optional dependency 未安裝。
- `ParseError` / `ExportError`：adapter 失敗，保留 exception chaining。
- `OutputExistsError`：未指定 overwrite 且目標存在。

CLI 建議映射：一般錯誤 1、使用方式/輸入錯誤 2、optional capability unavailable 3、內部錯誤 10。

## 8. 檔案與安全

- 驗證 resolved input/output，禁止輸入與輸出為同一檔案。
- 先寫入同目錄 temporary file，完成後 replace，避免半成品。
- 預設最大檔案大小由設定限制；zip-based Office 文件需防 zip bomb。
- 禁止執行文件內巨集、外部連結或嵌入物件。
- log 僅保留檔名、格式、大小、耗時、warning 類型，不記錄全文。

## 9. 測試分層

- Unit：IR validation、registry、settings、Markdown/JSON exporter。
- Contract：每個 parser/exporter 遵守 protocol 與錯誤契約。
- Fixture/golden：PDF/DOCX/XLSX/MD/Image 的小型合法測試檔。
- Integration：Docling 與 OCR；可能下載模型，預設不在 unit test 執行。
- E2E：CLI 在含空白/中文路徑下執行並檢查 exit code 與輸出。
