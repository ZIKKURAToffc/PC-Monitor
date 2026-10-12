import unittest
from dashboard import apply_config,available_rows,compatible
from aida_bridge import parse_shared_memory
from telemetry import Collector
from unittest.mock import patch

class DashboardTests(unittest.TestCase):
    def test_fps_real_zero_missing(self):
        for val in ['144','0','N/A','240 FPS']:
            raw=f'<sys><id>SRTSSFPS</id><label>RTSS FPS</label><value>{val}</value></sys>';rows,dev=parse_shared_memory(raw);c=Collector();c.configure('aida');c.nv=None
            with patch('telemetry.read_aida64',return_value=(rows,dev,{})),patch('telemetry.psutil.sensors_temperatures',return_value={},create=True):d=c._hardware_once()
            self.assertEqual(d['fps'],{'144':144,'0':0,'N/A':None,'240 FPS':240}[val])
    def test_full_system_table_not_discarded(self):
        rows,_=parse_shared_memory('<sys><id>SMEMTIM</id><label>Memory Timings</label><value>16-18-18</value></sys><sys><id>SRTSSFPS</id><label>RTSS FPS</label><value>120</value></sys>')
        self.assertEqual(len(rows),2);self.assertEqual(rows[0]['TextValue'],'16-18-18');self.assertIsNone(rows[0]['Value'])
    def test_custom_override_zero_and_missing(self):
        s={'cpu_temp':99,'sensor_rows':[dict(id='x',unit='°C',value=0,name='CPU Package',type='Temperature',source='Test')],'sensor_labels':{}}
        conf={'slots':{'cpu_temp':{'sensor':'x'}}};d=apply_config(s,conf);self.assertEqual(d['cpu_temp'],0);self.assertEqual(s['cpu_temp'],99)
        s['sensor_rows']=[];self.assertIsNone(apply_config(s,conf)['cpu_temp'])
    def test_units_rejected(self):
        s={'cpu_rpm':1500,'sensor_rows':[dict(id='pwm',unit='%',value=50,name='PWM',source='Test')]}
        self.assertIsNone(apply_config(s,{'slots':{'cpu_rpm':{'sensor':'pwm'}}})['cpu_rpm'])
    def test_independent_os_rows(self):
        s={'ram_used':16,'cpu_usage':3,'vram_used':2,'vram_total':12};r={r['id']:r for r in available_rows(s)}
        self.assertEqual(r['system/ram_used']['unit'],'GiB');self.assertEqual(r['driver/vram_free']['value'],10)
    def test_no_fps_fabrication(self):
        self.assertIsNone(apply_config({'sensor_rows':[]},{'slots':{'fps':{'sensor':'not-found'}}})['fps'])

class DashboardQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def test_layout_and_custom_hide(self):
        import desktop
        from PySide6.QtWidgets import QBoxLayout

        w=desktop.MonitorWindow(demo=True);w.show()
        try:
            w.resize(700,600);self.app.processEvents();self.assertEqual(w.width(),700);self.assertEqual(w.cpu.responsive_row.direction(),QBoxLayout.TopToBottom)
            w.resize(1366,900);self.app.processEvents();self.assertEqual(w.cpu.responsive_row.direction(),QBoxLayout.LeftToRight)
            w.dashboard_config={'slots':{'cpu_rpm':{'hidden':True},'cpu_temp':{'sensor':'demo/1','label':'CPU выбран вручную'}},'custom':[{'sensor':'demo/fan/0','label':'Корпус','unit':'RPM'}]}
            w.rebuild_custom_cards();w.refresh();self.app.processEvents()
            self.assertEqual(w.current['cpu_temp'],43);self.assertTrue(w.cpu.metrics['cpu_rpm'].isHidden());self.assertEqual(w.custom_widgets[0][1].value.text(),'1 240');self.assertEqual(w.thermal_metrics['cpu_temp'].label.text(),'CPU выбран вручную')
            self.assertEqual(w.fps_metric.value.text(),'144')
        finally:w.close()
    def test_save_restore_selection(self):
        import tempfile,json
        import desktop
        from PySide6.QtCore import QSettings,QTimer
        from PySide6.QtWidgets import QApplication,QDialogButtonBox,QComboBox
        with tempfile.TemporaryDirectory() as folder:
            settings=QSettings(folder+'/settings.ini',QSettings.IniFormat)
            with patch('desktop.QSettings',return_value=settings):
                w=desktop.MonitorWindow(demo=True);w.show()
                def save():
                    d=QApplication.activeModalWidget();boxes=d.findChildren(QComboBox)
                    box=d.findChild(QComboBox,'dashboardSensor_cpu_temp');box.setCurrentIndex(box.findData('demo/1'))
                    d.findChild(QDialogButtonBox).button(QDialogButtonBox.Save).click()
                QTimer.singleShot(30,save);w.configure_dashboard()
                conf=json.loads(settings.value('dashboard_config_v1'));self.assertEqual(conf['slots']['cpu_temp']['sensor'],'demo/1');w.close()
                w2=desktop.MonitorWindow(demo=True);self.assertEqual(w2.current['cpu_temp'],43);w2.close()
