"""One-file Windows build in an owned temporary workspace, removed after completion."""
import os,sys,struct,shutil,tempfile,subprocess,hashlib
from pathlib import Path
from create_shortcut import create_shortcut
from install_paths import installation_directory
from source_cleanup import remove_sources

def is_windows():return os.name=='nt'
def pyinstaller_command(root,workspace,python):
    root=Path(root).resolve();workspace=Path(workspace)
    return [str(python),'-B','-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed',
            '--name','PC-Monitor','--icon',str(root/'monitor.ico'),'--add-data',str(root/'assets')+';assets',
            '--workpath',str(workspace/'work'),'--specpath',str(workspace/'spec'),'--distpath',str(workspace/'output'),str(root/'desktop.py')]

def file_digest(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):digest.update(block)
    return digest.digest()

def publish_exe(source,destination_dir):
    source=Path(source);destination_dir=Path(destination_dir)
    if not source.is_file() or source.stat().st_size<64:raise ValueError('The compiled EXE is missing or empty.')
    with source.open('rb') as f:
        if f.read(2)!=b'MZ':raise ValueError('The build did not produce a Windows EXE.')
    destination_dir.mkdir(parents=True,exist_ok=True)
    # Copy to a unique staging file on the destination drive, then replace atomically.
    fd,name=tempfile.mkstemp(prefix='.PC-Monitor-',suffix='.tmp',dir=destination_dir);os.close(fd);staged=Path(name)
    target=destination_dir/'PC-Monitor.exe'
    try:
        shutil.copyfile(source,staged)
        if staged.stat().st_size!=source.stat().st_size or file_digest(staged)!=file_digest(source):raise OSError('Incomplete or corrupted EXE copy.')
        os.replace(staged,target)
    finally:staged.unlink(missing_ok=True)
    return target

def build(root=None,progress=print):
    if not is_windows():raise RuntimeError('Build on Windows 10/11 x64; PyInstaller does not cross-compile Windows EXEs.')
    if sys.version_info<(3,10) or struct.calcsize('P')!=8:raise RuntimeError('Use 64-bit Python 3.10 or newer.')
    root=Path(root or Path(__file__).resolve().parent).resolve()
    for name in ('desktop.py','monitor.ico','requirements-build.txt'):
        if not (root/name).is_file():raise FileNotFoundError(name)
    if not (root/'assets').is_dir():raise FileNotFoundError('assets')
    destination=Path(installation_directory(root))
    workspace=Path(tempfile.mkdtemp(prefix='pc-monitor-build-'))
    try:
        child_tmp=workspace/'tmp';child_tmp.mkdir();env=os.environ.copy()
        env.update(PYTHONDONTWRITEBYTECODE='1',PIP_NO_CACHE_DIR='1',PYINSTALLER_CONFIG_DIR=str(workspace/'cache'),TEMP=str(child_tmp),TMP=str(child_tmp))
        def run(args,label):
            progress(label);subprocess.run(args,cwd=str(root),env=env,check=True)
        venv=workspace/'venv';python=venv/'Scripts'/'python.exe'
        run([sys.executable,'-B','-m','venv',str(venv)],'Creating a temporary build environment...')
        run([str(python),'-B','-m','pip','install','--no-cache-dir','-r',str(root/'requirements-build.txt')],'Installing temporary build dependencies...')
        run(pyinstaller_command(root,workspace,python),'Building the one-file EXE...')
        target=publish_exe(workspace/'output'/'PC-Monitor.exe',destination)
        progress('DONE: '+str(target))
        try:progress('Desktop shortcut: '+create_shortcut(target))
        except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as e:
            progress('WARNING: EXE built, but shortcut creation failed: '+str(e)+'. Create a shortcut to the installed EXE manually if needed.')
        return target
    finally:
        # Only the unique workspace created above is deleted. Never source/.venv/user files.
        try:shutil.rmtree(workspace);progress('Temporary compiler, dependencies, caches and build files removed.')
        except OSError as e:progress('WARNING: Temporary cleanup incomplete: '+str(workspace)+' ('+str(e)+').')

def main():
    try:
        target=build()
        if '--keep-sources' not in sys.argv[1:]:
            try:remove_sources(Path(__file__).absolute().parent,target)
            except (OSError,ValueError) as e:
                print('WARNING: EXE installed, but source cleanup incomplete:',str(e),file=sys.stderr)
                print('Source folder may be partially removed; close files and remove the remaining source folder manually. Installed EXE is kept.',file=sys.stderr)
        try:subprocess.Popen(['explorer.exe',str(target.parent)])
        except OSError as e:print('WARNING: Cannot open installation folder:',str(e))
        return 0
    except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as e:
        print('Build failed:',str(e),file=sys.stderr)
        print('Any previous installed PC-Monitor.exe is kept. Check drive-root permissions and close a running EXE before replacement.',file=sys.stderr)
        return 1
if __name__=='__main__':raise SystemExit(main())
