import tempfile,unittest
from unittest.mock import patch
from PySide6.QtCore import QSettings,QTimer
from PySide6.QtWidgets import QApplication,QDialog,QLineEdit,QComboBox
import desktop,i18n
class LocalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.prefs=QSettings(self.tmp.name+'/prefs.ini',QSettings.IniFormat);self.patch=patch('desktop.QSettings',return_value=self.prefs);self.patch.start();self.w=desktop.MonitorWindow(demo=True);self.w.show();self.app.processEvents()
    def tearDown(self):self.w.close();self.patch.stop();self.tmp.cleanup();i18n.set_language('ru')
    def save(self,lang,name):
        def accept():
            d=self.w.findChildren(QDialog)[-1];d.findChild(QLineEdit,'displayName').setText(name);c=d.findChild(QComboBox,'interfaceLanguage');c.setCurrentIndex(c.findData(lang));d.accept()
        QTimer.singleShot(5,accept);self.w.show_settings();self.app.processEvents()
    def test_hidden_tabs_and_navigation(self):
        self.assertTrue(self.w.tabs.tabBar().isHidden());self.assertEqual(len(self.w.section_actions),3)
        for i,a in enumerate(self.w.section_actions):a.trigger();self.assertEqual(self.w.tabs.currentIndex(),i);self.w.sync_control_menu();self.assertTrue(a.isChecked())
    def test_languages_and_return_to_russian(self):
        for lang,menu,card in [('en','Settings','POWER'),('uk','Налаштування','ПОТУЖНІСТЬ'),('ru','Настройки','МОЩНОСТЬ')]:
            self.save(lang,'Roman');self.assertEqual(self.w.control_menu.actions()[5].text(),menu);self.assertEqual(self.w.cpu.metrics['cpu_power'].label.text(),card);self.assertEqual(self.w.brand_label.text(),'Roman');self.assertEqual(self.prefs.value('language'),lang)
            self.assertEqual(self.w.tabs.tabText(1),i18n.t('Температуры'));self.assertEqual(self.w.table.horizontalHeaderItem(0).text(),i18n.t('Устройство / датчик'))
    def test_stable_filter_and_hardware_names(self):
        self.save('en','Настройки');self.assertEqual(self.w.brand_label.text(),'Настройки')
        self.w.group_filter.setCurrentIndex(self.w.group_filter.findData('Накопитель'));self.w.refresh();self.assertEqual(self.w.table.rowCount(),1);self.assertIn('Composite',self.w.table.item(0,0).text())
        self.assertEqual(self.w.base_snapshot['temperatures'][9]['group'],'Накопитель');self.assertEqual(self.w.current['sensor_rows'][0]['name'],'CPU Package')
    def test_user_labels_not_translated(self):
        self.w.dashboard_config={'slots':{'cpu_power':{'label':'Настройки'}},'custom':[{'sensor':'demo/9','label':'Плата','unit':'°C'}]};self.w.rebuild_custom_cards();self.save('en','<Roman>');self.assertEqual(self.w.cpu.metrics['cpu_power'].label.text(),'Настройки');self.assertEqual(self.w.custom_widgets[0][1].label.text(),'Плата');self.assertEqual(self.w.brand_label.text(),'<Roman>')
    def test_saved_name_language_loaded(self):
        self.save('uk','  ROMAN   PC  ');other=desktop.MonitorWindow(demo=True)
        try:self.assertEqual(other.nickname,'ROMAN PC');self.assertEqual(other.language,'uk');self.assertEqual(other.pause_button.text(),'Пауза');self.assertIn('ROMAN PC',other.windowTitle())
        finally:other.close()
    def test_paused_state_survives_settings(self):
        self.w.toggle_pause();self.save('en','Roman');self.assertTrue(self.w.paused);self.assertEqual(self.w.pause_button.text(),'Resume');self.assertEqual(self.w.connection.text(),'PAUSED / READINGS FROZEN')
    def test_plain_input_and_icon(self):
        self.assertEqual(desktop.clean_nickname('  '),'PC MONITOR');self.assertEqual(len(desktop.clean_nickname('x'*60)),48);self.assertFalse(self.w.gear_button.icon().isNull());self.assertEqual(self.w.gear_button.text(),'')
