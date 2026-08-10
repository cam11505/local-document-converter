# AGENTS.md

## 專案使命

建立本機文件轉換器：PDF、DOCX、XLSX、Markdown、Image 經 `DocumentIR` 輸出 Markdown、DOCX、JSON。暫不包含 RAG。

## 開始工作前

1. 先閱讀 `PRODUCT_SPEC.md`、`ARCHITECTURE.md`、`LICENSE_NOTES.md`。
2. 檢查目前 git 狀態與既有修改；不得覆蓋使用者未提交內容。
3. 說明本次只處理哪個 Stage、會修改哪些檔案、如何驗收。
4. 資訊不足且會改變公開介面、授權或資料安全時，停止並詢問；不得自行擴大需求。

## 邊界

- 只做文件轉換，不加入 RAG、LLM、embedding、向量 DB、摘要或問答。
- CLI 優先；沒有明確指示不得加入 Streamlit、Web API、資料庫或雲端服務。
- Docling 是 PDF/DOCX/Image 主 parser；Excel 使用 openpyxl；DOCX 輸出使用 python-docx。
- PaddleOCR 僅 P1 optional fallback，必須是 optional dependency 且可完全關閉。
- 不把 PyMuPDF、PyMuPDF4LLM 或依賴其 AGPL/commercial 授權的路徑設為閉源商業核心。
- 不把 pdf2docx 當核心架構；若評估使用，先檢查當前版本、PyMuPDF 傳遞依賴與完整 dependency license graph。

## Coding standards

- Python 3.12；`src/` layout；UTF-8；4 spaces。
- 公開函式與 class 使用完整 type hints；核心 domain 使用 Pydantic model 或清楚 dataclass。
- 核心 domain 不得 import Docling、openpyxl、python-docx、PaddleOCR。
- 使用 `pathlib.Path`；禁止以字串拼接檔案路徑。
- 例外需使用專案自訂類型並保留 `raise ... from exc`。
- Parser/Exporter 必須可由 registry 注入；不得在 CLI 寫格式分支大雜燴。
- 輸出必須 deterministic；未指定 overwrite 時不得覆寫。
- 不用 blanket `except Exception` 吞錯；若在 CLI boundary 捕捉，必須記錄分類並回傳非 0。
- 不在 log 印文件全文、token、環境變數或機密資料。
- dependency 需有用途、版本策略、授權說明；不可為方便而加入大型框架。

## 測試規則

- 每個 bug fix 先新增能重現的測試；每個新 adapter 至少一個 contract test。
- Unit test 不可連網、不可下載模型、不可依賴本機 Office。
- Docling/OCR 重型測試標記 `integration` / `ocr`，預設跳過。
- Fixture 必須小、可再散布、無客戶或個資；來源與授權記在 `tests/fixtures/README.md`。
- Golden output 只比對穩定語意；第三方產生的隨機 ID、時間戳或路徑需正規化。

## 禁止事項

- 不提交 `.env`、真實 API key、模型權重、客戶文件或大檔案。
- 不宣稱 placeholder 已完成；未實作必須明確 `NotImplementedError` 或 capability error。
- 不自行刪除、重寫或 reset 使用者變更。
- 不以 shell 呼叫不受控外部程式處理使用者文件。
- 不執行 Office 巨集、不跟隨外部連結、不解壓未受限制的 archive。
- 不繞過型別、lint 或測試來讓 CI 表面通過。

## 每次變更的驗收方式

依風險執行下列命令，並在回報列出實際結果：

```powershell
python -m ruff check .
python -m mypy src
python -m pytest
```

若修改 CLI，再執行：

```powershell
local-doc-convert --help
local-doc-convert formats
```

若修改轉換流程，至少跑一個 fixture E2E，確認：輸出存在、非空、可重新解析、warning/exit code 正確、原始檔未被修改。

## 完成回報格式

- 結論：本 Stage 是否完成。
- 變更：檔案與核心行為。
- 驗證：執行的命令與結果。
- 限制：尚未完成、跳過或需要人工確認的項目。
- 下一步：只建議下一個 Stage，不自行擴充。
