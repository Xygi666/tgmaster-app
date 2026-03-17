$rootPath     = "G:\projects\traffsoft"
$backendPath  = Join-Path $rootPath "traffsoft-backend"
$frontendPath = Join-Path $rootPath "traffsoft-frontend"

Write-Host "=== Рестарт TraffSoft ===" -ForegroundColor Cyan

# --- ОСТАНОВКА СТАРЫХ ПРОЦЕССОВ ---
Write-Host "-> Останавливаю старые процессы uvicorn и node..." -ForegroundColor Yellow
Get-Process -Name "python", "uvicorn", "node" -ErrorAction SilentlyContinue | Stop-Process -Force

Start-Sleep -Seconds 2

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

Write-Host "=== Рестарт завершён, открыты новые окна backend и frontend. ===" -ForegroundColor Green
Read-Host "Нажми Enter, чтобы закрыть это окно"
