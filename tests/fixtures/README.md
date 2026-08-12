# Fixture Policy

此資料夾只能放：

- 專案成員自行產生、內容虛構的最小測試文件；或
- 已確認允許重分發且保留必要 attribution 的公開樣本。

禁止放客戶文件、公司內部規格、個資、受 NDA 約束資料、未確認授權的網路下載檔案、模型權重或大型文件。

## 預定 fixtures

| 檔案 | Stage | 內容與驗收 |
|---|---:|---|
| `sample.md` | 4 | 2026-08-11 由專案自行撰寫；虛構中文內容，涵蓋 heading、paragraph、ordered/unordered list、escaped pipe table、image reference，可自由隨本專案重分發 |
| `sample.xlsx` | 5 | 2026-08-11 由 `@oai/artifact-tool` 2.8.6+ 自行產生；虛構中文內容，含「摘要」與「空白與合併」兩張 sheet、日期、公式、內部空白列與 merged cells；可自由隨本專案重分發；SHA-256 `fa312bd4de6696802862b1c58f51b6c1deaca8c86563404d21cf3252bce5dcf0` |
| `sample.pdf` | 6 | 2026-08-11 以同目錄 `generate_sample_pdf.py` 與 ReportLab 4.4.9 自製；單頁 Letter fixture，含 heading、paragraph、list、table 與簡圖；專案可再散布；SHA-256 `80e1d6b5589ffd78771514de828169d8811a711cea4acfb823d0f2e60c5b9439`。 |
| `sample.docx` | 6/7 | 自製 heading、paragraph、list、table |
| `sample.png` | 9 | 2026-08-13 由 `generate_sample_image.py` 與 Pillow 產生；自製英文 OCR fixture，SHA-256 `233f18f48434bf34b87ad97175ef11dc262e01eb68cb8bc74e4d5f3938b8d459` |
| `expected/*.md` | 各 Stage | 經正規化的 deterministic golden output |

每次新增 binary fixture，需在本檔補充：產生工具與版本、產生日期、內容來源、授權/重分發依據、SHA-256、預期覆蓋行為。

## sample.pdf 建議產生方式

Stage 6 使用 `generate_sample_pdf.py` 產生固定的最小、自製 PDF；ReportLab 只用於重建
fixture，不是 runtime parser dependency。`Canvas(invariant=1)` 讓 metadata 與 binary 可重現；unit
tests 直接讀取已提交的 fixture，不會每次重建。
