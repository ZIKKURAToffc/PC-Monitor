import os,tempfile,unittest
from pathlib import Path,PosixPath
from unittest.mock import patch,MagicMock
import windows_shell as shell

class ShellTests(unittest.TestCase):
    def test_style_preserves_other_bits(self):
        source=shell.WS_EX_APPWINDOW|0x8|0x100
        self.assertEqual(shell.taskbar_style(source),0x8|0x100|shell.WS_EX_TOOLWINDOW)
    def test_nonwindows(self):
        with patch('windows_shell.os.name','posix'):
            self.assertFalse(shell.hide_taskbar_entry(123)['hidden_from_taskbar'])
    def run_native(self,success):
        u=MagicMock();u.GetWindowLongPtrW.return_value=shell.WS_EX_APPWINDOW|8;u.GetWindowLongW.return_value=shell.WS_EX_APPWINDOW|8
        u.SetWindowLongPtrW.return_value=8;u.SetWindowLongW.return_value=8;u.SetWindowPos.return_value=success
        with patch('windows_shell.os.name','nt'),patch('windows_shell.ctypes.WinDLL',return_value=u,create=True),patch('windows_shell.ctypes.set_last_error',create=True),patch('windows_shell.ctypes.get_last_error',return_value=0,create=True):
            report=shell.hide_taskbar_entry(123)
        return u,report
    def test_native_does_not_hide_minimize_move(self):
        u,r=self.run_native(1);self.assertTrue(r['hidden_from_taskbar']);u.ShowWindow.assert_not_called()
        self.assertEqual(u.SetWindowPos.call_args.args,(123,None,0,0,0,0,shell.SWP_NO_SIZE_MOVE_ACTIVATE))
    def test_failure_rolls_back(self):
        u,r=self.run_native(0);self.assertFalse(r['hidden_from_taskbar'])
        setter=u.SetWindowLongPtrW if shell.ctypes.sizeof(shell.ctypes.c_void_p)==8 else u.SetWindowLongW
        self.assertEqual(setter.call_args.args,(123,shell.GWL_EXSTYLE,shell.WS_EX_APPWINDOW|8))
    def test_shortcut_paths_safe_normal_window(self):
        import create_shortcut as c
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'Тест PC.exe';target.write_bytes(b'test')
            with patch('create_shortcut.os.name','nt'),patch('create_shortcut.Path',PosixPath),patch('create_shortcut.subprocess.run') as run:
                run.return_value.stdout='Desktop/PC Monitor.lnk\n';c.create_shortcut(target)
                args,kw=run.call_args;self.assertEqual(kw['env']['PC_MONITOR_SHORTCUT_TARGET'],str(target.resolve()));self.assertNotIn(str(target),args[0][-1]);self.assertTrue(kw['check'])
        self.assertIn('DesktopDirectory',c.SCRIPT);self.assertIn('$shortcut.WindowStyle = 1',c.SCRIPT);self.assertIn('-LiteralPath',c.SCRIPT);self.assertNotIn('ExecutionPolicy',c.SCRIPT)
    def test_missing_exe_no_shortcut(self):
        import create_shortcut as c
        with patch('create_shortcut.os.name','nt'),patch('create_shortcut.Path',PosixPath),patch('create_shortcut.subprocess.run') as run:
            with self.assertRaises(ValueError):c.create_shortcut('/no/file.exe')
            run.assert_not_called()
    def test_build_shortcut_after_success_guard(self):
        text=Path('build_windows.py').read_text();self.assertLess(text.index('run(pyinstaller_command'),text.index('create_shortcut(target)'));self.assertIn('check=True',text);self.assertIn('-B "%PROJECT%build_windows.py"',Path('build_windows.bat').read_text())


from PySide6.QtCore import QObject,Signal,QSettings,Qt
from PySide6.QtWidgets import QApplication,QSystemTrayIcon
class FakeTray(QObject):
    activated=Signal(object)
    Trigger=QSystemTrayIcon.Trigger;DoubleClick=QSystemTrayIcon.DoubleClick
    available=True
    @staticmethod
    def isSystemTrayAvailable():return FakeTray.available
    def __init__(self,icon,parent):super().__init__(parent);self.visible=False
    def setContextMenu(self,menu):self.menu=menu
    def setToolTip(self,text):self.tooltip=text
    def show(self):self.visible=True
    def hide(self):self.visible=False

class TrayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        import desktop,i18n
        i18n.set_language('ru');self.tmp=tempfile.TemporaryDirectory();self.settings=QSettings(self.tmp.name+'/prefs.ini',QSettings.IniFormat)
        self.p1=patch('desktop.QSettings',return_value=self.settings);self.p1.start();self.p2=patch('desktop.QSystemTrayIcon',FakeTray);self.p2.start();self.p3=patch('desktop.hide_taskbar_entry',return_value={'state':'applied','hidden_from_taskbar':True});self.native=self.p3.start();FakeTray.available=True;self.w=None
    def make(self):
        import desktop
        self.w=desktop.MonitorWindow(demo=True,tray_mode=True);self.w.show();self.app.processEvents();return self.w
    def tearDown(self):
        if self.w:self.w.close()
        FakeTray.available=True;self.p3.stop();self.p2.stop();self.p1.stop();self.tmp.cleanup()
    def test_visible_start_and_no_minimize_button(self):
        w=self.make();self.assertTrue(w.isVisible());self.assertFalse(w.isMinimized());self.assertTrue(w.tray_icon.visible);self.native.assert_called();self.assertFalse(w.windowFlags()&Qt.WindowMinimizeButtonHint)
    def test_show_restores_minimized_window(self):
        w=self.make();w.showMinimized();w.tray_show.trigger();self.app.processEvents();self.assertTrue(w.isVisible());self.assertFalse(w.isMinimized())
    def test_pause_and_close(self):
        w=self.make();w.tray_pause.trigger();self.assertTrue(w.paused);self.assertEqual(w.tray_pause.text(),'Продолжить');w.tray_pause.trigger();self.assertFalse(w.paused);w.close();self.assertFalse(w.tray_icon.visible);self.assertFalse(w.timer.isActive())
    def test_no_tray_keeps_normal_visible_window(self):
        FakeTray.available=False;w=self.make();self.assertTrue(w.isVisible());self.assertFalse(w.tray_enabled);self.native.assert_not_called()
