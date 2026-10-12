import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import autostart
class FakeKey:
    def __init__(self,reg):self.reg=reg
    def __enter__(self):return self
    def __exit__(self,*args):pass
class FakeRegistry:
    HKEY_CURRENT_USER='HKCU';KEY_READ=1;KEY_SET_VALUE=2;REG_SZ=1;REG_EXPAND_SZ=2
    def __init__(self):self.values={'Another application':('untouched.exe',1)};self.calls=[];self.deny_read=False;self.deny_write=False
    def OpenKey(self,hive,key,zero,access):
        self.calls.append(('open',hive,key,access))
        if self.deny_read and access==self.KEY_READ:raise PermissionError('Read denied')
        if self.deny_write and access==self.KEY_SET_VALUE:raise PermissionError('Write denied')
        return FakeKey(self)
    def CreateKeyEx(self,hive,key,zero,access):
        self.calls.append(('create',hive,key,access))
        if self.deny_write:raise PermissionError('Write denied')
        return FakeKey(self)
    def QueryValueEx(self,key,name):
        if name not in self.values:raise FileNotFoundError()
        return self.values[name]
    def SetValueEx(self,key,name,zero,kind,value):self.calls.append(('set',name,value));self.values[name]=(value,kind)
    def DeleteValue(self,key,name):
        self.calls.append(('delete',name))
        if name not in self.values:raise FileNotFoundError()
        del self.values[name]

class StartupBackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.exe=Path(self.tmp.name)/'Мой PC Monitor.exe';self.exe.write_bytes(b'EXE fixture');self.reg=FakeRegistry();self.patches=[patch('autostart.is_windows',return_value=True),patch('autostart.registry',return_value=self.reg),patch.object(autostart.sys,'frozen',True,create=True),patch.object(autostart.sys,'executable',str(self.exe))]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()
    def test_other_platform_does_not_access_registry(self):
        with patch('autostart.is_windows',return_value=False),patch('autostart.registry') as reg:
            self.assertFalse(autostart.current_status()['supported'])
            with self.assertRaises(RuntimeError):autostart.set_enabled(True)
            reg.assert_not_called()
    def test_default_is_off_no_write(self):
        s=autostart.current_status();self.assertTrue(s['can_enable']);self.assertFalse(s['enabled']);self.assertFalse(any(x[0] in ('set','create','delete') for x in self.reg.calls))
    def test_enable_quoted_current_exe_current_user_only(self):
        result=autostart.set_enabled(True);self.assertTrue(result['enabled']);self.assertEqual(self.reg.values[autostart.VALUE_NAME],('"'+str(self.exe.resolve())+'"',self.reg.REG_SZ));self.assertTrue(autostart.current_status()['matches_current'])
        for x in self.reg.calls:
            if x[0] in ('open','create'):self.assertEqual(x[1:3],('HKCU',autostart.RUN_KEY))
    def test_disable_only_owned_value(self):
        autostart.set_enabled(True);autostart.set_enabled(False);self.assertNotIn(autostart.VALUE_NAME,self.reg.values);self.assertEqual(self.reg.values['Another application'],('untouched.exe',1))
    def test_disable_missing_is_idempotent(self):
        self.assertFalse(autostart.set_enabled(False)['enabled']);self.assertFalse(any(x[0]=='create' for x in self.reg.calls))
    def test_source_cannot_enable_but_can_remove_old_entry(self):
        with patch.object(autostart.sys,'frozen',False):
            self.assertFalse(autostart.current_status()['can_enable'])
            with self.assertRaises(ValueError):autostart.set_enabled(True)
            self.reg.values[autostart.VALUE_NAME]=('old.exe',1);autostart.set_enabled(False);self.assertNotIn(autostart.VALUE_NAME,self.reg.values)
    def test_read_error_is_reported_not_enabled(self):
        self.reg.deny_read=True;s=autostart.current_status();self.assertFalse(s['readable']);self.assertFalse(s['enabled']);self.assertIn('denied',s['error'])
    def test_write_error_is_not_reported_as_success(self):
        self.reg.deny_write=True
        with self.assertRaises(PermissionError):autostart.set_enabled(True)
        self.assertNotIn(autostart.VALUE_NAME,self.reg.values)
    def test_new_exe_path_updates_existing_registration_on_save(self):
        self.reg.values[autostart.VALUE_NAME]=('"old.exe"',1);self.assertFalse(autostart.current_status()['matches_current']);autostart.set_enabled(True);self.assertTrue(autostart.current_status()['matches_current'])
    def test_invalid_or_missing_exe_never_writes(self):
        self.exe.unlink()
        with self.assertRaises(ValueError):autostart.set_enabled(True)
        self.assertFalse(any(x[0]=='create' for x in self.reg.calls))

