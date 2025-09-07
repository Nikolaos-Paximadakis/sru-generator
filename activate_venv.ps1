Write-Host "Activating sru_generator virtual environment..." -ForegroundColor Green
& .venv\Scripts\Activate.ps1
Write-Host "Virtual environment activated!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now run:" -ForegroundColor Yellow
Write-Host "  pytest tests/ -v" -ForegroundColor Cyan
Write-Host "  python -m build" -ForegroundColor Cyan
Write-Host "  python -c `"import sru_generator; print('Package imported successfully!')`"" -ForegroundColor Cyan
Write-Host ""
