# Codex Stage Prompts

使用方式：每次只貼一個 Stage。進入下一 Stage 前，先確認前一 Stage 的驗收全部通過。每段 prompt 都假設 Codex 已閱讀 `AGENTS.md`、`PRODUCT_SPEC.md`、`ARCHITECTURE.md`。

## Stage 1 — Bootstrap 與品質基線

```text
執行 Stage 1：建立可重現的 Python 3.12 開發基線。先檢查並保留現有骨架，不要開始任何真實文件解析。

要求：
1. 校正 pyproject.toml 的 package metadata、src layout、runtime/dev/ocr optional dependencies 與 CLI entry point。
2. 建立/修正 package __init__、版本常數、Typer CLI 最小入口；--help 與 formats 可執行。
3. 建立 ruff、mypy、pytest 設定與 marker；預設測試不可下載模型或連網。
4. 建立 settings loader 的契約，只做必要預設值；優先序保留為 CLI > env > YAML > defaults。
5. 補齊最小 smoke tests。

驗收：python -m ruff check .、python -m mypy src、python -m pytest、local-doc-convert --help、local-doc-convert formats 全部成功。回報實際結果後停止，不要開始 Stage 2。
```

## Stage 2 — Document IR

```text
執行 Stage 2：完成與第三方 library 無關的 DocumentIR v1。

要求：
1. 依 ARCHITECTURE.md 完成 SourceInfo、DocumentMetadata、Warning、Heading/Paragraph/List/Table/Image/PageBreak blocks 與 DocumentIR。
2. 使用 discriminated union；定義 page number、order、table cell、attributes 的 validation 規則。
3. JSON serialization 必須 deterministic，帶 schema_version="1.0"，並可 round-trip。
4. 新增合法/非法資料、Unicode、空文件、table、image reference 的 unit tests。
5. 核心 domain 不得 import Docling、openpyxl、python-docx 或 PaddleOCR。

驗收：ruff、mypy、unit tests 全通過，並展示一份最小 IR JSON。完成後停止，不要開始 Stage 3。
```

## Stage 3 — Parser / Exporter 契約與 Registry

```text
執行 Stage 3：完成 Parser、Exporter、context、registry 與例外契約，不實作重型 adapter。

要求：
1. 定義 typed Protocol/ABC，extension/format normalization 與 capability metadata。
2. Registry 禁止重複註冊；未知格式拋 UnsupportedFormatError；錯誤訊息列出可用格式。
3. 完成專案例外階層與穩定錯誤分類。
4. 使用 fake parser/exporter 完成 contract tests；不得 import 或安裝重型 adapter 才能跑測試。

驗收：registry 選擇、重複註冊、未知格式與 dependency unavailable 測試通過。完成後停止。
```

## Stage 4 — Markdown input + Markdown / JSON output

```text
執行 Stage 4：建立第一條不需模型的端到端垂直切片。

要求：
1. MarkdownParser 支援 MVP 所需 heading、paragraph、ordered/unordered list、pipe table、image reference；清楚記錄未支援語法。
2. MarkdownExporter 產生 deterministic UTF-8 Markdown，正確 escape table cell 與保留 block 順序。
3. JsonExporter 以 DocumentIR 官方 serialization 輸出縮排、UTF-8 JSON。
4. 實作 ConversionService 的基本選擇、輸出路徑、原子寫入與 no-overwrite。
5. CLI convert/inspect 接上 service。

驗收：sample.md -> IR -> output.md/json、中文與含空白路徑、目標已存在、未知格式的 unit/e2e tests 通過。完成後停止。
```

## Stage 5 — Excel parser

```text
執行 Stage 5：用 openpyxl 實作 XLSX -> DocumentIR。

要求：
1. 每個 worksheet 轉成 heading + table blocks，保存 sheet 名稱與順序。
2. 明確實作 data_only、公式快取缺失、日期、空白範圍、merged cells 策略並產生必要 warnings。
3. 優先安全讀取，不執行巨集；只接受 .xlsx。
4. 建立自製 fixture，含多 sheet、中文、公式、日期、merged cell；在 fixtures README 記錄來源。

驗收：XLSX -> IR -> Markdown/JSON 的 deterministic tests 通過；大型工作表限制有設定與測試。完成後停止。
```

