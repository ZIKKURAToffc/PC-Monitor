import unittest,time,json,tempfile
from unittest.mock import patch
from fps_diagnostics import inspect_fps
from dashboard import apply_config
class FpsPipelineTests(unittest.TestCase):
    def snapshot(self,value):
        return {'fps':value,'fps_source':'AIDA64 / RTSS','updated':100,'sensor_rows':[{'id':'/aida/application/0/fps/SRTSSFPS','type':'FPS','unit':'FPS','name':'RTSS FPS','value':value,'text_value':str(value),'source':'AIDA64 Shared Memory'}]}
    def test_export_zero_preserved_game_detection_unknown(self):
        d=inspect_fps(self.snapshot(0),now=103);self.assertEqual(d['value'],0);self.assertEqual(d['state'],'zero');self.assertEqual(d['game_detection'],'unknown');self.assertEqual(d['aida_export']['raw_text'],'0')
    def test_positive_is_published_not_game_identity(self):
        d=inspect_fps(self.snapshot(144),now=103);self.assertEqual(d['state'],'available');self.assertEqual(d['value'],144);self.assertEqual(d['game_detection'],'unknown')
    def test_absent_fps_not_fabricated(self):
        d=inspect_fps({'gpu_usage':99});self.assertEqual(d['state'],'missing');self.assertIsNone(d['value']);self.assertFalse(d['aida_export']['present'])
    def test_invalid_nan_and_negative(self):
        for value in [float('nan'),float('inf'),-1]:
            d=inspect_fps(self.snapshot(value),now=103);self.assertIsNone(d['value']);json.dumps(d,allow_nan=False)
        self.assertEqual(inspect_fps(self.snapshot(-1),now=103)['state'],'invalid')
    def test_old_data_not_shown_as_live_fps(self):
        d=inspect_fps(self.snapshot(144),now=121);self.assertEqual(d['state'],'stale');self.assertIsNone(d['value'])
    def test_explicit_source_is_reported_and_zero_aida_retained(self):
        s=self.snapshot(0);s['sensor_rows'].append({'id':'custom/fps','type':'FPS','unit':'FPS','name':'FPS selected','source':'Other provider','value':90});cfg={'slots':{'fps':{'sensor':'custom/fps'}}};d=inspect_fps(apply_config(s,cfg),cfg,now=103)
        self.assertEqual(d['value'],90);self.assertEqual(d['source'],'Other provider');self.assertEqual(d['aida_export']['value'],0)
    def test_wrong_units_or_missing_explicit_source_no_fallback(self):
        s=self.snapshot(144);s['sensor_rows'].append({'id':'wrong','unit':'%','value':99,'name':'GPU usage','source':'Test'})
        for sid in ['wrong','gone']:
            cfg={'slots':{'fps':{'sensor':sid}}};d=inspect_fps(apply_config(s,cfg),cfg,now=103);self.assertIsNone(d['value']);self.assertEqual(d['state'],'missing')
    def test_na_export_raw_text_is_diagnostic(self):
        s=self.snapshot(None);s['sensor_rows'][0]['text_value']='N/A';d=inspect_fps(s,now=103);self.assertEqual(d['aida_export']['raw_text'],'N/A');self.assertEqual(d['state'],'missing')

class StripAndFpsQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        import desktop
        from PySide6.QtCore import QSettings
        self.tmp=tempfile.TemporaryDirectory();self.settings=QSettings(self.tmp.name+'/p.ini',QSettings.IniFormat);self.p=patch('desktop.QSettings',return_value=self.settings);self.p.start();self.w=desktop.MonitorWindow(demo=True);self.w.show()
    def tearDown(self):self.w.close();self.p.stop();self.tmp.cleanup()
    def test_same_bold_font_main_strips(self):
        for compact in [True,False]:
            self.w.compact_mode=compact;self.w.adapt_layout();self.app.processEvents()
            for label in [self.w.cpu.title_label,self.w.gpu.title_label,self.w.syshead,self.w.cpu.temp,self.w.gpu.temp,self.w.board_temp]:
                self.assertIn('font-family:Arial',label.styleSheet());self.assertIn('font-weight:900',label.styleSheet());self.assertIn('font-size:'+('18' if compact else '24')+'px',label.styleSheet())
            for label in [self.w.cpu.detail,self.w.gpu.detail,self.w.board_caption]:self.assertIn('font-weight:900',label.styleSheet())
    def test_zero_warning_and_export_diagnostics(self):
        import desktop
        d=desktop.demo_snapshot();d.update(fps=0,fps_source='AIDA64 / RTSS');d['sensor_rows'].append({'id':'/aida/application/0/fps/SRTSSFPS','name':'RTSS FPS','device':'AIDA64','type':'FPS','unit':'FPS','value':0,'text_value':'0','source':'AIDA64 Shared Memory'})
        with patch('desktop.demo_snapshot',return_value=d):
            self.w.refresh();self.assertEqual(self.w.fps_metric.value.text(),'0');self.assertIn('Источник игры не определён',self.w.fps_status.text());self.assertEqual(self.w.diagnostic_payload()['diagnostics']['fps']['aida_export']['value'],0)
    def test_custom_fps_diagnostic_not_old_source(self):
        import desktop
        d=desktop.demo_snapshot();d['sensor_rows'].append({'id':'test/fps','name':'FPS','device':'Test','type':'FPS','unit':'FPS','value':50,'source':'Test provider'});self.w.dashboard_config={'slots':{'fps':{'sensor':'test/fps'}}}
        with patch('desktop.demo_snapshot',return_value=d):self.w.refresh();self.assertEqual(self.w.current_fps_diagnostic['source'],'Test provider');self.assertEqual(self.w.fps_metric.value.text(),'50')

    def test_zero_status_localized_without_claiming_detection(self):
        import i18n
        from fps_diagnostics import STATUS
        try:
            for code,expected in [('ru','Источник игры не определён'),('uk','Джерело гри не визначено'),('en','Game source not identified')]:
                i18n.set_language(code);self.assertTrue(i18n.t(STATUS['zero']).startswith(expected))
        finally:i18n.set_language('ru')
