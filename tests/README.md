# Tests

- `test_smoke.py`：package 與 CLI 基線。
- `test_document_ir.py`：IR validation 與 JSON round-trip。
- `test_markdown_pipeline.py`：目前可執行的 Markdown -> IR -> Markdown/JSON 垂直切片。
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
