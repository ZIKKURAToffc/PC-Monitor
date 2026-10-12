import tempfile,unittest
from unittest.mock import patch
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
import desktop,i18n
class MotherboardHeaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.settings=QSettings(self.tmp.name+'/prefs.ini',QSettings.IniFormat);self.p=patch('desktop.QSettings',return_value=self.settings);self.p.start();self.w=desktop.MonitorWindow(demo=True);self.w.resize(1366,768);self.w.show();self.app.processEvents()
    def tearDown(self):self.w.close();self.p.stop();self.tmp.cleanup();i18n.set_language('ru')
    def test_standard_temperature_in_sys_header(self):
        self.assertEqual(self.w.board_temp.text(),'29,0 °C');self.assertTrue(self.w.board_temp.isVisible());self.assertEqual(self.w.board_temp.parent(),self.w.sys_header);self.assertEqual(self.w.board_caption.text(),'ПЛАТА');self.assertIn('System',self.w.board_temp.toolTip())
    def test_shared_manual_mapping_matches_thermal(self):
        self.w.dashboard_config={'slots':{'sys_temp':{'sensor':'demo/8'}}};self.w.refresh();self.assertEqual(self.w.board_temp.text(),'29,0 °C');self.assertEqual(self.w.thermal_metrics['sys_temp'].value.text(),'29,0');self.assertIn('System',self.w.board_temp.toolTip())
    def test_missing_sensor_no_fallback(self):
        self.w.dashboard_config={'slots':{'sys_temp':{'sensor':'missing'}}};self.w.refresh();self.assertEqual(self.w.board_temp.text(),'— °C');self.assertIsNone(self.w.current['sys_temp'])
    def test_localization_and_custom_label(self):
        for code,label,value in [('uk','ПЛАТА','29,0 °C'),('en','MOTHERBOARD','29.0 °C'),('ru','ПЛАТА','29,0 °C')]:
            i18n.set_language(code);self.w.refresh();self.assertEqual(self.w.board_caption.text(),label);self.assertEqual(self.w.board_temp.text(),value)
        self.w.dashboard_config={'slots':{'sys_temp':{'label':'Моя плата'}}};i18n.set_language('en');self.w.refresh();self.assertEqual(self.w.board_caption.text(),'Моя плата')
    def test_hidden_and_zero_valid(self):
        self.w.dashboard_config={'slots':{'sys_temp':{'hidden':True}}};self.w.refresh();self.assertTrue(self.w.board_temp.isHidden());self.assertTrue(self.w.board_caption.isHidden())
        self.w.dashboard_config={};d=desktop.demo_snapshot();d['sys_temp']=0
        with patch('desktop.demo_snapshot',return_value=d):self.w.refresh();self.assertEqual(self.w.board_temp.text(),'0,0 °C');self.assertFalse(self.w.board_temp.isHidden())
    def test_hot_color_survives_paused_resize(self):
        d=desktop.demo_snapshot();d['sys_temp']=95
        with patch('desktop.demo_snapshot',return_value=d):self.w.refresh()
        self.assertIn('#942014',self.w.board_temp.styleSheet());self.w.paused=True;self.w.resize(1920,1080);self.w.adapt_layout();self.assertIn('#942014',self.w.board_temp.styleSheet());self.assertEqual(self.w.board_temp.text(),'95,0 °C')
