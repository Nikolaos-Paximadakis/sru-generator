@echo off
echo Activating sru_generator virtual environment...
call .venv\Scripts\activate.bat
echo Virtual environment activated!
echo.
echo You can now run:
echo   pytest tests/ -v
echo   python -m build
echo   python -c "import sru_generator; print('Package imported successfully!')"
echo.
