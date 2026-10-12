"""Create the current user's Desktop shortcut after a successful Windows build."""
import os,sys,subprocess
from pathlib import Path
from install_paths import installed_exe_path
SCRIPT=r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$target = $env:PC_MONITOR_SHORTCUT_TARGET
if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw 'EXE not found' }
$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
if ([string]::IsNullOrWhiteSpace($desktop)) { throw 'Desktop directory unavailable' }
$link = Join-Path $desktop 'PC Monitor.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($link)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = [IO.Path]::GetDirectoryName($target)
$shortcut.IconLocation = $target + ',0'
$shortcut.Description = 'PC Monitor'
$shortcut.WindowStyle = 1
$shortcut.Save()
if (-not (Test-Path -LiteralPath $link -PathType Leaf)) { throw 'Shortcut was not saved' }
[Console]::WriteLine($link)
'''

def create_shortcut(target):
    if os.name!='nt':raise RuntimeError('Desktop shortcut creation is available on Windows only.')
    target=Path(target).resolve()
    if not target.is_file() or target.suffix.lower()!='.exe':raise ValueError('A compiled EXE is required.')
    env=os.environ.copy();env['PC_MONITOR_SHORTCUT_TARGET']=str(target)
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',SCRIPT],env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=20,check=True)
    return result.stdout.strip()

def default_target(project_directory=None):
    return installed_exe_path(project_directory if project_directory is not None else Path(__file__).resolve().parent)

def main():
    try:
        target=sys.argv[1] if len(sys.argv)>1 and sys.argv[1] else default_target()
        print('Desktop shortcut:',create_shortcut(target));return 0
    except Exception as e:
        print('Shortcut not created:',str(e),file=sys.stderr)
        if isinstance(e,subprocess.CalledProcessError) and e.stderr:print(e.stderr.strip(),file=sys.stderr)
        return 1
if __name__=='__main__':raise SystemExit(main())
