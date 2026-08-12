# License Notes

## Stage 9 OCR review (2026-08-12)

- PaddleOCR 3.7.0、PaddleX 3.7.2 與 PaddlePaddle 3.3.1 wheel metadata 均標示 Apache-2.0；
  PaddlePaddle 提供 Python 3.12 Windows x64 wheel。
- PaddleOCR collaborator 在預訓練模型授權 issue #8780 明確回覆所列 models 均為
  Apache-2.0。採用模型的 ID、來源、SHA-256 與 attribution 記錄於
  `config/ocr-models.yaml`，不提交權重，也不在預設設定自動下載。
- Python 3.12 `pip --dry-run --ignore-installed` 解析的 OCR graph 未發現 GPL/AGPL。
  `crc32c`（LGPL-2.1-or-later）與 `python-bidi`（LGPL）為動態安裝相依；發佈時需保留其
  license/notice，並於 Stage 10 SBOM 再做人工作業與法務複核。

> 這是工程盤點，不是法律意見。正式對外或閉源商用發布前，必須鎖定實際版本、產生完整 dependency tree/SBOM，並由法務或授權負責人複核。

## 直接依賴

| 元件 | 預期用途 | 已知專案授權 | 工程決策 |
|---|---|---|---|
| Docling | PDF/DOCX/Image 主解析 | MIT | 可作主 parser；仍需檢查實際版本的模型與傳遞依賴 |
| python-docx | DOCX exporter | MIT | 可作 DOCX 輸出核心 |
| openpyxl | XLSX parser | MIT/Expat | 可作 Excel 核心；建議搭配 defusedxml 評估 XML 風險 |
| PaddleOCR | P1 optional OCR fallback | Apache-2.0（程式碼） | 只做 optional extra；模型/推論引擎另外審查 |
| PyMuPDF / PyMuPDF4LLM | 非核心 | AGPL 或商業授權 | 不納入閉源商業核心，除非完成 AGPL 義務評估或取得商業授權 |
| pdf2docx | 非核心 | 目前上游顯示 MIT，但專案已不再積極維護 | 不作核心；其歷史/目前 PyMuPDF 傳遞依賴仍需完整審查 |

## 官方參考（查核日期：2026-08-10）

- Docling package metadata：<https://github.com/docling-project/docling/blob/main/pyproject.toml>
- python-docx LICENSE：<https://github.com/python-openxml/python-docx/blob/master/LICENSE>
- openpyxl 官方文件：<https://openpyxl.readthedocs.io/en/stable/>
- PaddleOCR repository：<https://github.com/PaddlePaddle/PaddleOCR>
- PyMuPDF license 說明：<https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright>
- pdf2docx repository/status：<https://github.com/ArtifexSoftware/pdf2docx>

## OCR 與模型授權

PaddleOCR repository 的 Apache-2.0 不自動代表所有下載的預訓練模型、字型、資料集、推論引擎與轉換工具都使用相同授權。Stage 9 前必須為每個模型記錄：

- model ID / 精確版本
- 下載來源與原始 URL
- checksum
- code license 與 weights license
- NOTICE / attribution 要求
- 訓練資料限制（若官方有揭露）
- 是否允許商用、重分發與離線打包

資訊無法確認時，預設不將模型放入產品包，也不宣稱可商用。

## PyMuPDF / pdf2docx 邊界

- PyMuPDF 官方目前提供 AGPL 與商業授權雙軌；閉源網路或商業散布情境必須個別評估。
- pdf2docx 上游目前標示 MIT 且不再積極維護，但它過去/目前版本可能依賴 PyMuPDF；只看頂層 LICENSE 不足以判定整個產品路徑。
- 因此本專案不將兩者列入 runtime dependencies，也不以直接 PDF -> DOCX 版面轉換作為核心。
- 若第三方套件間接帶入 PyMuPDF，release audit 必須列出原因、版本、使用方式與授權結論。

## 發布前檢查清單

- 鎖定 dependency 與 optional extras 版本。
- 匯出 `pip list`、dependency tree、license report 與 SBOM。
- 檢查 wheels 是否捆綁原生 library、模型、字型或其他資料檔。
- 保存 LICENSE/NOTICE/attribution，確認是否需在 UI/CLI/文件中揭露。
- 測試 core install 不會意外安裝 OCR、PyMuPDF 或其他未核准重型依賴。
- 對每一個 OCR/Docling 模型保留獨立授權紀錄。
