@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
 set "PY=py -3"
) else (
 set "PY=python"
)
%PY% --version
if errorlevel 1 goto missing
if not exist ".venv\Scripts\pythonw.exe" (
 %PY% -m venv .venv
 if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
start "" ".venv\Scripts\pythonw.exe" "%~dp0desktop.py"
exit /b 0
:missing
echo Install 64-bit Python 3.10+ from python.org. Enable Add Python to PATH.
pause
exit /b 1
:fail
echo Setup failed. Check Python and internet access. Qt requires Windows 10/11 64-bit.
pause
exit /b 1