from PySide6.QtCore import QSettings,QTimer
from PySide6.QtWidgets import QApplication,QCheckBox,QDialogButtonBox,QLineEdit
class StartupSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        import desktop
        self.tmp=tempfile.TemporaryDirectory();self.prefs=QSettings(self.tmp.name+'/p.ini',QSettings.IniFormat);self.p=patch('desktop.QSettings',return_value=self.prefs);self.p.start();self.w=desktop.MonitorWindow(demo=True,tray_mode=False);self.w.timer.stop();self.w.show();self.state={'supported':True,'readable':True,'enabled':False,'can_enable':True,'matches_current':False,'error':None}
    def tearDown(self):self.w.close();self.w.deleteLater();self.p.stop();self.tmp.cleanup()
    def settings(self,callback,state=None,setter=None):
        errors=[]
        def inspect():
            d=QApplication.activeModalWidget()
            try:callback(d)
            except Exception as e:errors.append(e);d.reject()
        with patch('desktop.autostart_status',return_value=state or self.state),patch('desktop.set_autostart',side_effect=setter) as set_start:
            QTimer.singleShot(30,inspect);self.w.show_settings()
            calls=set_start.call_args_list
        if errors:raise errors[0]
        return calls
    def save(self,d):d.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok).click()
    def test_unsupported_option_disabled(self):
        state={**self.state,'supported':False,'readable':False,'can_enable':False}
        def inspect(d):self.assertFalse(d.findChild(QCheckBox,'startWithWindows').isEnabled());d.reject()
        self.assertEqual(self.settings(inspect,state),[])
    def test_cancel_does_not_change_registration(self):
        def inspect(d):d.findChild(QCheckBox,'startWithWindows').setChecked(True);d.reject()
        self.assertEqual(self.settings(inspect),[])
    def test_enable_and_disable_committed_only_on_save(self):
        for before in (False,True):
            state={**self.state,'enabled':before,'matches_current':before}
            def inspect(d):d.findChild(QCheckBox,'startWithWindows').setChecked(not before);self.save(d)
            calls=self.settings(inspect,state);self.assertEqual(len(calls),1);self.assertEqual(calls[0].args,(not before,))
    def test_unchanged_enabled_does_not_rewrite(self):
        state={**self.state,'enabled':True,'matches_current':True};self.assertEqual(self.settings(self.save,state),[])
    def test_source_keeps_existing_exe_entry_without_re_registering(self):
        state={**self.state,'enabled':True,'can_enable':False,'matches_current':False};self.assertEqual(self.settings(self.save,state),[])
    def test_new_location_updates_on_explicit_save(self):
        state={**self.state,'enabled':True,'matches_current':False};calls=self.settings(self.save,state);self.assertEqual(calls[0].args,(True,))
    def test_failure_keeps_dialog_and_edits_open(self):
        import desktop
        before=self.w.nickname
        def inspect(d):
            d.findChild(QLineEdit,'displayName').setText('Unsaved title');d.findChild(QCheckBox,'startWithWindows').setChecked(True)
            with patch('desktop.QMessageBox.warning') as warning:
                self.save(d);warning.assert_called_once();self.assertTrue(d.isVisible());self.assertEqual(self.w.nickname,before)
            d.reject()
        self.settings(inspect,setter=PermissionError('Access denied'));self.assertEqual(self.w.nickname,before)
    def test_setting_localizes_in_all_languages(self):
        import i18n
        try:
            for language,caption in [('ru','Запускать вместе с Windows'),('uk','Запускати разом із Windows'),('en','Start with Windows')]:
                i18n.set_language(language)
                def inspect(d):self.assertEqual(d.findChild(QCheckBox,'startWithWindows').text(),caption);d.reject()
                self.settings(inspect)
        finally:i18n.set_language('ru')