## Stage 6 — Docling parser 與首個 PDF 成功案例

```text
執行 Stage 6：以目前安裝版本的 Docling 官方 API 實作 PDF/DOCX/Image 主 parser，優先完成 PDF 路徑。

要求：
1. 所有 Docling import 與版本相容處理只存在 adapter；domain 不可依賴 Docling。
2. 將 reading order、heading、paragraph、list、table、image reference、page number 映射為 DocumentIR；無法映射者產生 warning。
3. 建立自製、可再散布的小型 sample.pdf 與 golden Markdown，記錄產生方式。
4. unit tests 使用 fake/mocked Docling result；真實 Docling 測試標記 integration。
5. 不啟用 PaddleOCR fallback，不加入 PyMuPDF/pdf2docx 核心路徑。

主要驗收：tests/fixtures/sample.pdf -> DocumentIR -> sample.md 成功，輸出非空且關鍵標題/段落符合 golden。另驗證損壞 PDF 與缺少 optional runtime 的明確錯誤。完成後停止。
```

## Stage 7 — DOCX exporter

```text
執行 Stage 7：用 python-docx 完成 DocumentIR -> DOCX。

要求：
1. heading/paragraph/list/table/page break 使用正確 Word 結構與樣式。
2. 圖片存在時安全嵌入；缺失時保留 alt/caption 並回傳 warning。
3. 使用 temporary file + atomic replace；預設 no-overwrite。
4. 不做像素級版面還原，不使用 pdf2docx 當捷徑。

驗收：產生的 DOCX 可由 python-docx 重新開啟；標題、段落、list、table、page break 內容與數量有測試。完成後停止。
```

## Stage 8 — CLI 完整化與批次安全

```text
執行 Stage 8：完成 CLI 使用體驗與 ConversionService 安全邊界。

要求：
1. 完成 convert、inspect、formats、--output、--overwrite、--verbose、--config。
2. 設定優先序為 CLI > env > YAML > defaults；錯誤映射成文件所定 exit codes。
3. 驗證 input/output 不可相同、輸入大小上限、輸出目錄、原子寫入與 cleanup。
4. 可加入最小 batch 模式，但單檔失敗不能默默成功；不得擴充 GUI/API。
5. log 不含文件全文或機密。

驗收：CliRunner/e2e 覆蓋成功、部分失敗、overwrite、中文/空白路徑、Ctrl-C cleanup。完成後停止。
```

## Stage 9 — PaddleOCR optional fallback

```text
執行 Stage 9：加入可完全關閉、獨立安裝的 PaddleOCR fallback。

前置條件：先閱讀 LICENSE_NOTES.md，並核對當前 PaddleOCR、推論引擎、預訓練模型與傳遞依賴的官方授權。若無法確認模型授權或安裝會引入不相容授權，停止並回報，不得自行繼續。

要求：
1. OCR 只在 settings 啟用且主 parser 判定文字不足/低信心時觸發。
2. 將 dependency 放在 [ocr] extra；未安裝時核心功能仍正常，並提供明確安裝提示。
3. 模型 ID、版本、來源、checksum、license/notice 可追溯；不得提交大型模型權重。
4. unit tests 全部 mock；真實模型測試標記 ocr/integration，預設跳過。

驗收：停用、未安裝、符合觸發條件、不符合觸發條件、OCR 失敗 fallback 的測試通過。完成後停止。
```

## Stage 10 — Release hardening

```text
執行 Stage 10：完成 MVP 發布前硬化，不新增產品範圍。

要求：
1. 在全新 Windows Python 3.12 venv 重跑 README 安裝與 sample.pdf -> sample.md。
2. 完成 ruff、mypy、pytest、integration smoke，修正 flaky/non-deterministic tests。
3. 做 dependency/license audit 與 SBOM 草案；特別檢查 Docling/PaddleOCR 傳遞依賴與模型授權。
4. 補齊錯誤處理、效能量測、檔案大小/頁數限制、文件與 troubleshooting。
5. 建立版本與 changelog 建議；不得加入 RAG、GUI、雲端或不必要 dependency。

驗收：PRODUCT_SPEC.md 的 MVP/DoD checklist 逐項提供證據；列出已知限制與人工授權複核項目。若任何必要項未完成，明確標記未完成，不可宣稱 release-ready。
```
