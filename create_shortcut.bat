@echo off
setlocal
cd /d "%~dp0"
set "TARGET=%~1"
if exist ".venv\Scripts\python.exe" (
 .venv\Scripts\python.exe create_shortcut.py "%TARGET%"
) else (
 where py >nul 2>nul
 if errorlevel 1 (
  python -B create_shortcut.py "%TARGET%"
 ) else (
  py -3 -B create_shortcut.py "%TARGET%"
 )
)
if errorlevel 1 (
 echo Could not create the shortcut. Check the EXE path and Desktop access.
 pause
 exit /b 1
)
pause
exit /b 0
