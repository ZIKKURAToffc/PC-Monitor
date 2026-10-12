import unittest,tempfile
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QComboBox
from PySide6.QtCore import QSettings,QTimer
import desktop,i18n
from dashboard import SLOTS
class GpuMemoryHeaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=patch('desktop.QSettings',return_value=QSettings(self.tmp.name+'/p.ini',QSettings.IniFormat));self.p.start();self.w=desktop.MonitorWindow(demo=True)
    def tearDown(self):self.w.close();self.p.stop();self.tmp.cleanup();i18n.set_language('ru')
    def test_memory_not_hotspot_and_missing_not_substituted(self):
        d=dict(self.w.current);d.update(gpu_temp=36,gpu_hotspot=88,gpu_mem_temp=40)
        for code,caption in [('ru','ПАМЯТЬ GPU'),('uk','ПАМ’ЯТЬ GPU'),('en','GPU MEMORY')]:
            i18n.set_language(code);self.w.gpu.update_data(d,85);self.assertEqual(self.w.gpu.detail.text(),caption+' 40 °C');self.assertEqual(self.w.gpu.temp.text(),'36 °C')
            d['gpu_mem_temp']=None;self.w.gpu.update_data(d,85);self.assertEqual(self.w.gpu.detail.text(),caption+' — °C');d['gpu_mem_temp']=40
    def test_hotspot_absent_from_both_assignment_dialogs(self):
        self.assertNotIn('gpu_hotspot',[x[0] for x in SLOTS]);errors=[]
        for method,prefix in [(self.w.configure_dashboard,'dashboardSensor_'),(self.w.sensor_help,'panelSensor_')]:
            def check():
                d=QApplication.activeModalWidget()
                try:
                    self.assertIsNone(d.findChild(QComboBox,prefix+'gpu_hotspot'));self.assertIsNotNone(d.findChild(QComboBox,prefix+'gpu_mem_temp'))
                except Exception as e:errors.append(e)
                finally:d.reject()
            QTimer.singleShot(20,check);method()
        if errors:raise errors[0]
