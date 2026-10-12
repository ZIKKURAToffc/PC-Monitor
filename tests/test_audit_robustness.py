import json,math,os,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from settings_validation import bounded_int,source_mode
from dashboard import normalize_config,apply_config,available_rows,number
from telemetry import Collector,finite
from lhm_bridge import numeric,formatted_value,parse_tree
from fps_diagnostics import inspect_fps

class ValidationAuditTests(unittest.TestCase):
    def test_invalid_numeric_settings_use_defaults(self):
        for value in (None,True,False,'bad',[],{},float('nan'),float('inf'),-1,0,10**500,250.5):
            with self.subTest(value_type=type(value).__name__):self.assertEqual(bounded_int(value,500,250,5000),500)
    def test_allowed_refresh_choices_only(self):
        self.assertEqual(bounded_int('250',500,250,5000,(250,500)),250);self.assertEqual(bounded_int(333,500,250,5000,(250,500)),500)
    def test_invalid_source_mode_defaults(self):
        for value in (None,{},'remote','HTTP'):self.assertEqual(source_mode(value),'aida')
    def test_overflow_and_bool_are_not_sensor_values(self):
        import fps_diagnostics
        for fn in (finite,number,numeric,fps_diagnostics.numeric):
            for value in (True,False,10**500,float('nan'),float('inf')):self.assertIsNone(fn(value))
    def test_zero_remains_valid(self):
        for fn in (finite,number,numeric):self.assertEqual(fn(0),0)
    def test_localized_mixed_separators(self):
        self.assertEqual(formatted_value('1.234,5 MHz','Clock'),1234.5);self.assertEqual(formatted_value('1,234.5 MHz','Clock'),1234.5)
    def test_malformed_lhm_identifier_does_not_crash_tree(self):
        rows,_=parse_tree({'Children':[{'SensorId':'bad','RawValue':0,'Children':42},{'SensorId':'/cpu/0/temperature/0','RawValue':51,'Type':'Temperature'}]});self.assertEqual(len(rows),2);self.assertEqual(rows[1]['Value'],51)
    def test_malformed_children_do_not_hide_sibling_sensors(self):
        rows,_=parse_tree({'Children':[{'Children':{'bad':'child'}},{'SensorId':'/cpu/0/load/0','RawValue':25,'Type':'Load'}]});self.assertEqual(rows[0]['Value'],25)
    def test_bad_nested_dashboard_structure_is_sanitized(self):
        for config in ({'slots':[],'custom':{}},{'slots':{'cpu_temp':None,'gpu_temp':[]},'custom':[None,'bad',42]},None,[]):
            clean=normalize_config(config);self.assertIsInstance(clean,dict);self.assertIsNone(apply_config({'cpu_temp':None},config).get('cpu_temp'))
    def test_config_preserves_valid_explicit_selection(self):
        config={'slots':{'cpu_temp':{'sensor':'missing','label':'My CPU','hidden':False}}};self.assertEqual(normalize_config(config),config);self.assertIsNone(apply_config({'cpu_temp':47},config)['cpu_temp'])
    def test_bad_label_types_and_hidden_false_are_safe(self):
        self.assertEqual(normalize_config({'slots':{'cpu_temp':{'sensor':[],'label':True,'hidden':'false'}}}),{'slots':{'cpu_temp':{'hidden':False}}})
    def test_custom_card_size_is_bounded(self):
        clean=normalize_config({'custom':[{'sensor':'x','label':'a'*1000}]*1000});self.assertEqual(len(clean['custom']),128);self.assertEqual(len(clean['custom'][0]['label']),80)
    def test_invalid_sensor_rows_ignored(self):
        rows=available_rows({'sensor_rows':[None,42,{}, {'id':[]},{'id':'x','name':'test'}]});self.assertIn('x',[r['id'] for r in rows]);self.assertTrue(all(isinstance(r['id'],str) for r in rows))
    def test_numeric_string_vram_is_calculated_safely(self):
        snapshot={'vram_total':'12','vram_used':'2'};self.assertEqual(apply_config(snapshot,{})['vram_free'],10);self.assertEqual(next(r['value'] for r in available_rows(snapshot) if r['id']=='driver/vram_free'),10)
    def test_malformed_fps_metadata_is_safe(self):
        for data in ('bad',42,{'applications':None},{'applications':[None,42]}):self.assertEqual(inspect_fps({'fps':120,'rtss_applications':data}, {'slots':[]})['application']['state'],'unknown')
    def test_malformed_fps_sensor_rows_are_safe(self):
        self.assertEqual(inspect_fps({'fps':120,'sensor_rows':[None,42]})['value'],120)
    def test_fuzz_config_json_shapes(self):
        shapes=[None,True,0,'text',[],{},[{},None],{'cpu_temp':None}]
        for slots in shapes:
            for custom in shapes:
                config=json.loads(json.dumps({'slots':slots,'custom':custom}));result=apply_config({'cpu_temp':47},config);self.assertEqual(result['cpu_temp'],47)

