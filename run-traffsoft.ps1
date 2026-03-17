$rootPath     = "G:\projects\traffsoft"
$backendPath  = Join-Path $rootPath "traffsoft-backend"
$frontendPath = Join-Path $rootPath "traffsoft-frontend"

Write-Host "=== Запускаю TraffSoft ===" -ForegroundColor Cyan

# --- BACKEND ---
Write-Host "-> Запуск backend..." -ForegroundColor Yellow
Set-Location $backendPath

Start-Process powershell -ArgumentList `
    '-NoExit', `
    '-Command', "cd `"$backendPath`"; venv\Scripts\activate; python -m uvicorn --reload --host 0.0.0.0 --port 8000 app.main:app"

# --- FRONTEND ---
Write-Host "-> Запуск frontend..." -ForegroundColor Yellow
Set-Location $frontendPath

Start-Process powershell -ArgumentList `
    '-NoExit', `
    '-Command', "cd `"$frontendPath`"; npm run dev -- --host 127.0.0.1"

Write-Host "=== Команды на запуск backend и frontend отправлены в отдельные окна. ===" -ForegroundColor Green
Read-Host "Нажми Enter, чтобы закрыть это окно"
