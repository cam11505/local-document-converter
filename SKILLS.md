# Project Capability Specifications

此檔描述 agent 執行專案所需的能力與操作契約；不代表這些是 Codex 已安裝的全域 skills，也不要求建立自訂 skill 才能開始。

## Skill 1：Docling 文件解析

**目的**：將 PDF、DOCX 與支援的圖片格式映射成 `DocumentIR`。

**輸入**：本機 `Path`、解析設定、頁數/大小限制。

**輸出**：只回傳 `DocumentIR`；不得讓 Docling 原生物件穿透 domain boundary。

**必備行為**：

- 依實際安裝版本查核官方 API，不憑記憶硬寫。
- 將標題、段落、清單、表格、圖片、頁碼與 reading order 映射成 IR。
- 無法映射的內容加入 structured warning。
- 模型下載或重型推論只在 integration test；unit test 使用 fake adapter。
- 不把 Docling 內建輸出直接當成專案 IR。

**驗收**：小型 PDF fixture 轉成非空 IR；順序穩定；可輸出符合 golden 的 Markdown。

## Skill 2：DOCX export（python-docx）

**目的**：從 `DocumentIR` 產生可編輯 DOCX。

**必備行為**：

- Heading block 對應 Word heading style；paragraph/list/table 使用語意結構。
- 圖片不存在或無法嵌入時保留 alt/caption 並產生 warning。
- 產生檔能被 python-docx 重新開啟。
- 不承諾精準還原原始 PDF 版面。

**驗收**：重開檔案後標題、段落、表格數量與內容符合測試。

## Skill 3：Excel parsing（openpyxl）

**目的**：將 XLSX workbook 映射成 section/table blocks。

**必備行為**：

- 每張 worksheet 產生可辨識的 heading/metadata。
- 明確定義 `data_only`、公式、日期、空白列欄與 merged cells 策略。
- 預設不執行巨集；只支援 `.xlsx`，其他格式明確拒絕。
- 對大檔優先 `read_only=True`，但不得破壞必要語意而不告警。

**驗收**：多 sheet、公式快取、日期、merged cells 與中文內容有 fixture 測試。

## Skill 4：OCR fallback（PaddleOCR，P1 optional）

**目的**：主 parser 無法取得足夠文字時，提供可選 OCR 路徑。

**必備行為**：

- 安裝群組獨立，例如 `pip install -e ".[ocr]"`；預設關閉。
- 觸發條件可設定且可觀察，不得每份 PDF 都重跑 OCR。
- 模型名稱、來源、版本、checksum 與 license 必須可追溯。
- 未安裝時回傳 `ParserUnavailableError` 與安裝提示。
- OCR confidence、語言、頁碼/座標以 optional metadata 保存。

**驗收**：使用 mock 的 unit test；真實模型測試標記 `ocr`，不納入預設 CI。

## Skill 5：CLI 與 ConversionService

**目的**：提供穩定、可腳本化且不破壞資料的入口。

**必備行為**：

- CLI 只負責參數與呈現；所有轉換由 `ConversionService` 協調。
- 支援 `convert`、`inspect`、`formats`、`--verbose`、`--overwrite`。
- 輸出採原子寫入；預設不得覆蓋。
- 錯誤分類與 exit code 穩定；不輸出 stack trace，除非 debug/verbose。

**驗收**：Typer CliRunner 測試成功、未知格式、目標已存在、中文/空白路徑。

## Skill 6：Testing / Quality

**目的**：確保 IR、adapter、CLI 與授權邊界可持續維護。

**必備行為**：

- pytest、ruff、mypy；測試依 unit/contract/integration/e2e 分層。
- fixtures 可再散布且無敏感資料。
- 以 fake parser/exporter 測 ConversionService，不讓 unit test 依賴重型套件。
- golden files 必須 deterministic；第三方版本差異需隔離在 adapter tests。

**驗收**：乾淨 Python 3.12 venv 可執行 `ruff check .`、`mypy src`、`pytest`。
