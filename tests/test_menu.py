import tempfile,unittest
from unittest.mock import patch

class GearMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        import desktop
        from PySide6.QtCore import QSettings
        self.d=tempfile.TemporaryDirectory();self.settings=QSettings(self.d.name+'/prefs.ini',QSettings.IniFormat);self.p=patch('desktop.QSettings',return_value=self.settings);self.p.start();self.w=desktop.MonitorWindow(demo=True);self.w.resize(1366,768);self.w.show();self.app.processEvents()
    def tearDown(self):self.w.control_menu.close();self.w.close();self.p.stop();self.d.cleanup()
    def test_all_actions_and_no_toolbar_buttons(self):
        from PySide6.QtWidgets import QPushButton
        self.assertEqual([a.text() for a in self.w.control_menu.actions()],['Разделы','Пауза','Экспорт JSON','Подключить датчики','Панель / датчики','Настройки','Полный экран','Компактно'])
        self.assertFalse(self.w.findChildren(QPushButton));self.assertEqual(self.w.tabs.count(),3);self.assertTrue(self.w.gear_button.accessibleName())
    def test_adjacent_to_status(self):
        self.w.connection.setText('LIVE / ЛОКАЛЬНЫЙ МОНИТОРИНГ');self.app.processEvents()
        self.assertGreater(self.w.gear_button.x(),self.w.connection.geometry().right());self.assertLess(self.w.gear_button.x()-self.w.connection.geometry().right(),12);self.assertFalse(self.w.connection.wordWrap())
    def test_pause_action_and_resume(self):
        self.w.pause_button.trigger();self.assertTrue(self.w.paused);self.assertEqual(self.w.pause_button.text(),'Продолжить')
        self.w.pause_button.trigger();self.assertFalse(self.w.paused);self.assertEqual(self.w.pause_button.text(),'Пауза')
    def test_compact_action_and_fullscreen_sync(self):
        self.w.compact_button.trigger();self.assertFalse(self.w.compact_mode);self.assertFalse(self.settings.value('compact_original'))
        self.w.compact_button.trigger();self.assertTrue(self.w.compact_mode)
        self.w.fullscreen_action.trigger();self.app.processEvents();self.assertTrue(self.w.isFullScreen());self.w.sync_control_menu();self.assertTrue(self.w.fullscreen_action.isChecked())
        self.w.escape();self.app.processEvents();self.w.sync_control_menu();self.assertFalse(self.w.fullscreen_action.isChecked())
    def test_gear_opens_menu(self):
        from PySide6.QtCore import QTimer,Qt
        from PySide6.QtTest import QTest
        seen=[]
        def close():seen.append(self.w.control_menu.isVisible());self.w.control_menu.close()
        QTimer.singleShot(60,close);QTest.mouseClick(self.w.gear_button,Qt.LeftButton);QTest.qWait(100);self.app.processEvents();self.assertEqual(seen,[True])
