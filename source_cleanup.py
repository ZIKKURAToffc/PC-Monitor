"""Delete only the marked extracted source tree, after a valid EXE is installed."""
import os,shutil,stat,time
from pathlib import Path

MARKER='.pc-monitor-source'
MARKER_CONTENT='PC-Monitor extracted sources: removable after successful build\n'

def validate_source_cleanup(root,target):
    raw=Path(root)
    if raw.is_symlink() or getattr(raw.lstat(),'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400):
        raise ValueError('Refusing to delete a source folder that is a link or junction.')
    root=raw.resolve();target=Path(target).resolve()
    if root==Path(root.anchor) or root==Path.home().resolve():raise ValueError('Refusing to delete a drive root or home folder.')
    if target.is_relative_to(root):raise ValueError('Installed EXE must be outside the source folder.')
    marker=root/MARKER
    if not marker.is_file() or marker.is_symlink() or marker.read_text(encoding='utf-8')!=MARKER_CONTENT:
        raise ValueError('Source ownership marker missing or invalid; source folder kept.')
    for name in ('desktop.py','build_windows.py','requirements-build.txt'):
        if not (root/name).is_file():raise ValueError('Not a complete PC-Monitor source folder.')
    if target.name!='PC-Monitor.exe' or not target.is_file() or target.stat().st_size<64:
        raise ValueError('Installed EXE missing or incomplete; sources kept.')
    with target.open('rb') as f:
        if f.read(2)!=b'MZ':raise ValueError('Installed file is not a Windows EXE; sources kept.')
    # Never follow externally redirected folders/files during recursive deletion.
    for folder,dirs,files in os.walk(root,followlinks=False):
        for path in [Path(folder),*(Path(folder)/name for name in dirs+files)]:
            info=path.lstat()
            if path.is_symlink() or getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400):
                raise ValueError('Source tree contains a link/junction; remove it before building with cleanup.')
    return root,target

def remove_sources(root,target,progress=print):
    root,target=validate_source_cleanup(root,target)
    # Release Python's working-directory handle before deleting the source tree.
    os.chdir(target.parent)
    for attempt in range(3):
        try:
            shutil.rmtree(root)
            progress('Extracted source folder removed: '+str(root))
            return
        except OSError:
            if not root.exists():return
            if attempt==2:raise
            time.sleep(0.5)
