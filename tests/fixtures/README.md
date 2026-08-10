# Fixture Policy

此資料夾只能放：

- 專案成員自行產生、內容虛構的最小測試文件；或
- 已確認允許重分發且保留必要 attribution 的公開樣本。

禁止放客戶文件、公司內部規格、個資、受 NDA 約束資料、未確認授權的網路下載檔案、模型權重或大型文件。

## 預定 fixtures

| 檔案 | Stage | 內容與驗收 |
|---|---:|---|
| `sample.md` | 4 | heading、paragraph、list、pipe table、image reference |
| `sample.xlsx` | 5 | 多 sheet、中文、日期、公式、merged cells |
| `sample.pdf` | 6 | 自製一頁或兩頁 PDF，含標題、段落、小表格 |
| `sample.docx` | 6/7 | 自製 heading、paragraph、list、table |
| `sample.png` | 6/9 | 自製清楚中英文文字圖片 |
| `expected/*.md` | 各 Stage | 經正規化的 deterministic golden output |

每次新增 binary fixture，需在本檔補充：產生工具與版本、產生日期、內容來源、授權/重分發依據、SHA-256、預期覆蓋行為。

## sample.pdf 建議產生方式

Stage 6 可用測試專用 generator 產生一份完全自製的 PDF。Generator 可以使用只放在 dev/test dependency 的 permissive library，但不可讓它成為 runtime parser。產生後固定 binary fixture 與 SHA-256；unit tests 不應每次重建造成 binary diff。
