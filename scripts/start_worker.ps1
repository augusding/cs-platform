# CS Platform RQ Worker 启动脚本
# 在独立终端运行：.\scripts\start_worker.ps1

$ErrorActionPreference = "Stop"

Set-Location (Split-Path $PSScriptRoot)

# 若存在 .venv 则激活
$venv = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venv) {
    . $venv
    Write-Host "Activated .venv" -ForegroundColor DarkGray
}

Write-Host "Starting RQ Worker (ingestion / notifications / signals)..." -ForegroundColor Green
python main.py worker
