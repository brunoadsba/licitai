param(
    [string]$BackendUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."

# 1. Generate fixture DOCX if not exists
$Fixture = "$PSScriptRoot\fixtures\sample-tr.docx"
if (-not (Test-Path $Fixture)) {
    Write-Host "Gerando fixture DOCX..." -ForegroundColor Cyan
    python "$PSScriptRoot\scripts\generate_fixture.py"
}

# 2. Clean test database
$TestDb = "$Root\e2e-test.db"
if (Test-Path $TestDb) { Remove-Item $TestDb -Force }

# 3. Init test database
Write-Host "Inicializando banco de teste..." -ForegroundColor Cyan
$env:DATABASE_URL = "sqlite+aiosqlite:///$($Root.Replace('\','/'))/e2e-test.db"
$env:UPLOAD_DIR = "$Root\e2e-uploads"
python "$PSScriptRoot\scripts\init_test_db.py"

# 4. Check if backend is running
try {
    $health = Invoke-RestMethod -Uri "$BackendUrl/health" -TimeoutSec 5
    Write-Host "Backend OK: $($health | ConvertTo-Json)" -ForegroundColor Green
}
catch {
    Write-Warning "Backend nao esta rodando em $BackendUrl"
    Write-Host "Inicie o backend primeiro:" -ForegroundColor Yellow
    Write-Host "  cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000" -ForegroundColor Yellow
    exit 1
}

# 5. Run e2e tests
Write-Host "Executando testes E2E..." -ForegroundColor Cyan
$env:E2E_BASE_URL = $BackendUrl
$env:PYTHONPATH = "$Root\backend"
python -m pytest "$PSScriptRoot\tests" -v --tb=short $args
