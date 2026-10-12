"""Opt-in Windows login startup for the current user. No elevation or machine-wide writes."""
import os,sys
from pathlib import Path
RUN_KEY=r'Software\Microsoft\Windows\CurrentVersion\Run'
VALUE_NAME='PC Monitor'

def is_windows():return os.name=='nt'
def registry():
    import winreg
    return winreg

def launch_command():
    if not getattr(sys,'frozen',False):raise ValueError('Autostart requires the compiled Windows EXE.')
    path=Path(sys.executable).resolve()
    if not path.is_file() or path.suffix.lower()!='.exe':raise ValueError('The current EXE was not found.')
    value=str(path)
    if any(c in value for c in ('"','\0','\r','\n')):raise ValueError('Invalid EXE path.')
    return '"'+value+'"'

def read_command(reg):
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER,RUN_KEY,0,reg.KEY_READ) as key:
            value,kind=reg.QueryValueEx(key,VALUE_NAME)
        return value if isinstance(value,str) and kind in (reg.REG_SZ,reg.REG_EXPAND_SZ) else ''
    except FileNotFoundError:return ''

def current_status():
    state={'supported':is_windows(),'readable':False,'enabled':False,'can_enable':False,'matches_current':False,'error':None}
    if not state['supported']:return state
    try:
        command=read_command(registry());state.update(readable=True,enabled=bool(command))
        try:desired=launch_command();state.update(can_enable=True,matches_current=command==desired)
        except ValueError:pass
    except OSError as e:state['error']=str(e)
    return state

def set_enabled(enabled):
    if not is_windows():raise RuntimeError('Autostart is available on Windows only.')
    desired=launch_command() if enabled else ''
    reg=registry()
    if enabled:
        with reg.CreateKeyEx(reg.HKEY_CURRENT_USER,RUN_KEY,0,reg.KEY_SET_VALUE) as key:
            reg.SetValueEx(key,VALUE_NAME,0,reg.REG_SZ,desired)
    else:
        try:
            with reg.OpenKey(reg.HKEY_CURRENT_USER,RUN_KEY,0,reg.KEY_SET_VALUE) as key:reg.DeleteValue(key,VALUE_NAME)
        except FileNotFoundError:pass
    actual=read_command(reg)
    if actual!=desired:raise OSError('Autostart change could not be verified.')
    return {'enabled':bool(actual),'matches_current':bool(enabled)}