class StopCycles:
    def __init__(self,cycles):self.cycles=cycles;self.waits=0
    def wait(self,seconds):self.waits+=1;return self.waits>self.cycles
    def is_set(self):return self.waits>=self.cycles

class CollectorAuditTests(unittest.TestCase):
    def test_change_source_discards_previous_values(self):
        c=Collector();c.hardware={'gpu_temp':80};c.state={'gpu_temp':80};c.configure('http');self.assertEqual(c.hardware,{});self.assertEqual(c.snapshot(),{})
    def test_identical_configuration_keeps_data(self):
        c=Collector();c.configure('http');c.hardware={'cpu_temp':47};generation=c.generation;c.configure('http');self.assertEqual(c.hardware,{'cpu_temp':47});self.assertEqual(c.generation,generation)
    def test_inflight_old_hardware_is_not_committed(self):
        c=Collector();c.stop=StopCycles(1)
        def old():c.configure('http');return {'cpu_temp':99}
        with patch.object(c,'_hardware_once',side_effect=old):c._hardware_loop()
        self.assertEqual(c.hardware,{})
    def test_invalid_port_and_mapping_do_not_crash(self):
        c=Collector();c.configure('unknown',port='bad',mapping=[]);self.assertEqual(c.source_mode,'aida');self.assertEqual(c.port,8085);self.assertEqual(c.mapping,{})
    def test_start_does_not_duplicate_live_threads(self):
        c=Collector();c.threads=[Mock(is_alive=Mock(return_value=True))]
        with patch('telemetry.threading.Thread') as thread:c.start();thread.assert_not_called()
    def run_system(self,network=None,cycles=2,boot=None,rtss=None):
        c=Collector();c.stop=StopCycles(cycles)
        ram=SimpleNamespace(total=16*1024**3,available=8*1024**3,percent=50)
        with patch('telemetry.psutil.net_io_counters',return_value=network),patch('telemetry.psutil.virtual_memory',return_value=ram),patch('telemetry.psutil.boot_time',side_effect=boot or (lambda:1)),patch('telemetry.psutil.cpu_count',return_value=4),patch('telemetry.psutil.cpu_percent',return_value=5),patch('telemetry.psutil.cpu_freq',return_value=None),patch('telemetry.psutil.disk_partitions',return_value=[]),patch.object(c.rtss_reader,'poll',side_effect=rtss or (lambda:{})):
            c._system_loop()
        return c
    def test_no_network_interfaces_does_not_stop_cpu_ram(self):
        c=self.run_system();self.assertEqual(c.state['ram_usage'],50);self.assertEqual(c.state['cpu_usage'],5);self.assertIsNone(c.state['upload'])
    def test_initial_os_failure_recovers_next_cycle(self):
        c=self.run_system(boot=[OSError('transient'),1]);self.assertEqual(c.state['cpu_usage'],5);self.assertIn('uptime',c.state)
    def test_initial_network_failure_recovers(self):
        counter=SimpleNamespace(bytes_sent=10,bytes_recv=20)
        with patch('telemetry.psutil.net_io_counters',side_effect=[OSError('transient'),counter,counter]):
            c=Collector();c.stop=StopCycles(3)
            with patch('telemetry.psutil.disk_partitions',return_value=[]):c._system_loop()
        self.assertIn('cpu_usage',c.state)
    def test_invalid_polling_float_does_not_raise(self):
        c=Collector();c.set_poll_interval(float('inf'));self.assertEqual(c.poll_ms,500)

class GuiSettingsAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_corrupt_persistent_settings_do_not_prevent_launch(self):
        import desktop
        with tempfile.TemporaryDirectory() as d:
            settings=QSettings(d+'/prefs.ini',QSettings.IniFormat)
            for key,value in [('interval','bad'),('history',0),('threshold',float('inf')),('lhm_port','bad'),('sensor_source_mode','invalid'),('dashboard_config_v1',json.dumps({'slots':[None],'custom':[None,{'sensor':'missing','label':42}]}))]:settings.setValue(key,value)
            with patch('desktop.QSettings',return_value=settings):
                w=desktop.MonitorWindow(demo=True,tray_mode=False)
                try:
                    w.show();self.app.processEvents();self.assertEqual(w.timer.interval(),500);self.assertEqual(w.history_span,60);self.assertEqual(w.threshold,85);self.assertEqual(w.collector.port,8085);self.assertEqual(w.collector.source_mode,'aida');self.assertEqual(w.current['cpu_temp'],47)
                finally:w.close();w.deleteLater()
    def test_malformed_legacy_mapping_is_migrated_safely(self):
        import desktop
        with tempfile.TemporaryDirectory() as d:
            settings=QSettings(d+'/prefs.ini',QSettings.IniFormat);settings.setValue('dashboard_config_v1','{"slots": []}');settings.setValue('aida_sensor_cpu_temp','demo/1')
            with patch('desktop.QSettings',return_value=settings):
                w=desktop.MonitorWindow(demo=True,tray_mode=False)
                try:self.assertEqual(w.current['cpu_temp'],43)
                finally:w.close();w.deleteLater()
    def test_graph_rejects_bool_and_overflow_and_accepts_numeric_string(self):
        from desktop import Graph
        g=Graph('test','cpu')
        try:
            g.push(1,'32.5');self.assertEqual(g.latest,32.5);g.push(2,True);self.assertIsNone(g.latest);g.push(3,10**500);self.assertIsNone(g.latest)
        finally:g.deleteLater()

class PublishIntegrityAuditTests(unittest.TestCase):
    def test_corrupt_same_size_copy_keeps_previous_exe(self):
        import build_windows as b
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source.exe';source.write_bytes(b'MZ'+b'x'*200);destination=root/'installed';destination.mkdir();old=destination/'PC-Monitor.exe';old.write_bytes(b'MZ'+b'o'*200)
            def corrupt(src,dst):Path(dst).write_bytes(b'MZ'+b'z'*200)
            with patch('build_windows.shutil.copyfile',side_effect=corrupt):
                with self.assertRaises(OSError):b.publish_exe(source,destination)
            self.assertEqual(old.read_bytes(),b'MZ'+b'o'*200);self.assertEqual(list(destination.iterdir()),[old])

class ErrorLogAuditTests(unittest.TestCase):
    def setUp(self):
        import runtime_errors as r
        self.r=r;self.handlers=list(r.LOGGER.handlers);self.path=r.LOG_PATH;self.propagate=r.LOGGER.propagate
        r.LOGGER.handlers=[]
    def tearDown(self):
        for h in self.r.LOGGER.handlers:h.close()
        self.r.LOGGER.handlers=self.handlers;self.r.LOG_PATH=self.path;self.r.LOGGER.propagate=self.propagate
    def test_traceback_saved_locally_without_locals(self):
        import sys
        with tempfile.TemporaryDirectory() as d:
            path=self.r.setup_log(d)
            try:raise ValueError('test failure')
            except ValueError:self.r.LOGGER.error('Test',exc_info=sys.exc_info())
            text=path.read_text();self.assertIn('ValueError: test failure',text);self.assertNotIn('password=',text)
    def test_no_write_permission_does_not_raise(self):
        with patch('runtime_errors.Path.mkdir',side_effect=PermissionError('denied')):self.assertIsNone(self.r.setup_log('/invalid'))
    def test_log_rotation_is_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            self.r.setup_log(d)
            for _ in range(40):self.r.LOGGER.error('x'*30000)
            paths=list(Path(d).iterdir());self.assertLessEqual(len(paths),3);self.assertLess(sum(p.stat().st_size for p in paths),3*256*1024)
    def test_background_exceptions_do_not_open_gui_dialog(self):
        import sys
        with tempfile.TemporaryDirectory() as d,patch('PySide6.QtWidgets.QMessageBox.warning') as dialog:
            self.r.setup_log(d)
            def fail():
                try:raise OSError('worker failure')
                except OSError:self.r.report_exception(*sys.exc_info())
            t=threading.Thread(target=fail);t.start();t.join();dialog.assert_not_called();self.assertIn('worker failure',self.r.LOG_PATH.read_text())

class DialogLifetimeAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def check_dialog(self,method):
        import desktop
        from PySide6.QtWidgets import QDialog
        from PySide6.QtCore import QTimer,QEvent,QCoreApplication
        with tempfile.TemporaryDirectory() as d:
            settings=QSettings(d+'/prefs.ini',QSettings.IniFormat)
            with patch('desktop.QSettings',return_value=settings):
                w=desktop.MonitorWindow(demo=True,tray_mode=False);w.timer.stop();w.clock_timer.stop();w.show()
                try:
                    for _ in range(4):
                        QTimer.singleShot(1,lambda:QApplication.activeModalWidget().reject());getattr(w,method)();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);self.app.processEvents();self.assertEqual(w.findChildren(QDialog),[])
                finally:w.close();w.deleteLater()
    def test_settings_dialogs_are_released(self):self.check_dialog('show_settings')
    def test_style_dialogs_are_released(self):self.check_dialog('choose_theme')
    def test_developer_dialogs_are_released(self):self.check_dialog('show_developer')
    def test_dashboard_dialogs_are_released(self):self.check_dialog('configure_dashboard')
    def test_connection_dialogs_are_released(self):self.check_dialog('sensor_help')

class CliDiagnosticAuditTests(unittest.TestCase):
    def test_version_shared_with_native_application(self):
        import diagnose,desktop
        self.assertEqual(diagnose.APP_VERSION,desktop.APP_VERSION)
    def test_cli_export_reports_current_version_and_closes_collector(self):
        import diagnose
        with tempfile.TemporaryDirectory() as d,patch('diagnose.Collector') as collector,patch('diagnose.Path.cwd',return_value=Path(d)):
            collector.return_value._hardware_once.return_value={'diagnostics':{},'sensor_rows':[]};self.assertEqual(diagnose.main(),0);report=json.loads((Path(d)/'lhm-diagnostics.json').read_text());self.assertEqual(report['app_version'],diagnose.APP_VERSION);collector.return_value.close.assert_called_once()
    def test_cli_write_failure_is_reported_without_uncaught_error(self):
        import diagnose
        with patch('diagnose.Collector') as collector,patch('diagnose.Path.write_text',side_effect=PermissionError('denied')):
            collector.return_value._hardware_once.return_value={};self.assertEqual(diagnose.main(),1);collector.return_value.close.assert_called_once()

class SourceRaceAuditTests(unittest.TestCase):
    def test_old_backend_report_cannot_override_new_configuration(self):
        c=Collector();generation=c.generation;c.configure('http');c._set_backend_report({'connected':True},'AIDA64 Shared Memory',generation);self.assertEqual(c.diagnostics,{});self.assertEqual(c.transport,'Недоступно')
    def test_current_backend_report_is_committed(self):
        c=Collector();c._set_backend_report({'connected':True},'HTTP',c.generation);self.assertEqual(c.diagnostics,{'connected':True});self.assertEqual(c.transport,'HTTP')
    def test_system_result_discarded_if_source_changes_during_poll(self):
        c=Collector();c.stop=StopCycles(1);ram=SimpleNamespace(total=16*1024**3,available=8*1024**3,percent=50)
        def switch():c.configure('http');return {}
        with patch('telemetry.psutil.net_io_counters',return_value=None),patch('telemetry.psutil.virtual_memory',return_value=ram),patch('telemetry.psutil.boot_time',return_value=1),patch('telemetry.psutil.cpu_count',return_value=4),patch('telemetry.psutil.cpu_percent',return_value=5),patch('telemetry.psutil.cpu_freq',return_value=None),patch('telemetry.psutil.disk_partitions',return_value=[]),patch.object(c.rtss_reader,'poll',side_effect=switch):c._system_loop()
        self.assertEqual(c.state,{})
    def test_boolean_poll_interval_does_not_enable_fast_poll(self):
        c=Collector();c.set_poll_interval(True);self.assertEqual(c.poll_ms,500)

