import tempfile,unittest,json
from unittest.mock import patch
from PySide6.QtCore import QSettings,QTimer
from PySide6.QtWidgets import QApplication,QPushButton,QLabel
import desktop,i18n
from fps_diagnostics import FPS_GUIDE
class DeveloperContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.prefs=QSettings(self.tmp.name+'/p.ini',QSettings.IniFormat);self.p=patch('desktop.QSettings',return_value=self.prefs);self.p.start();self.w=desktop.MonitorWindow(demo=True);self.w.show()
    def tearDown(self):self.w.close();self.p.stop();self.tmp.cleanup();i18n.set_language('ru')
    def test_neutral_default_and_export_build_names(self):
        from pathlib import Path
        self.assertEqual(self.w.brand_label.text(),'PC MONITOR');self.assertNotIn('ZIKKURAT',self.w.windowTitle());self.assertEqual(desktop.clean_nickname(''),'PC MONITOR');self.assertIn('PC-Monitor',__import__('build_windows').pyinstaller_command(Path.cwd(),Path('/scratch'),'python.exe'));self.assertTrue(Path('monitor.ico').exists())
    def test_legacy_default_migrates_without_resetting_settings(self):
        cfg={'slots':{'cpu_temp':{'sensor':'demo/1'}}};self.prefs.setValue('dashboard_config_v1',json.dumps(cfg));self.prefs.setValue('display_name','ZIKKURAT');self.prefs.setValue('display_hardware_gpu','My GPU');self.prefs.remove('neutral_branding_v1')
        other=desktop.MonitorWindow(demo=True)
        try:self.assertEqual(other.nickname,'PC MONITOR');self.assertEqual(other.dashboard_config,cfg);self.assertEqual(other.hardware_names['gpu'],'My GPU');self.assertEqual(other.current['cpu_temp'],43)
        finally:other.close()
    def test_user_title_preserved(self):
        self.prefs.setValue('display_name','Roman PC');self.prefs.remove('neutral_branding_v1');other=desktop.MonitorWindow(demo=True)
        try:self.assertEqual(other.nickname,'Roman PC')
        finally:other.close()
    def test_game_specific_description_removed_all_languages(self):
        for lang in ('ru','uk','en'):
            i18n.set_language(lang);guide=i18n.t(FPS_GUIDE);self.assertNotIn('AION',guide);self.assertNotIn('ZIKKURAT',guide);self.assertIn('SRTSSFPS',guide)
    def test_settings_developer_name_only_and_no_external_open(self):
        errors=[]
        def inspect():
            d=QApplication.activeModalWidget()
            try:self.assertEqual(d.findChild(QPushButton,'developerButton').text(),'ZIKKURAT');self.assertIsNone(d.findChild(QLabel,'developerContact'))
            except Exception as e:errors.append(e)
            finally:d.reject()
        with patch('desktop.QDesktopServices.openUrl',return_value=True) as opening:
            QTimer.singleShot(20,inspect);self.w.show_settings();opening.assert_not_called()
        if errors:raise errors[0]
    def test_button_opens_name_only_developer_dialog(self):
        errors=[]
        def about():
            d=QApplication.activeModalWidget()
            try:
                self.assertEqual(d.objectName(),'developerDialog');self.assertEqual(d.findChild(QLabel,'developerName').text(),'ZIKKURAT');self.assertEqual([b.text() for b in d.findChildren(QPushButton)],['Закрыть'])
            except Exception as e:errors.append(e)
            finally:d.accept()
        def settings():
            d=QApplication.activeModalWidget();QTimer.singleShot(20,about);d.findChild(QPushButton,'developerButton').click();d.reject()
        with patch('desktop.QDesktopServices.openUrl',return_value=True) as opening:
            QTimer.singleShot(20,settings);self.w.show_settings();opening.assert_not_called()
        if errors:raise errors[0]
    def test_developer_dialog_translated_name_only(self):
        errors=[]
        for lang,title in [('uk','Розробник'),('en','Developer'),('ru','Разработчик')]:
            i18n.set_language(lang)
            def inspect():
                d=QApplication.activeModalWidget()
                try:self.assertEqual(d.windowTitle(),title);self.assertEqual(d.findChild(QLabel,'developerName').text(),'ZIKKURAT');self.assertEqual(len(d.findChildren(QPushButton)),1)
                except Exception as e:errors.append(e)
                finally:d.accept()
            QTimer.singleShot(20,inspect);self.w.show_developer()
        if errors:raise errors[0]
    def test_personal_hostname_not_displayed_raw_snapshot_unchanged(self):
        snapshot=desktop.demo_snapshot();snapshot['hostname']='ZIKKURAT'
        with patch('desktop.demo_snapshot',return_value=snapshot):self.w.refresh()
        self.assertNotIn('ZIKKURAT',self.w.status.text());self.assertEqual(self.w.current['hostname'],'ZIKKURAT')
