@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run start_windows.bat first to install dependencies.
 pause
 exit /b 1
)
.venv\Scripts\python.exe diagnose.py
pause
