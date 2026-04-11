# CS Platform — 停止所有开发服务

$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host ""
Write-Host "  停止 CS Platform 开发环境..." -ForegroundColor Yellow
Write-Host ""

# 停止 Python 进程（API + Worker）
$pythonProcs = Get-Process python -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "main.py" }
if ($pythonProcs) {
    $pythonProcs | ForEach-Object {
        Write-Host "  停止进程 PID $($_.Id) ($($_.ProcessName))..." -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force
    }
} else {
    # 兜底：停止所有 python 进程
    taskkill /F /IM python.exe 2>$null | Out-Null
}

Write-Host "  ✓ Python 进程已停止" -ForegroundColor Green

# 询问是否停止 Docker
$stopDocker = Read-Host "  是否同时停止 Docker 服务？(y/N)"
if ($stopDocker -eq "y" -or $stopDocker -eq "Y") {
    docker-compose stop 2>&1 | Out-Null
    Write-Host "  ✓ Docker 服务已停止（数据已保留）" -ForegroundColor Green
} else {
    Write-Host "  Docker 服务保持运行（下次启动更快）" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  已停止完毕" -ForegroundColor Cyan
Write-Host ""
