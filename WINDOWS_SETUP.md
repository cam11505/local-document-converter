# Windows 開發環境啟動

## 1. 前置條件

- Windows 10/11 x64
- Python 3.12 x64（安裝時勾選 Python Launcher）
- Git（建議，但骨架可先在未安裝 Git 時執行）
- 足夠磁碟空間；Docling/OCR 模型可能額外占用空間

確認版本：

```powershell
py -0p
py -3.12 --version
git --version
```

若 `py -3.12` 找不到，先從 Python 官方安裝 3.12，再重新開啟 PowerShell。

## 2. 建立虛擬環境

在專案根目錄執行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
```

若 PowerShell 阻擋本次啟用，可只針對目前 process 執行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

也可不啟用，直接使用 `.\.venv\Scripts\python.exe`。

## 3. 安裝

開發安裝：

```powershell
python -m pip install -e ".[dev,docling]"
```

若只開發不需要 Docling 的核心、Markdown 或 Excel 路徑，可改裝 `.[dev]`；PDF、
DOCX、Image 主 parser 需要 `docling` extra。

OCR 是 P1 optional。只有完成授權與環境確認後才安裝：

```powershell
python -m pip install -e ".[dev,ocr]"
```

Paddle 推論引擎可能依 CPU/GPU 與 CUDA 版本需要不同安裝指令；不得在未核對官方安裝矩陣時硬裝 GPU 版本。

## 4. 建立本機設定

```powershell
Copy-Item .env.example .env
Copy-Item config\settings.example.yaml config\settings.yaml
```

`.env` 與 `config/settings.yaml` 已排除於 Git。MVP 不需要 API key。

## 5. 驗證骨架

```powershell
python -m ruff check .
python -m mypy src
python -m pytest
local-doc-convert --help
local-doc-convert formats
```

optional adapter 未安裝或 runtime 失敗時，`convert` 必須明確失敗，不能產生空白假輸出。

## 6. 第一個 PDF -> Markdown

完成 Stage 6 後：

```powershell
New-Item -ItemType Directory -Force work | Out-Null
local-doc-convert convert tests\fixtures\sample.pdf --to markdown --output work\sample.md
Get-Item work\sample.md
Get-Content work\sample.md -TotalCount 20
```

期望：exit code 0、`work/sample.md` 非空、標題與關鍵段落符合 golden fixture。

## 7. 常見問題

- **模型第一次執行很慢**：Docling 可能下載/初始化模型；integration test 與 unit test 應分開。
- **公司網路無法下載模型**：先使用不需模型的 Stage 1～5；不要關閉 TLS 驗證。
- **路徑含中文或空白**：adapter 已使用 PyPDFium2 backend 並關閉 `torch.compile` 以相容
  Windows 非 ASCII 安裝路徑；命令中的路徑仍需加引號。
- **套件編譯失敗**：先確認 Python 3.12 x64 與 pip 已更新，再查該版本官方 Windows wheel 支援。
- **執行原則問題**：只對目前 PowerShell process 使用 Bypass，不要任意放寬整台電腦政策。

完整診斷與 release gate 見 `docs/TROUBLESHOOTING.md`、`docs/RELEASE_CHECKLIST.md`。
