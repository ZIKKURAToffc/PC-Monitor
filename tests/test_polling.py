import unittest,tempfile
from unittest.mock import patch
from telemetry import Collector
class FakeStop:
    def __init__(self,cycles=3):self.cycles=cycles;self.waits=[]
    def is_set(self):return len(self.waits)>=self.cycles
    def wait(self,seconds):self.waits.append(seconds);return self.is_set()
class PollingTests(unittest.TestCase):
    def test_defaults_and_bounds(self):
        c=Collector();self.assertEqual(c.poll_ms,500);self.assertEqual(c.system_period,.25)
        for value,expected in [(0,250),(10000,5000),('bad',500),(250,250),(1000,1000)]:c.set_poll_interval(value);self.assertEqual(c.poll_ms,expected)
    def test_slow_backend_and_connection_failure_throttle(self):
        c=Collector();c.set_poll_interval(250);self.assertEqual(c.effective_poll_ms(),250);c.transport='WMI';self.assertEqual(c.effective_poll_ms(),2000)
        c.transport='HTTP';c.diagnostics={'connected':False};self.assertEqual(c.effective_poll_ms(),2000);c.set_poll_interval(3000);self.assertEqual(c.effective_poll_ms(),3000)
    def test_hardware_deadline_subtracts_read_time(self):
        c=Collector();c.stop=FakeStop();c._hardware_once=lambda:{'value':1}
        with patch('telemetry.time.monotonic',side_effect=[0,.2,.5,.7,1,1.2]):c._hardware_loop()
        for wait in c.stop.waits:self.assertAlmostEqual(wait,.3)
        self.assertEqual(c.hardware['value'],1)
    def test_failed_poll_backs_off(self):
        c=Collector();c.stop=FakeStop(1)
        with patch.object(c,'_hardware_once',side_effect=OSError()),patch('telemetry.time.monotonic',side_effect=[0,.1]):c._hardware_loop()
        self.assertAlmostEqual(c.stop.waits[0],1.9)
    def test_nvidia_queries_not_per_fast_tick_and_errors_not_stale(self):
        c=Collector();c.nv='nvidia-smi'
        with patch('telemetry.time.monotonic',side_effect=[0,.25,1.1]),patch('telemetry.command',side_effect=['first','second']) as query:
            self.assertEqual(c._nvidia_output(),'first');self.assertEqual(c._nvidia_output(),'first');self.assertEqual(c._nvidia_output(),'second');self.assertEqual(query.call_count,2)
        with patch('telemetry.time.monotonic',side_effect=[2.2,2.4]),patch('telemetry.command',side_effect=OSError()) as query:
            for _ in range(2):
                with self.assertRaises(OSError):c._nvidia_output()
            self.assertEqual(query.call_count,1);self.assertIsNone(c._nv_cache)
class PollingSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        import desktop
        from PySide6.QtCore import QSettings
        self.tmp=tempfile.TemporaryDirectory();self.prefs=QSettings(self.tmp.name+'/p.ini',QSettings.IniFormat);self.p=patch('desktop.QSettings',return_value=self.prefs);self.p.start();self.w=desktop.MonitorWindow(demo=True)
    def tearDown(self):
        import i18n
        self.w.close();self.p.stop();self.tmp.cleanup();i18n.set_language('ru')
    def dialog(self,accept=True):
        from PySide6.QtWidgets import QApplication,QComboBox
        from PySide6.QtCore import QTimer
        errors=[]
        def edit():
            d=QApplication.activeModalWidget()
            try:
                for name,value in [('interfaceRefresh',250),('sensorPolling',250)]:
                    box=d.findChild(QComboBox,name);self.assertIsNotNone(box);box.setCurrentIndex(box.findData(value))
                d.accept() if accept else d.reject()
            except Exception as e:errors.append(e);d.reject()
        QTimer.singleShot(20,edit);self.w.show_settings()
        if errors:raise errors[0]
    def test_save_updates_timers_and_restore(self):
        import desktop
        self.dialog();self.assertEqual(self.w.collector.poll_ms,250);self.assertEqual(self.w.timer.interval(),250);self.assertEqual(int(self.prefs.value('sensor_poll_ms')),250)
        other=desktop.MonitorWindow(demo=True)
        try:self.assertEqual(other.collector.poll_ms,250);self.assertEqual(other.timer.interval(),250)
        finally:other.close()
    def test_cancel_preserves_and_old_ui_preference_not_overwritten(self):
        self.dialog(False);self.assertEqual(self.w.collector.poll_ms,500);self.assertEqual(self.w.interval,500)
        import desktop
        self.prefs.setValue('interval',2000);other=desktop.MonitorWindow(demo=True)
        try:self.assertEqual(other.interval,2000);self.assertEqual(other.collector.poll_ms,500)
        finally:other.close()
    def test_polling_label_translated(self):
        import i18n
        for lang,expected in [('ru','Опрос датчиков'),('uk','Опитування датчиків'),('en','Sensor polling')]:i18n.set_language(lang);self.assertEqual(i18n.t('Опрос датчиков'),expected)
