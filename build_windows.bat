@echo off
setlocal
set "PROJECT=%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
 set "PY=py -3"
) else (
 set "PY=python"
)
rem Release the source-folder handle before Python removes that folder.
cd /d "%SystemRoot%"
rem The complete final block is parsed before the batch file can be deleted.
(
 echo WARNING: After a successful build the entire extracted source folder is deleted.
 echo Keep ZIP backups and personal files OUTSIDE that source folder.
 %PY% -B "%PROJECT%build_windows.py" %*
 if errorlevel 1 (
  echo Build failed. Sources have not been automatically deleted.
 ) else (
  echo EXE installed. Review any cleanup or shortcut warnings above.
  echo Hardware monitoring still needs AIDA64, LHM or RTSS as appropriate.
 )
 pause
)
