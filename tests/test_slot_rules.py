import unittest,tempfile
from unittest.mock import patch
from dashboard import matches_slot,apply_config,available_rows,SLOTS

def row(sid,name,typ,unit,value=30,**more):return dict(id=sid,name=name,type=typ,unit=unit,value=value,source='Test',**more)
class SemanticSlotTests(unittest.TestCase):
    def test_all_23_roles_have_valid_examples(self):
        rows={
         'fps':row('/aida/application/0/fps/SRTSSFPS','RTSS FPS','FPS','FPS',0),
         'cpu_temp':row('/amdcpu/0/temperature/0','CPU Package','Temperature','°C'),
         'cpu_core_max':row('/intelcpu/0/temperature/1','CPU Core #1','Temperature','°C'),
         'cpu_clock':row('/amdcpu/0/clock/0','Cores (Average)','Clock','MHz'),
         'cpu_power':row('/amdcpu/0/power/0','CPU Package','Power','W'),
         'cpu_usage':row('/amdcpu/0/load/0','CPU Total','Load','%'),
         'cpu_rpm':row('/lpc/0/fan/0','CPU OPT Fan','Fan','RPM'),
         'gpu_temp':row('/gpu-nvidia/0/temperature/0','GPU Core','Temperature','°C'),
         'gpu_hotspot':row('/gpu-nvidia/0/temperature/1','GPU Hot Spot','Temperature','°C'),
         'gpu_mem_temp':row('/gpu-nvidia/0/temperature/2','GPU Memory Junction','Temperature','°C'),
         'gpu_clock':row('/gpu-nvidia/0/clock/0','GPU Core','Clock','MHz'),
         'gpu_usage':row('/gpu-nvidia/0/load/0','GPU Core','Load','%'),
         'gpu_power':row('/gpu-nvidia/0/power/0','GPU Package','Power','W'),
         'gpu_rpm':row('/gpu-nvidia/0/fan/0','GPU Fan 1','Fan','RPM'),
         'sys_temp':row('/lpc/0/temperature/0','Motherboard','Temperature','°C'),
         'disk_temp':row('/nvme/0/temperature/0','Composite Temperature','Temperature','°C')}
        independent={r['id'].split('/')[-1]:r for r in available_rows({})};rows.update(independent)
        for key,_,_ in SLOTS:
            with self.subTest(slot=key):self.assertTrue(matches_slot(rows[key],key))
    def test_same_units_do_not_mean_same_role(self):
        cpu=row('/amdcpu/0/temperature/0','CPU Package','Temperature','°C');gpu=row('/gpu/0/temperature/0','GPU Core','Temperature','°C');hot=row('/gpu/0/temperature/1','GPU Hotspot','Temperature','°C');mem=row('/gpu/0/temperature/2','GPU Memory','Temperature','°C');board=row('/lpc/0/temperature/0','Motherboard','Temperature','°C');ssd=row('/storage/0/temperature/0','Composite','Temperature','°C')
        cases={'cpu_temp':[gpu,hot,mem,board,ssd], 'gpu_temp':[cpu,hot,mem,board,ssd], 'gpu_hotspot':[cpu,gpu,mem,board,ssd], 'gpu_mem_temp':[cpu,gpu,hot,board,ssd], 'sys_temp':[cpu,gpu,hot,mem,ssd], 'disk_temp':[cpu,gpu,hot,mem,board]}
        for key,wrong in cases.items():
            for r in wrong:
                with self.subTest(slot=key,sensor=r['name']):self.assertFalse(matches_slot(r,key))
    def test_clock_load_and_fan_subtypes_rejected(self):
        for name in ['Bus Speed','Infinity Fabric','Memory','SoC','L3 Cache']:self.assertFalse(matches_slot(row('/amdcpu/0/clock/0',name,'Clock','MHz'),'cpu_clock'))
        for name in ['GPU Memory','GPU Shader']:self.assertFalse(matches_slot(row('/gpu/0/clock/0',name,'Clock','MHz'),'gpu_clock'))
        for name in ['GPU Memory Controller','GPU Video Engine','GPU Bus']:self.assertFalse(matches_slot(row('/gpu/0/load/0',name,'Load','%'),'gpu_usage'))
        for name in ['Fan #1','Chassis Fan','System Fan']:self.assertFalse(matches_slot(row('/lpc/0/fan/0',name,'Fan','RPM'),'cpu_rpm'))
        self.assertFalse(matches_slot(row('/amdcpu/0/temperature/0','CPU Package','Temperature','°C'),'cpu_core_max'))
        for name in ['Temperature #3','VRM','PCH','Southbridge']:self.assertFalse(matches_slot(row('/lpc/0/temperature/0',name,'Temperature','°C'),'sys_temp'))
    def test_memory_and_network_roles_separate(self):
        virtual=available_rows({});lookup={r['id']:r for r in virtual}
        for key in ['ram_used','ram_free','vram_used','vram_free','cpu_usage','ram_usage','upload','download']:
            sid=('driver/' if key.startswith('vram') else 'system/')+key
            for other,_,unit in SLOTS:
                if other!=key:self.assertFalse(matches_slot(lookup[sid],other))
        self.assertTrue(matches_slot(row('/ram/data/0','Used Memory','Data','GiB'),'ram_used'));self.assertFalse(matches_slot(row('/gpu/data/0','GPU Memory Used','Data','GiB'),'ram_used'))
        self.assertTrue(matches_slot(row('/nic/0/throughput/0','Data Uploaded','Throughput','KiB/s'),'upload'));self.assertFalse(matches_slot(row('/nic/0/throughput/0','Data Downloaded','Throughput','KiB/s'),'upload'))
    def test_invalid_old_mapping_is_not_auto_replaced(self):
        r=row('/storage/0/temperature/0','Composite','Temperature','°C',38);s={'cpu_temp':99,'sensor_rows':[r]};cfg={'slots':{'cpu_temp':{'sensor':r['id'],'label':'CPU'}}};d=apply_config(s,cfg)
        self.assertIsNone(d['cpu_temp']);self.assertEqual(d['mapping_status']['cpu_temp'],'incompatible');self.assertEqual(s['cpu_temp'],99);self.assertEqual(cfg['slots']['cpu_temp']['sensor'],r['id'])
    def test_canonical_names_not_custom_display_names(self):
        r=row('/gpu/0/temperature/1','Мой датчик','Temperature','°C',canonical_name='GPU Hotspot');self.assertTrue(matches_slot(r,'gpu_hotspot'));self.assertFalse(matches_slot(r,'gpu_temp'))
    def test_thresholds_and_zero_not_confused(self):
        self.assertFalse(matches_slot(row('/storage/0/temperature/0','Critical Temperature','Temperature','°C'),'disk_temp'))
        self.assertFalse(matches_slot(row('/cpu/0/temperature/0','CPU Package','Temperature','°C',is_limit=True),'cpu_temp'))
        r=row('/aida/application/0/fps/SRTSSFPS','RTSS FPS','FPS','FPS',0);self.assertTrue(matches_slot(r,'fps'));self.assertEqual(apply_config({'sensor_rows':[r]},{'slots':{'fps':{'sensor':r['id']}}})['fps'],0)
    def test_unknown_ambiguous_sensor_fails_closed(self):
        r=row('/unknown/0/temperature/1','Temperature #2','Temperature','°C',device='Unknown')
        for key,_,_ in SLOTS:self.assertFalse(matches_slot(r,key))

class SemanticSelectionQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        import desktop
        from PySide6.QtCore import QSettings
        self.tmp=tempfile.TemporaryDirectory();self.prefs=QSettings(self.tmp.name+'/p.ini',QSettings.IniFormat);self.patch=patch('desktop.QSettings',return_value=self.prefs);self.patch.start();self.w=desktop.MonitorWindow(demo=True);self.w.show()
    def tearDown(self):self.w.close();self.patch.stop();self.tmp.cleanup()
    def run_dialog(self,open_dialog,check):
        from PySide6.QtCore import QTimer
        errors=[]
        def inspect():
            d=self.app.activeModalWidget()
            try:check(d)
            except Exception as e:errors.append(e)
            finally:d.reject()
        QTimer.singleShot(20,inspect);open_dialog()
        if errors:raise errors[0]
    def test_both_dialogs_filter_every_standard_card(self):
        from PySide6.QtWidgets import QComboBox
        lookup={r['id']:r for r in available_rows(self.w.base_snapshot)}
        for method,prefix in [(self.w.configure_dashboard,'dashboardSensor_'),(self.w.sensor_help,'panelSensor_')]:
            def inspect(d):
                for key,_,_ in SLOTS:
                    box=d.findChild(QComboBox,prefix+key);self.assertIsNotNone(box)
                    for i in range(1,box.count()):self.assertTrue(matches_slot(lookup[box.itemData(i)],key),(key,box.itemText(i)))
                cpu=d.findChild(QComboBox,prefix+'cpu_temp');self.assertGreaterEqual(cpu.findData('demo/0'),0)
                for wrong in ['demo/5','demo/8','demo/9']:self.assertLess(cpu.findData(wrong),0)
            self.run_dialog(method,inspect)
    def test_invalid_legacy_choice_disabled_and_kept_as_error(self):
        from PySide6.QtWidgets import QComboBox
        self.w.dashboard_config={'slots':{'cpu_temp':{'sensor':'demo/9'}}};self.w.refresh();self.assertIsNone(self.w.current['cpu_temp'])
        for method,prefix in [(self.w.configure_dashboard,'dashboardSensor_'),(self.w.sensor_help,'panelSensor_')]:
            def inspect(d):
                box=d.findChild(QComboBox,prefix+'cpu_temp');self.assertEqual(box.currentData(),'demo/9');self.assertFalse(box.model().item(box.currentIndex()).isEnabled());self.assertIn('Несовместимое',box.currentText())
            self.run_dialog(method,inspect)
    def test_custom_cards_remain_numeric_unit_based(self):
        from PySide6.QtWidgets import QComboBox
        self.w.dashboard_config={'custom':[{'sensor':'demo/fan/0','label':'Корпус','unit':'RPM'}]};self.w.rebuild_custom_cards()
        def inspect(d):
            box=d.findChild(QComboBox,'customSensor_0');self.assertGreaterEqual(box.findData('demo/fan/0'),0)
        self.run_dialog(self.w.sensor_help,inspect)
    def test_no_cyan_border_in_focused_and_pressed_gear_render(self):
        from PySide6.QtCore import Qt
        import desktop
        self.assertIsInstance(self.w.gear_button,desktop.GearButton)
        for pressed in [False,True]:
            self.w.gear_button.setFocus(Qt.TabFocusReason);self.w.gear_button.setDown(pressed);self.app.processEvents();image=self.w.gear_button.grab().toImage()
            for x,y in [(1,image.height()//2),(image.width()-2,image.height()//2),(image.width()//2,1),(image.width()//2,image.height()-2)]:self.assertNotEqual(image.pixelColor(x,y).name(),desktop.CYAN)
        self.w.gear_button.setDown(False)
    def test_gear_has_no_backing_in_any_state(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt,QEvent
        for pressed in (False,True):
            self.w.gear_button.setFocus(Qt.TabFocusReason);self.w.gear_button.setDown(pressed)
            QApplication.sendEvent(self.w.gear_button,QEvent(QEvent.Enter));self.app.processEvents()
            image=self.w.gear_button.grab().toImage()
            for x,y in [(2,2),(4,22),(22,4),(40,22)]:
                self.assertNotIn(image.pixelColor(x,y).name(),['#0b1510','#143328','#1b503c','#18ffe0'])
        self.w.gear_button.setDown(False)

class LegacySemanticTests(unittest.TestCase):
    def test_backend_manual_cpu_temperature_cannot_read_ssd(self):
        from telemetry import Collector
        c=Collector();c.mapping={'cpu_temp':'/nvme/0/temperature/0'}
        raw={'Identifier':'/nvme/0/temperature/0','Name':'Composite','SensorType':'Temperature','Value':38}
        self.assertIsNone(c.choose_sensor([raw],'cpu_temp','Temperature','cpu',['CPU Package'])[0])
    def test_auto_cpu_fan_excludes_ambiguous_chassis_fan(self):
        from telemetry import Collector
        c=Collector();raw=[{'Identifier':'/lpc/0/fan/0','Name':'Fan #1','SensorType':'Fan','Value':1500}, {'Identifier':'/lpc/0/fan/1','Name':'CPU OPT Fan','SensorType':'Fan','Value':1700}]
        self.assertEqual(c.choose_sensor(raw,'cpu_rpm','Fan','',['CPU Fan','CPU'])[0],1700)
    def test_startup_migrates_invalid_legacy_without_auto_substitution(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QSettings
        import desktop
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            prefs=QSettings(folder+'/p.ini',QSettings.IniFormat);prefs.setValue('sensor_source_mode','aida');prefs.setValue('aida_sensor_cpu_temp','demo/9')
            with patch('desktop.QSettings',return_value=prefs):
                w=desktop.MonitorWindow(demo=True)
                try:self.assertIsNone(w.current['cpu_temp']);self.assertEqual(w.current['mapping_status']['cpu_temp'],'incompatible');self.assertEqual(w.collector.mapping,{});self.assertEqual(w.dashboard_config['slots']['cpu_temp']['sensor'],'demo/9');self.assertEqual(prefs.value('aida_sensor_cpu_temp'),'')
                finally:w.close()
