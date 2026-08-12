# Performance Baseline

量測日期：2026-08-13。數字是單機 smoke baseline，不是 SLA。

## 環境

- Windows x64、Python 3.12.13。
- 全新 `.[dev,docling]` venv 約 1,412.8 MiB。
- Hugging Face Docling layout/table cache 約 505.4 MiB。
- RapidOCR runtime models 約 61.0 MiB。
- fixture：`tests/fixtures/sample.pdf`，2,238 bytes、1 page。

## 結果

- 全新 venv 安裝 `.[dev,docling]`：約 165 秒；網路與 pip cache 會顯著影響結果。
- 模型已快取後，獨立 CLI process 的 PDF -> Markdown：6.834 秒 wall time；CLI 內部
  `elapsed_ms=5885.8`。
- 輸出：363 bytes，SHA-256
  `69ddccd7d77850f4542fbdc74d0aa9bcd9afd56812ef70a5f3adcdcc91e8c36d`。
- 標題、關鍵段落、清單與 table 都存在，warning 為 `none`。

## 操作限制

- 預設 `max_file_size_mb=100`，在 parser 啟動前檢查。
- 預設 `max_pages=500`，目前在建立 `DocumentIR` 後檢查；它不是 Docling 前置 page-count
  preflight，因此不能當作 parser 記憶體上限。
- 初次模型下載時間未設 SLA；企業或離線環境應預先核准、下載、驗證並快取模型。
- 超大型、掃描密集、加密或損壞文件不在此 baseline 範圍。
