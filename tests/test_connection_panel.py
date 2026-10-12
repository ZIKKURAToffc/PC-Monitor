import json,tempfile,unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QComboBox,QPushButton,QTabWidget
from PySide6.QtCore import QSettings,QTimer
import desktop,i18n
from dashboard import SLOTS
class ConnectionPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.settings=QSettings(self.tmp.name+'/prefs.ini',QSettings.IniFormat);self.p=patch('desktop.QSettings',return_value=self.settings);self.p.start();self.w=desktop.MonitorWindow(demo=True);self.w.show()
    def tearDown(self):self.w.close();self.p.stop();self.tmp.cleanup();i18n.set_language('ru')
    def dialog(self,callback):
        errors=[]
        def run():
            d=QApplication.activeModalWidget()
            try:callback(d)
            except Exception as e:errors.append(e)
            finally:d.reject()
        QTimer.singleShot(30,run);self.w.sensor_help()
        if errors:raise errors[0]
    def box(self,d,key):return d.findChild(QComboBox,'panelSensor_'+key)
    def apply(self,d):d.findChild(QPushButton,'applySensors').click()
    def test_all_23_slots_present(self):
        def check(d):
            self.assertEqual(len([b for b in d.findChildren(QComboBox) if b.objectName().startswith('panelSensor_')]),len(SLOTS));self.assertEqual(d.findChild(QTabWidget,'connectionPages').currentIndex(),1)
            for key,_,_ in SLOTS:self.assertIsNotNone(self.box(d,key))
        self.dialog(check)
    def test_memory_temperature_assignment_applies(self):
        original=desktop.demo_snapshot()
        original['sensor_rows'].append(dict(id='demo/memory',name='GPU Memory',device='GPU',type='Temperature',unit='°C',value=67,source='DEMO'))
        with patch('desktop.demo_snapshot',return_value=original):
            self.w.refresh()
            def check(d):b=self.box(d,'gpu_mem_temp');b.setCurrentIndex(b.findData('demo/memory'));self.apply(d)
            self.dialog(check);self.assertEqual(self.w.current['gpu_mem_temp'],67);self.assertIn('67',self.w.gpu.detail.text());self.assertEqual(self.w.dashboard_config['slots']['gpu_mem_temp']['sensor'],'demo/memory')
    def test_preserves_label_hidden_custom_and_shared_mapping(self):
        self.w.dashboard_config={'slots':{'gpu_temp':{'sensor':'demo/5','label':'Мой GPU','hidden':True}},'custom':[{'sensor':'demo/9','label':'SSD','unit':'°C'}]};self.w.rebuild_custom_cards();self.w.refresh()
        def check(d):
            b=self.box(d,'gpu_temp');self.assertEqual(b.currentData(),'demo/5');self.assertLess(b.findData('demo/9'),0);b.setCurrentIndex(b.findData('demo/5'))
            custom=d.findChild(QComboBox,'customSensor_0');custom.setCurrentIndex(custom.findData('demo/0'));self.apply(d)
        self.dialog(check);self.assertEqual(self.w.current['gpu_temp'],36);self.assertEqual(self.w.dashboard_config['slots']['gpu_temp']['label'],'Мой GPU');self.assertTrue(self.w.dashboard_config['slots']['gpu_temp']['hidden']);self.assertEqual(self.w.dashboard_config['custom'][0]['sensor'],'demo/0');self.assertEqual(self.w.custom_widgets[0][1].label.text(),'SSD')
    def test_compatible_units_and_no_temperature_limits(self):
        data=desktop.demo_snapshot();data['sensor_rows'].append(dict(id='demo/limit',name='Critical Temperature',device='SSD',type='Temperature',unit='°C',value=85,source='DEMO',is_limit=True))
        with patch('desktop.demo_snapshot',return_value=data):
            self.w.refresh()
            def check(d):
                self.assertLess(self.box(d,'cpu_temp').findData('demo/limit'),0);self.assertLess(self.box(d,'cpu_rpm').findData('demo/9'),0);self.assertLess(self.box(d,'cpu_rpm').findData('demo/fan/0'),0);self.assertGreaterEqual(self.box(d,'ram_used').findData('system/ram_used'),0)
            self.dialog(check)
    def test_missing_selected_is_not_replaced_and_refresh_preserves_edits(self):
        self.w.dashboard_config={'slots':{'gpu_mem_temp':{'sensor':'gone'}}};self.w.refresh()
        def check(d):
            b=self.box(d,'gpu_mem_temp');self.assertEqual(b.currentData(),'gone');self.assertIn('недоступен',b.currentText());self.apply(d);self.assertIsNone(self.w.current['gpu_mem_temp'])
            b=self.box(d,'cpu_temp');b.setCurrentIndex(b.findData('demo/1'));d.findChild(QPushButton,'refreshSensors').click();self.assertEqual(b.currentData(),'demo/1')
        self.dialog(check)
    def test_cancel_without_apply_does_not_save(self):
        def check(d):b=self.box(d,'cpu_temp');b.setCurrentIndex(b.findData('demo/1'))
        before=json.dumps(self.w.dashboard_config);self.dialog(check);self.assertEqual(json.dumps(self.w.dashboard_config),before)
    def test_legacy_five_migrate_and_auto_clears_override(self):
        self.settings.setValue('aida_sensor_cpu_temp','demo/1');self.w.collector.mapping={'cpu_temp':'demo/1'}
        def check(d):
            self.assertEqual(self.box(d,'cpu_temp').currentData(),'demo/1');self.apply(d);self.assertEqual(self.w.dashboard_config['slots']['cpu_temp']['sensor'],'demo/1');self.assertEqual(self.w.collector.mapping,{})
        self.dialog(check);self.assertEqual(self.w.current['cpu_temp'],43)
        def auto(d):self.box(d,'cpu_temp').setCurrentIndex(0);self.apply(d)
        self.dialog(auto);self.assertEqual(self.w.current['cpu_temp'],47);self.assertEqual(self.settings.value('aida_sensor_cpu_temp'),'')
    def test_language_and_saved_restore(self):
        self.w.language='uk';i18n.set_language('uk');self.w.refresh()
        def check(d):
            self.assertEqual(d.findChild(QTabWidget,'connectionPages').tabText(1),'Датчики панелі');b=self.box(d,'cpu_usage');b.setCurrentIndex(b.findData('system/cpu_usage'));self.apply(d)
        self.dialog(check);stored=json.loads(self.settings.value('dashboard_config_v1'));self.assertEqual(stored['slots']['cpu_usage']['sensor'],'system/cpu_usage')
        other=desktop.MonitorWindow(demo=True)
        try:self.assertEqual(other.dashboard_config['slots']['cpu_usage']['sensor'],'system/cpu_usage')
        finally:other.close()

    def test_live_values_update_without_apply_preserving_edit(self):
        import copy
        data=desktop.demo_snapshot()
        data['sensor_rows']=[dict(id='/aida/cpu/temperature/0',name='CPU Package',device='CPU',group='CPU',type='Temperature',unit='°C',value=50,source='AIDA64')]
        self.w.demo=False;self.w.paused=True
        before=copy.deepcopy(self.w.dashboard_config)
        with patch.object(self.w.collector,'snapshot',side_effect=lambda:copy.deepcopy(data)):
            def check(d):
                d.findChild(QComboBox,'sourceMode').setCurrentIndex(0)
                box=self.box(d,'cpu_temp');box.setCurrentIndex(box.findData('/aida/cpu/temperature/0'))
                timer=d.findChild(QTimer,'panelLiveRefreshTimer');self.assertIsNotNone(timer);self.assertTrue(timer.isActive());self.assertEqual(timer.interval(),250)
                data['sensor_rows'][0]['value']=61;timer.timeout.emit()
                self.assertEqual(box.currentData(),'/aida/cpu/temperature/0');self.assertIn('61,0',box.currentText());self.assertEqual(self.w.dashboard_config,before)
                box.showPopup();self.app.processEvents();self.assertTrue(box.view().isVisible())
                data['sensor_rows'][0]['value']=62;timer.timeout.emit();self.assertTrue(box.view().isVisible());self.assertIn('62,0',box.itemText(box.findData('/aida/cpu/temperature/0')));box.hidePopup()
                data['sensor_rows']=[];timer.timeout.emit();self.assertEqual(box.currentData(),'/aida/cpu/temperature/0');self.assertIn('недоступен',box.currentText())
                self.assertFalse(box.model().item(box.currentIndex()).isEnabled())
                self.apply(d);self.assertIsNone(self.w.current['cpu_temp'])
            self.dialog(check)
    def test_live_structure_adds_only_matching_sensors(self):
        import copy
        data=desktop.demo_snapshot();data['sensor_rows']=[];self.w.demo=False;self.w.paused=True
        with patch.object(self.w.collector,'snapshot',side_effect=lambda:copy.deepcopy(data)):
            def check(d):
                d.findChild(QComboBox,'sourceMode').setCurrentIndex(0)
                data['sensor_rows']=[dict(id='/aida/cpu/temperature/0',name='CPU Package',device='CPU',group='CPU',type='Temperature',unit='°C',value=50,source='AIDA64'),dict(id='/aida/gpu/temperature/0',name='GPU Core',device='GPU',group='GPU',type='Temperature',unit='°C',value=40,source='AIDA64')]
                d.findChild(QTimer,'panelLiveRefreshTimer').timeout.emit();box=self.box(d,'cpu_temp')
                self.assertGreater(box.findData('/aida/cpu/temperature/0'),0);self.assertEqual(box.findData('/aida/gpu/temperature/0'),-1);self.assertEqual(box.currentData(),'')
            self.dialog(check)
    def test_core_max_removed_from_both_settings(self):
        self.assertNotIn('cpu_core_max',[key for key,_,_ in SLOTS])
        self.dialog(lambda d:self.assertIsNone(self.box(d,'cpu_core_max')))
        errors=[]
        def check():
            d=QApplication.activeModalWidget()
            try:self.assertIsNone(d.findChild(QComboBox,'dashboardSensor_cpu_core_max'))
            except Exception as e:errors.append(e)
            finally:d.reject()
        QTimer.singleShot(20,check);self.w.configure_dashboard()
        if errors:raise errors[0]
