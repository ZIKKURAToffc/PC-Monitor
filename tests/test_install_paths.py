import unittest,subprocess
from pathlib import Path,PureWindowsPath
from unittest.mock import patch
from install_paths import installation_directory,installed_exe_path
import create_shortcut as c
import build_windows as b

class InstallPathTests(unittest.TestCase):
    def test_system_drive(self):self.assertEqual(installed_exe_path(r'C:\Users\Me\Project'),PureWindowsPath(r'C:\PC-Monitor\PC-Monitor.exe'))
    def test_other_drive(self):self.assertEqual(installation_directory(r'D:\Downloads\Project'),PureWindowsPath(r'D:\PC-Monitor'))
    def test_removable_drive(self):self.assertEqual(installation_directory(r'F:\Project'),PureWindowsPath(r'F:\PC-Monitor'))
    def test_unicode_and_spaces(self):self.assertEqual(installation_directory('E:\\Мои проекты\\PC Monitor'),PureWindowsPath(r'E:\PC-Monitor'))
    def test_temp_on_other_drive_ignored(self):
        with patch.dict('os.environ',TEMP=r'C:\Temp',TMP=r'C:\Temp'):
            self.assertEqual(installation_directory(r'D:\Project'),PureWindowsPath(r'D:\PC-Monitor'))
    def test_unc_rejected(self):
        with self.assertRaises(ValueError):installation_directory(r'\\server\share\project')
    def test_drive_relative_rejected(self):
        with self.assertRaises(ValueError):installation_directory('D:project')
    def test_non_windows_path_rejected(self):
        for path in ('/data/project','project',r'\project'):
            with self.subTest(path=path),self.assertRaises(ValueError):installation_directory(path)
    def test_default_shortcut_uses_installation(self):self.assertEqual(c.default_target(r'D:\Source\Project'),PureWindowsPath(r'D:\PC-Monitor\PC-Monitor.exe'))
    def test_empty_shortcut_argument_uses_default(self):
        with patch('create_shortcut.sys.argv',['create_shortcut.py','']),patch('create_shortcut.default_target',return_value=r'D:\PC-Monitor\PC-Monitor.exe'),patch('create_shortcut.create_shortcut',return_value='link') as link:
            self.assertEqual(c.main(),0);link.assert_called_once_with(r'D:\PC-Monitor\PC-Monitor.exe')
    def test_explicit_shortcut_target_preserved(self):
        with patch('create_shortcut.sys.argv',['create_shortcut.py',r'E:\Apps\PC-Monitor.exe']),patch('create_shortcut.create_shortcut',return_value='link') as link:
            self.assertEqual(c.main(),0);link.assert_called_once_with(r'E:\Apps\PC-Monitor.exe')
    def test_explorer_uses_actual_published_directory(self):
        target=Path('/some/drive/PC-Monitor/PC-Monitor.exe')
        with patch('build_windows.remove_sources'),patch('build_windows.build',return_value=target),patch('build_windows.subprocess.Popen') as explorer:
            self.assertEqual(b.main(),0);explorer.assert_called_once_with(['explorer.exe',str(target.parent)])
    def test_explorer_failure_does_not_fail_build(self):
        with patch('build_windows.remove_sources'),patch('build_windows.build',return_value=Path('/installed/PC-Monitor.exe')),patch('build_windows.subprocess.Popen',side_effect=OSError('No explorer')):
            self.assertEqual(b.main(),0)
    def test_batches_no_longer_point_to_dist(self):
        for name in ('build_windows.bat','create_shortcut.bat'):
            self.assertNotIn('dist\\',Path(name).read_text())
