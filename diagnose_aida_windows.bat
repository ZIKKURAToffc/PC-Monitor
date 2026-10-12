@echo off
setlocal
cd /d "%~dp0"
echo Exports AIDA64 sensor labels and values locally. Review before sharing.
if not exist ".venv\Scripts\python.exe" (
 echo First run start_windows.bat to install Python dependencies.
 pause
 exit /b 1
)
.venv\Scripts\python.exe aida_dump.py --output aida-sensors.xml
pause
