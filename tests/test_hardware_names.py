import unittest,tempfile
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QDialog,QComboBox
from PySide6.QtCore import QSettings,QTimer
import desktop,i18n
class HardwareNamesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.settings=QSettings(self.tmp.name+'/p.ini',QSettings.IniFormat);self.p=patch('desktop.QSettings',return_value=self.settings);self.p.start();self.w=desktop.MonitorWindow(demo=True);self.w.show();self.app.processEvents()
    def tearDown(self):self.w.close();self.p.stop();self.tmp.cleanup();i18n.set_language('ru')
    def settings_dialog(self,values,accept=True):
        errors=[]
        def edit():
            d=QApplication.activeModalWidget()
            try:
                for key,value in values.items():d.findChild(QComboBox,'hardwareName_'+key).setEditText(value)
                d.accept() if accept else d.reject()
            except Exception as e:errors.append(e);d.reject()
        QTimer.singleShot(20,edit);self.w.show_settings()
        if errors:raise errors[0]
    def test_actual_font_identical_for_all_text_in_main_strips(self):
        for compact in (True,False):
            self.w.compact_mode=compact;self.w.adapt_layout();self.app.processEvents()
            labels=[self.w.cpu.title_label,self.w.cpu.slash_label,self.w.cpu.temp,self.w.cpu.detail,self.w.gpu.title_label,self.w.gpu.slash_label,self.w.gpu.temp,self.w.gpu.detail,self.w.syshead,self.w.board_caption,self.w.board_temp]
            reference=labels[0].font()
            for label in labels:self.assertEqual(label.font(),reference);self.assertEqual(label.font().pixelSize(),18 if compact else 24)
    def test_save_restore_and_no_sensor_remapping(self):
        before=dict(self.w.dashboard_config);self.settings_dialog({'cpu':'AMD Ryzen 9 5950X','gpu':'NVIDIA RTX 5070','board':'ASUS TUF'})
        self.assertEqual(self.w.cpu.title_label.text(),'AMD Ryzen 9 5950X');self.assertEqual(self.w.gpu.title_label.text(),'NVIDIA RTX 5070');self.assertTrue(self.w.syshead.text().startswith('ASUS TUF  //////'));self.assertEqual(self.w.board_caption.text(),'ПЛАТА');self.assertEqual(self.w.dashboard_config,before);self.assertEqual(self.w.current['cpu_temp'],47)
        other=desktop.MonitorWindow(demo=True)
        try:self.assertEqual(other.hardware_names,self.w.hardware_names);self.assertEqual(other.gpu.title_label.text(),'NVIDIA RTX 5070')
        finally:other.close()
    def test_empty_resets_and_cancel_does_not_save(self):
        self.settings_dialog({'cpu':'Ryzen','gpu':'RTX','board':'Mainboard'});self.settings_dialog({'cpu':'Changed'},False);self.assertEqual(self.w.cpu.title_label.text(),'Ryzen')
        self.settings_dialog({'cpu':' ','gpu':'','board':''});self.assertEqual(self.w.cpu.title_label.text(),'CPU');self.assertEqual(self.w.gpu.title_label.text(),'GPU');self.assertEqual(self.w.board_caption.text(),'ПЛАТА')
    def test_names_not_translated_or_interpreted_as_html(self):
        self.settings_dialog({'cpu':'Настройки','gpu':'<GPU>','board':'Плата пользователя'});i18n.set_language('en');self.w.refresh();self.assertEqual(self.w.cpu.title_label.text(),'Настройки');self.assertEqual(self.w.gpu.title_label.text(),'<GPU>');self.assertTrue(self.w.syshead.text().startswith('Плата пользователя  //////'));self.assertIn('MEMORY AND RESOURCES',self.w.syshead.text())
    def test_long_names_do_not_push_values_outside_header(self):
        self.settings_dialog({'cpu':'x'*80,'gpu':'y'*80,'board':'z'*80});self.w.resize(520,600);self.w.adapt_layout();self.app.processEvents()
        viewport=self.w.overview_scroll.viewport()
        for value in [self.w.cpu.temp,self.w.gpu.temp,self.w.board_temp]:self.assertLess(value.mapTo(viewport,value.rect().topRight()).x(),viewport.width())
    def test_gear_has_no_red_border_any_state(self):
        import re
        for rule in re.findall(r'QToolButton#controlGear[^{}]*\{([^{}]*)\}',desktop.STYLE):self.assertNotIn('#ff442d',rule);self.assertIn('border:0',rule) if 'menu-indicator' not in rule and 'image:none' not in rule else None

    def test_section_numbers_removed_not_just_hidden(self):
        from PySide6.QtWidgets import QLabel
        for section in [self.w.cpu,self.w.gpu]:
            self.assertFalse(hasattr(section,'index_label'))
            header=section.header_layout.parentWidget()
            self.assertFalse(any(label.text() in ('01','02') for label in header.findChildren(QLabel)))
        self.assertIn('ядер',self.w.cpu.detail.text());self.assertIn('ПАМЯТЬ GPU',self.w.gpu.detail.text())

    def test_board_title_languages_and_reset(self):
        self.w.hardware_names['board']='ASUS TUF'
        for code,caption in [('ru','ПАМЯТЬ И РЕСУРСЫ'),('uk','ПАМ’ЯТЬ І РЕСУРСИ'),('en','MEMORY AND RESOURCES')]:
            i18n.set_language(code);self.w.refresh()
            self.assertEqual(self.w.syshead.text(),'ASUS TUF  //////  '+caption)
            i18n.localize_tree(self.w)
            self.assertTrue(self.w.syshead.text().startswith('ASUS TUF'))
        self.w.hardware_names['board']='';self.w.refresh();self.assertTrue(self.w.syshead.text().startswith('SYS  //////'))
