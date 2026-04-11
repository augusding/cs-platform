# CS Platform — 一键启动开发环境
# 用法：在项目根目录右键「用 PowerShell 运行」，或：
#   powershell -ExecutionPolicy Bypass -File scripts\start_dev.ps1

$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host ""
Write-Host "  CS Platform 开发环境启动" -ForegroundColor Cyan
Write-Host "  ========================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1：Docker 基础服务 ────────────────────────────────
Write-Host "  [1/4] 启动 Docker 服务 (PostgreSQL / Redis / Milvus)..." -ForegroundColor Yellow

$dockerRunning = docker info 2>$null
if (-not $dockerRunning) {
    Write-Host "  ✗ Docker 未运行，请先启动 Docker Desktop" -ForegroundColor Red
    Read-Host "  按 Enter 退出"
    exit 1
}

docker-compose up -d 2>&1 | Out-Null

# 等待健康检查
Write-Host "    等待服务就绪..." -ForegroundColor Gray
$maxWait = 30
$waited = 0
while ($waited -lt $maxWait) {
    $pg = docker inspect --format="{{.State.Health.Status}}" cs-postgres 2>$null
    $rd = docker inspect --format="{{.State.Health.Status}}" cs-redis 2>$null
    if ($pg -eq "healthy" -and $rd -eq "healthy") { break }
    Start-Sleep 2
    $waited += 2
    Write-Host "    ..." -ForegroundColor Gray -NoNewline
}
Write-Host ""

$pgStatus = docker inspect --format="{{.State.Health.Status}}" cs-postgres 2>$null
$rdStatus = docker inspect --format="{{.State.Health.Status}}" cs-redis 2>$null
$mvStatus = docker inspect --format="{{.State.Status}}" cs-milvus 2>$null

Write-Host "    PostgreSQL : $pgStatus" -ForegroundColor $(if ($pgStatus -eq "healthy") { "Green" } else { "Red" })
Write-Host "    Redis      : $rdStatus" -ForegroundColor $(if ($rdStatus -eq "healthy") { "Green" } else { "Red" })
Write-Host "    Milvus     : $mvStatus" -ForegroundColor $(if ($mvStatus -eq "running") { "Green" } else { "Yellow" })

if ($pgStatus -ne "healthy" -or $rdStatus -ne "healthy") {
    Write-Host ""
    Write-Host "  ✗ 基础服务未就绪，中止启动" -ForegroundColor Red
    Write-Host "    运行 docker-compose logs 查看详情" -ForegroundColor Gray
    Read-Host "  按 Enter 退出"
    exit 1
}

Write-Host "  ✓ Docker 服务已就绪" -ForegroundColor Green
Write-Host ""

# ── Step 2：API 后端 ────────────────────────────────────────
Write-Host "  [2/4] 启动 API 后端 (端口 8081)..." -ForegroundColor Yellow

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$Root'; " +
    ".venv\Scripts\Activate.ps1; " +
    "Write-Host '[ API 后端 ]' -ForegroundColor Cyan; " +
    "python main.py serve"
) -WindowStyle Normal

# 等待后端就绪
Start-Sleep 3
$backendOk = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8081/health" -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $backendOk = $true; break }
    } catch {}
    Start-Sleep 1
}

if ($backendOk) {
    Write-Host "  ✓ API 后端已就绪 → http://localhost:8081" -ForegroundColor Green
} else {
    Write-Host "  ✗ API 后端启动超时，请检查后端窗口的错误信息" -ForegroundColor Red
}
Write-Host ""

# ── Step 3：RQ Worker ──────────────────────────────────────
Write-Host "  [3/4] 启动 RQ Worker (知识库摄取)..." -ForegroundColor Yellow

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$Root'; " +
    ".venv\Scripts\Activate.ps1; " +
    "Write-Host '[ RQ Worker ]' -ForegroundColor Magenta; " +
    "python main.py worker"
) -WindowStyle Normal

Start-Sleep 2
Write-Host "  ✓ RQ Worker 已启动" -ForegroundColor Green
Write-Host ""

# ── Step 4：前端 Vite ──────────────────────────────────────
Write-Host "  [4/4] 启动前端 (端口 3001)..." -ForegroundColor Yellow

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$Root\frontend'; " +
    "Write-Host '[ 前端 Vite ]' -ForegroundColor Blue; " +
    "npm run dev"
) -WindowStyle Normal

Start-Sleep 3
Write-Host "  ✓ 前端已启动 → http://localhost:3001" -ForegroundColor Green
Write-Host ""

# ── 汇总 ──────────────────────────────────────────────────
Write-Host "  ========================" -ForegroundColor Cyan
Write-Host "  所有服务已启动" -ForegroundColor Green
Write-Host ""
Write-Host "  Admin Console  → http://localhost:3001" -ForegroundColor White
Write-Host "  API            → http://localhost:8081" -ForegroundColor White
Write-Host "  Health Detail  → http://localhost:8081/health/detail" -ForegroundColor White
Write-Host ""
Write-Host "  关闭：直接关闭各服务窗口，或运行 scripts\stop_dev.ps1" -ForegroundColor Gray
Write-Host ""

# 打开浏览器
Start-Sleep 2
Start-Process "http://localhost:3001"
