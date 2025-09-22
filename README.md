Automated Data Entry Bot for Notepad (Windows)

Overview
This project automates typing content into Notepad using Python and saves blog-style text files generated from the JSONPlaceholder API.

Prerequisites
- Windows 10 or 11 (use the old Notepad on Windows 11 from [here](https://www.winhelponline.com/blog/restore-old-classic-notepad-windows/))
- Python 3.10+ installed and added to PATH
- Internet access (to fetch posts)

You should see 10 Notepad windows open sequentially, each saving a post file to `Desktop`.

Build a Standalone Executable (venv)
```powershell
./build.ps1
```
The generated executable will be at `dist\data-entry-bot.exe`.

