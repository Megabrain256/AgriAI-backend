# PowerShell script to run the FastAPI server with Python 3.12
# This ensures we use the correct Python version from the virtual environment

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting AgriAI Backend Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Activate virtual environment
Write-Host "`n[1/3] Activating Python 3.12 virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Verify Python version
Write-Host "`n[2/3] Verifying Python version..." -ForegroundColor Yellow
$pythonVersion = python --version
Write-Host "   $pythonVersion" -ForegroundColor Green

if ($pythonVersion -notmatch "Python 3\.12") {
    Write-Host "`n[ERROR] Wrong Python version detected!" -ForegroundColor Red
    Write-Host "   Expected: Python 3.12" -ForegroundColor Yellow
    Write-Host "   Detected: $pythonVersion" -ForegroundColor Yellow
    Write-Host "`nPlease activate the virtual environment first:" -ForegroundColor Yellow
    Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    exit 1
}

# Verify app imports
Write-Host "`n[3/3] Verifying app imports..." -ForegroundColor Yellow
try {
    python -c "import app; print('[OK] App imports successfully')" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Import failed"
    }
    Write-Host "   [OK] App imports successfully" -ForegroundColor Green
} catch {
    Write-Host "   [ERROR] App import failed!" -ForegroundColor Red
    Write-Host "   Please check your dependencies: pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Start server
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Starting uvicorn server..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nServer will be available at:" -ForegroundColor Yellow
Write-Host "   http://localhost:8000" -ForegroundColor Green
Write-Host "   http://localhost:8000/docs" -ForegroundColor Green
Write-Host "`nPress Ctrl+C to stop the server`n" -ForegroundColor Yellow

uvicorn app:app --reload --host 0.0.0.0 --port 8000

