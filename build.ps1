$ErrorActionPreference = "Stop"

Write-Host "Creating virtual environment..."
python -m venv .venv

Write-Host "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "Installing requirements..."
pip install -r requirements.txt

Write-Host "Building executable with PyInstaller..."
pyinstaller --noconfirm --onefile --name data-entry-bot --add-data "README.md;." --paths src src/data_entry_bot/main.py

Write-Host "Build complete. Executable located at: dist\\data-entry-bot.exe"

