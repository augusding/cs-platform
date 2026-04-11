# CS Platform - 一键启动开发环境

$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host ""
Write-Host "  CS Platform 开发环境启动" -ForegroundColor Cyan
Write-Host "  ========================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Docker
Write-Host "  [1/4] 启动 Docker 服务..." -ForegroundColor Yellow
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  X Docker 未运行，请先启动 Docker Desktop" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}

docker-compose up -d 2>&1 | Out-Null

Write-Host "    等待服务就绪..." -ForegroundColor Gray
$waited = 0
while ($waited -lt 30) {
    $pg = docker inspect --format="{{.State.Health.Status}}" cs-postgres 2>&1
    $rd = docker inspect --format="{{.State.Health.Status}}" cs-redis 2>&1
    if ($pg -eq "healthy" -and $rd -eq "healthy") { break }
    Start-Sleep 2
    $waited += 2
}

$pgStatus = docker inspect --format="{{.State.Health.Status}}" cs-postgres 2>&1
$rdStatus = docker inspect --format="{{.State.Health.Status}}" cs-redis 2>&1
$mvStatus = docker inspect --format="{{.State.Status}}" cs-milvus 2>&1

if ($pgStatus -eq "healthy") {
    Write-Host "    PostgreSQL : $pgStatus" -ForegroundColor Green
} else {
    Write-Host "    PostgreSQL : $pgStatus" -ForegroundColor Red
}
if ($rdStatus -eq "healthy") {
    Write-Host "    Redis      : $rdStatus" -ForegroundColor Green
} else {
    Write-Host "    Redis      : $rdStatus" -ForegroundColor Red
}
Write-Host "    Milvus     : $mvStatus" -ForegroundColor Yellow

if ($pgStatus -ne "healthy" -or $rdStatus -ne "healthy") {
    Write-Host ""
    Write-Host "  X 基础服务未就绪，中止启动" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}

Write-Host "  OK Docker 服务已就绪" -ForegroundColor Green
Write-Host ""

# Step 2: Worker
Write-Host "  [2/4] 启动 RQ Worker..." -ForegroundColor Yellow
docker-compose --profile worker up -d worker 2>&1 | Out-Null
Write-Host "  OK RQ Worker 已启动" -ForegroundColor Green
Write-Host ""

# Step 3: API
Write-Host "  [3/4] 启动 API 后端 (8081)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root'; .venv\Scripts\Activate.ps1; Write-Host '[API]' -ForegroundColor Cyan; python main.py serve" -WindowStyle Normal
Start-Sleep 4

$backendOk = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8081/health" -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $backendOk = $true; break }
    } catch {}
    Start-Sleep 1
}

if ($backendOk) {
    Write-Host "  OK API 后端已就绪 http://localhost:8081" -ForegroundColor Green
} else {
    Write-Host "  X API 后端启动超时，请检查后端窗口" -ForegroundColor Red
}
Write-Host ""

# Step 4: Frontend
Write-Host "  [4/4] 启动前端 Vite..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root\frontend'; Write-Host '[Frontend]' -ForegroundColor Blue; npm run dev" -WindowStyle Normal
Start-Sleep 3
Write-Host "  OK 前端已启动 http://localhost:3001" -ForegroundColor Green
Write-Host ""

Write-Host "  ========================" -ForegroundColor Cyan
Write-Host "  Admin Console -> http://localhost:3001" -ForegroundColor White
Write-Host "  API           -> http://localhost:8081" -ForegroundColor White
Write-Host "  Health        -> http://localhost:8081/health/detail" -ForegroundColor White
Write-Host ""

Start-Sleep 2
Start-Process "http://localhost:3001"
