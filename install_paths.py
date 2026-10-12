"""Destination derived from the source project's local Windows drive, not TEMP."""
from pathlib import PureWindowsPath

def installation_directory(project_directory):
    path=PureWindowsPath(str(project_directory))
    drive=path.drive
    if not path.is_absolute() or len(drive)!=2 or drive[1]!=':' or not drive[0].isascii() or not drive[0].isalpha():
        raise ValueError('Place the project on an absolute local drive-letter path, such as D:\\Projects\\PC-Monitor. Network paths are not supported.')
    return PureWindowsPath(drive+'\\')/'PC-Monitor'

def installed_exe_path(project_directory):
    return installation_directory(project_directory)/'PC-Monitor.exe'
