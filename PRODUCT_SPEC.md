# Product Specification

## 1. 產品定位

Local Document Converter 是在 Windows 本機執行的 CLI 文件轉換工具。它將不同來源文件解析成統一 `DocumentIR`，再輸出 Markdown、DOCX 或 JSON。

## 2. 使用者與情境

- FAE / 工程師將客戶 PDF、規格書、Word 報告或 Excel 表格轉為可整理的格式。
- 文件可能含中英文、標題、段落、清單、表格、圖片與頁碼資訊。
- 預設不將文件送到雲端服務。

## 3. MVP 範圍

### 輸入格式

| 格式 | MVP 行為 | Parser |
|---|---|---|
| PDF | 擷取可讀文字、表格與基本結構 | Docling |
| DOCX | 擷取標題、段落、清單、表格與圖片參照 | Docling |
| XLSX | 每張 worksheet 轉為 section/table | openpyxl |
| Markdown | 轉成基本 block 結構 | 內建輕量 parser |
| PNG/JPG/TIFF | 優先走 Docling 支援路徑；無文字或低信心時明確回報 | Docling；P1 可選 PaddleOCR fallback |

### 輸出格式

- Markdown：保留標題層級、段落、清單、表格與圖片參照。
- JSON：輸出帶 `schema_version` 的完整 `DocumentIR`。
- DOCX：以語意正確、可編輯為目標；不承諾像素級版面重建。

### CLI

```text
local-doc-convert convert INPUT --to markdown|json|docx [--output PATH]
local-doc-convert inspect INPUT
local-doc-convert formats
```

必要行為：

- 自動依副檔名選 parser，未知格式必須失敗並給可行訊息。
- 未指定輸出路徑時，輸出到來源旁或設定的 output directory，且不得默默覆蓋。
- 成功時 exit code 0；輸入、設定或轉換失敗時使用非 0 exit code。
- `--verbose` 顯示 parser、exporter、耗時與 warnings，但不可印出文件全文。

## 4. 優先級

- P0：DocumentIR、registry、Docling PDF、Markdown exporter、ConversionService、CLI、測試。
- P0：`sample.pdf -> DocumentIR -> sample.md` 可重現成功。
- P1：DOCX/XLSX/Image input、JSON/DOCX output、錯誤處理、批次基本能力。
- P1 optional：PaddleOCR fallback，可獨立安裝與關閉。
- P2：效能調校、更多格式、GUI/Streamlit、進階版面保真。

## 5. 明確排除

- RAG、向量資料庫、embedding、語意搜尋。
- LLM 呼叫、摘要、翻譯、問答或內容補寫。
- 雲端儲存、協作、帳號、權限管理。
- Streamlit 或其他 GUI（此啟動包不實作）。
- PDF/DOCX 數位簽章、巨集保存、OCR 模型訓練。
- 將 PyMuPDF / pdf2docx 設為核心商業轉換路徑。

## 6. 功能驗收

1. 支援的輸入均能被 registry 辨識；不支援格式有明確錯誤。
2. `DocumentIR` 能 round-trip JSON，並驗證 schema。
3. PDF fixture 能產生非空 Markdown，且關鍵標題/段落符合 golden file。
4. XLSX fixture 的 worksheet 名稱、儲存格值與合併儲存格策略有測試。
5. DOCX output 可由 python-docx 重新開啟，且主要元素存在。
6. 預設 OCR 關閉；啟用但未安裝依賴時，錯誤訊息包含安裝方式。
7. CLI 路徑含空白、中文檔名時可正常處理。
8. 測試不依賴網路；需下載模型的測試標記為 `integration` / `ocr` 並預設跳過。

## 7. 非功能需求

- Python 3.12；Windows 11 為主要開發平台。
- 型別提示、結構化例外、可測試的依賴注入。
- 不在 log、錯誤追蹤或遙測中記錄文件全文。
- 原始輸入唯讀；採原子寫入；預設不覆蓋既有輸出。
- 所有模型與外部依賴版本在正式發布前產生 SBOM / license report。

## 8. Definition of Done

- `ruff check .`、`mypy src`、`pytest` 通過。
- 新功能有單元測試；格式 adapter 有 fixture/golden 測試。
- README 的命令可在乾淨 Python 3.12 venv 重現。
- 未完成能力不得以假成功或空文件回傳。
- 發布前完成人工授權複核，尤其 OCR 模型與 Docling 的傳遞依賴。