class CleanupBoundaryAuditTests(unittest.TestCase):
    def test_source_root_junction_rejected_before_resolving(self):
        import source_cleanup as cleanup
        with tempfile.TemporaryDirectory() as d:
            source=Path(d);real=source.lstat();fake=SimpleNamespace(st_mode=real.st_mode,st_file_attributes=0x400)
            with patch('source_cleanup.Path.lstat',return_value=fake):
                with self.assertRaisesRegex(ValueError,'link or junction'):cleanup.validate_source_cleanup(source,source.parent/'PC-Monitor.exe')

class FinalInputAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_wrong_outer_sensor_rows_type_is_safe(self):
        for value in (42,True,{},'bad',None):self.assertTrue(available_rows({'sensor_rows':value}))
    def test_dynamic_labels_never_interpret_html(self):
        from desktop import Metric,text
        from PySide6.QtCore import Qt
        card=Metric('<b>Sensor</b>','W');label=text('<img src="file:///private">')
        try:self.assertEqual(card.label.textFormat(),Qt.PlainText);self.assertEqual(label.textFormat(),Qt.PlainText)
        finally:card.deleteLater();label.deleteLater()

class SystemTimezoneAuditTests(unittest.TestCase):
    def test_empty_system_timezone_id_uses_native_local_offset(self):
        from clock_display import clock_data
        from PySide6.QtCore import QTimeZone,QDateTime,Qt,QByteArray
        instant=QDateTime.fromString('2026-01-01T12:00:00Z',Qt.ISODate);native=instant.toLocalTime();expected=clock_data(instant,QTimeZone.fromSecondsAheadOfUtc(native.offsetFromUtc()))
        with patch('clock_display.QTimeZone.systemTimeZoneId',return_value=QByteArray()),patch('clock_display.QTimeZone.systemTimeZone',return_value=QTimeZone.fromSecondsAheadOfUtc(1)) as old_api:
            actual=clock_data(instant);self.assertEqual(actual['offset'],expected['offset']);self.assertEqual(actual['time'],expected['time']);old_api.assert_not_called()
    def test_valid_system_timezone_id_is_used(self):
        from clock_display import clock_data
        from PySide6.QtCore import QTimeZone,QDateTime,Qt,QByteArray
        zone=QTimeZone(b'Europe/Berlin')
        if not zone.isValid():self.skipTest('Timezone database unavailable')
        instant=QDateTime.fromString('2026-07-01T12:00:00Z',Qt.ISODate)
        with patch('clock_display.QTimeZone.systemTimeZoneId',return_value=QByteArray(b'Europe/Berlin')):
            self.assertEqual(clock_data(instant)['zone'],'Europe/Berlin');self.assertEqual(clock_data(instant)['offset'],'UTC+02:00')

class CustomCardLimitAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_add_button_respects_limit_and_reenables_after_delete(self):
        import desktop
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QPushButton
        errors=[]
        with tempfile.TemporaryDirectory() as d,patch('desktop.MAX_CUSTOM_CARDS',2):
            settings=QSettings(d+'/prefs.ini',QSettings.IniFormat)
            with patch('desktop.QSettings',return_value=settings):
                w=desktop.MonitorWindow(demo=True,tray_mode=False);w.show()
                def inspect():
                    dialog=QApplication.activeModalWidget()
                    try:
                        add=dialog.findChild(QPushButton,'dashboardAddCustom');add.click();add.click();self.assertFalse(add.isEnabled());remove=next(b for b in dialog.findChildren(QPushButton) if b.text()=='Удалить карточку');remove.click();self.assertTrue(add.isEnabled())
                    except Exception as e:errors.append(e)
                    finally:dialog.reject()
                try:QTimer.singleShot(5,inspect);w.configure_dashboard()
                finally:w.close();w.deleteLater()
        if errors:raise errors[0]
