# Troubleshooting

## Docling 首次執行下載模型

- `.[docling]` 只安裝 Python runtime；首次 PDF 轉換仍可能從 Hugging Face／ModelScope
  下載 layout、table 或 RapidOCR 模型。
- 公司網路應使用核准的 proxy／artifact mirror 或預先佈署快取；不要關閉 TLS 驗證。
- 模型權重不納入 Python SBOM。離線打包前另建 model BOM，記錄 model ID、revision、URL、
  SHA-256、code license、weights license 與 attribution。
- Windows 未啟用 Developer Mode 時，Hugging Face cache 不能使用 symlink，會增加磁碟占用，
  但不應影響正確性。

## Windows 中文／非 ASCII 路徑

- Stage 10 驗證發現 `docling-parse 7.12.1` 原生 backend 在中文安裝路徑會錯誤尋找
  `pdf_resources/glyphs/standard/additional.dat`。
- adapter 已改用 Docling 官方提供的 PyPDFium2 backend，且關閉選擇性的 `torch.compile`，
  避免 CP950 讀取 Torch template 時的 `UnicodeDecodeError`。
- 若仍遇到編碼問題，使用 Python 3.12 x64、更新到本專案鎖定的 extras，並附 `--verbose`
  的錯誤類型；不要手工複製第三方 resource 到 site-packages。

## CLI 失敗但沒有輸出檔

這是預期的安全行為。解析或匯出失敗時，temporary file 會移除，不會留下空白假成功檔。
常見 exit code：

- `1`：已知 parse/export/output conflict。
- `2`：輸入、設定、格式或限制錯誤。
- `3`：optional adapter 未安裝或停用。
- `10`：未預期內部錯誤；加 `--verbose` 只顯示 exception type，不輸出文件全文。

## 檔案／頁數限制

- 預設最大檔案 100 MiB、最大 500 pages，可透過 YAML 或 `LDC_*` 環境變數調整。
- 頁數限制是在 parser 回傳 IR 後執行。對不可信的大型 PDF，仍應在受限 process、磁碟配額與
  OS resource policy 下執行。

## OCR fallback 未執行

- OCR 預設關閉，且不會隱式下載模型。
- 需安裝 `.[ocr]`、配置本機 detection/recognition model directories，並確認主 parser
  結果低於文字或 confidence threshold 才會觸發。
- 發布 OCR runtime 前先閱讀 `docs/DEPENDENCY_AUDIT.md`；目前仍有人工授權 blockers。
