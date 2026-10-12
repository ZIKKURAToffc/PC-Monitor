import unittest,tempfile
from unittest.mock import patch
from PySide6.QtCore import QDateTime,QTimeZone,Qt,QSettings
from clock_display import clock_data
class ClockDataTests(unittest.TestCase):
    def instant(self,stamp):return QDateTime.fromString(stamp,Qt.ISODate)
    def test_midnight_rollover_and_quarter_hour_zone(self):
        d=clock_data(self.instant('2026-01-01T23:30:00Z'),QTimeZone.fromSecondsAheadOfUtc(20700))
        self.assertEqual(d['date'],'02.01.2026');self.assertEqual(d['time'],'05:15:00');self.assertEqual(d['offset'],'UTC+05:45')
    def test_negative_offset_and_previous_date(self):
        d=clock_data(self.instant('2026-01-01T00:30:00Z'),QTimeZone.fromSecondsAheadOfUtc(-12600))
        self.assertEqual(d['date'],'31.12.2025');self.assertEqual(d['time'],'21:00:00');self.assertEqual(d['offset'],'UTC-03:30')
    def test_dst_offset_follows_current_date(self):
        zone=QTimeZone(b'Europe/Berlin')
        if not zone.isValid():self.skipTest('Timezone database unavailable')
        self.assertEqual(clock_data(self.instant('2026-01-01T12:00:00Z'),zone)['offset'],'UTC+01:00');self.assertEqual(clock_data(self.instant('2026-07-01T12:00:00Z'),zone)['offset'],'UTC+02:00')
    def test_invalid_zone_falls_back_utc(self):
        d=clock_data(self.instant('2026-01-01T12:00:00Z'),QTimeZone(b'Invalid/Zone'));self.assertEqual(d['time'],'12:00:00');self.assertEqual(d['offset'],'UTC+00:00')
    def test_second_precision_offset_is_not_rounded(self):
        d=clock_data(self.instant('2026-01-01T12:00:00Z'),QTimeZone.fromSecondsAheadOfUtc(1));self.assertEqual(d['offset'],'UTC+00:00:01')
    def test_system_zone_not_inferred_from_language(self):
        d=clock_data();self.assertRegex(d['time'],r'^\d{2}:\d{2}:\d{2}$');self.assertRegex(d['date'],r'^\d{2}\.\d{2}\.\d{4}$');self.assertTrue(d['zone'])
class ClockQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        import desktop
        self.tmp=tempfile.TemporaryDirectory();self.p=patch('desktop.QSettings',return_value=QSettings(self.tmp.name+'/p.ini',QSettings.IniFormat));self.p.start();self.w=desktop.MonitorWindow(demo=True);self.w.show();self.app.processEvents()
    def tearDown(self):
        import i18n
        self.w.close();self.p.stop();self.tmp.cleanup();i18n.set_language('ru')
    def test_removed_thermal_cards_and_centralized_version(self):
        import desktop
        self.assertNotIn('cpu_core_max',self.w.thermal_metrics);self.assertNotIn('gpu_hotspot',self.w.thermal_metrics);self.assertIn('gpu_mem_temp',self.w.thermal_metrics)
        self.assertEqual(self.w.version_label.text(),'/ DESKTOP '+desktop.APP_VERSION);self.assertFalse(desktop.APP_VERSION.startswith('0'));self.assertIn(desktop.APP_VERSION,self.w.windowTitle());self.assertEqual(self.w.diagnostic_payload()['app_version'],desktop.APP_VERSION)
    def test_clock_date_zone_update_and_remain_visible_in_small_window(self):
        import i18n
        d={'time':'01:22:30','date':'18.07.2026','zone':'Europe/Kyiv','offset':'UTC+03:00','abbreviation':'EEST'}
        self.w.resize(520,600);self.w.adapt_layout();self.app.processEvents()
        with patch('desktop.clock_data',return_value=d):
            for lang in ('ru','uk','en'):
                i18n.set_language(lang);self.w.update_clock();i18n.localize_tree(self.w)
                self.assertEqual(self.w.clock.text(),'01:22:30');self.assertEqual(self.w.clock_date.text(),'18.07.2026 · UTC+03:00');self.assertIn('Europe/Kyiv',self.w.clock_zone.toolTip());self.assertTrue(self.w.clock_date.isVisible());self.assertTrue(self.w.clock_zone.isVisible())
        self.assertLessEqual(self.w.clock_widget.mapTo(self.w,self.w.clock_widget.rect().topRight()).x(),self.w.width())
