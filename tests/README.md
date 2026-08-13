# Tests

- `test_smoke.py`：package 與 CLI 基線。
- `test_document_ir.py`：IR validation 與 JSON round-trip。
- `test_markdown_pipeline.py`：目前可執行的 Markdown -> IR -> Markdown/JSON 垂直切片。
- `test_cli_stage8.py`：設定優先序、exit codes、verbose 安全 log、限制、atomic cleanup 與 Ctrl-C。
- `fixtures/`：小型、可再散布、無敏感內容的來源與 golden files。

預設命令不得連網或下載模型：

```powershell
python -m pytest -m "not integration and not ocr"
```

重型測試需明確啟用：

```powershell
python -m pytest -m integration
python -m pytest -m ocr
```

真實 PaddleOCR 測試需要先安裝 `.[ocr]`、下載並校驗 `config/ocr-models.yaml`
所列模型，再設定 `LDC_OCR_DETECTION_MODEL_DIR`、`LDC_OCR_RECOGNITION_MODEL_DIR`
與 `LDC_RUN_OCR_INTEGRATION=1`。預設測試不下載模型或執行 OCR runtime。
