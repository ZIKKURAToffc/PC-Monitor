import unittest,tempfile,copy,gc
from unittest.mock import patch
from themes import THEMES,contrast,theme_css,theme_color,theme_name,valid_theme,set_active_theme
class PaletteTests(unittest.TestCase):
    def tearDown(self):set_active_theme('classic')
    def test_ten_themes_and_all_anime_presets(self):
        self.assertEqual(len(THEMES),10)
        for key in ['frieren','one_piece','one_punch','naruto','death_note','titan']:self.assertTrue(THEMES[key]['motif'])
        for key in THEMES:
            for lang in ('ru','uk','en'):self.assertTrue(theme_name(key,lang))
    def test_contrast_of_data_strips_and_alerts(self):
        for key,data in THEMES.items():
            p=data['palette'];self.assertGreaterEqual(contrast(p['strip_text'],p['accent']),7,key)
            for role in ('bg','panel','input'):
                self.assertGreaterEqual(contrast(p['accent'],p[role]),4.5,key);self.assertGreaterEqual(contrast(p['muted'],p[role]),4.5,key)
            self.assertGreaterEqual(contrast(p['warning'],p['panel']),4.5,key);self.assertGreaterEqual(contrast(p['hotstrip'],p['accent']),4.5,key)
    def test_classic_css_preserved_and_unknown_fallback(self):
        css='background:#060b09;color:#18ffe0;border:1px solid #ff442d;'
        self.assertEqual(theme_css(css,'classic'),css);self.assertEqual(valid_theme('missing'),'classic');self.assertEqual(theme_css(css,'missing'),css)
    def test_mapping_is_single_pass_and_roles_are_distinct(self):
        for key in THEMES:
            css=theme_css('color:#18ffe0;background:#06100b;',key)
            self.assertIn(THEMES[key]['palette']['accent'],css);self.assertIn(THEMES[key]['palette']['strip_text'],css)
            self.assertEqual(theme_color('#ff7777',key),THEMES[key]['palette']['warning'])
class ThemeQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QSettings,QCoreApplication,QEvent
        import desktop
        gc.collect()
        for w in QApplication.topLevelWidgets():
            if not w.isVisible():w.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
        self.tmp=tempfile.TemporaryDirectory();self.prefs=QSettings(self.tmp.name+'/p.ini',QSettings.IniFormat);self.p=patch('desktop.QSettings',return_value=self.prefs);self.p.start();self.w=desktop.MonitorWindow(demo=True);self.w.resize(1366,768);self.w.show();self.app.processEvents()
    def tearDown(self):
        import i18n
        self.w.apply_theme('classic',persist=False);self.w.close();self.w.deleteLater();self.p.stop();self.tmp.cleanup();i18n.set_language('ru')
    def chooser(self,key,accept):
        from PySide6.QtWidgets import QApplication,QComboBox
        from PySide6.QtCore import QTimer
        errors=[]
        def edit():
            d=QApplication.activeModalWidget()
            try:
                box=d.findChild(QComboBox,'interfaceTheme');self.assertEqual(box.count(),10);box.setCurrentIndex(box.findData(key));d.accept() if accept else d.reject()
            except Exception as e:errors.append(e);d.reject()
        QTimer.singleShot(30,edit);self.w.choose_theme()
        if errors:raise errors[0]
    def test_picker_apply_saves_and_restores(self):
        import desktop
        self.chooser('frieren',True);self.assertEqual(self.w.theme_id,'frieren');self.assertEqual(self.prefs.value('interface_theme'),'frieren');other=desktop.MonitorWindow(demo=True)
        try:self.assertEqual(other.theme_id,'frieren')
        finally:other.close();other.deleteLater()
    def test_picker_cancel_preserves_theme_and_settings(self):
        self.chooser('naruto',False);self.assertEqual(self.w.theme_id,'classic');self.assertIsNone(self.prefs.value('interface_theme'))
    def test_all_palettes_keep_readings_mapping_graph_history_and_font_sizes(self):
        self.w.timer.stop()
        before=copy.deepcopy(self.w.dashboard_config);points=list(self.w.cpu.graph.points);value=self.w.cpu.temp.text();font=self.w.cpu.temp.font().pixelSize()
        for key in THEMES:
            self.w.apply_theme(key,persist=False);self.app.processEvents();self.assertEqual(self.w.dashboard_config,before);self.assertEqual(self.w.cpu.graph.points,points);self.assertEqual(self.w.cpu.temp.text(),value);self.assertEqual(self.w.cpu.temp.font().pixelSize(),font)
            self.assertEqual(self.w.theme_badge.isVisible(),bool(THEMES[key]['motif']))
    def test_refresh_does_not_restore_classic_colors_and_gear_has_no_backing(self):
        import desktop
        self.w.apply_theme('arctic');self.w.refresh();self.assertIn(THEMES['arctic']['palette']['accent'],self.w.fps_metric.value.styleSheet());self.assertNotIn('#18ffe0',self.w.cpu.header_layout.parentWidget().styleSheet())
        from PySide6.QtCore import Qt
        self.w.gear_button.setFocus(Qt.TabFocusReason);self.w.gear_button.setDown(True);self.app.processEvents();image=self.w.gear_button.grab().toImage()
        self.assertNotEqual(image.pixelColor(2,22).name(),THEMES['arctic']['palette']['accent'])
    def test_settings_has_style_button_and_anime_descriptions_localize(self):
        from PySide6.QtWidgets import QApplication,QPushButton
        from PySide6.QtCore import QTimer
        import i18n
        errors=[]
        def check():
            d=QApplication.activeModalWidget()
            try:self.assertIsNotNone(d.findChild(QPushButton,'chooseInterfaceStyle'))
            except Exception as e:errors.append(e)
            finally:d.reject()
        QTimer.singleShot(30,check);self.w.show_settings()
        if errors:raise errors[0]
        for code,name in [('ru','Фрирен'),('uk','Фрірен'),('en','Frieren')]:self.assertEqual(theme_name('frieren',code),name)
    def test_style_application_while_paused_keeps_pause_and_values(self):
        self.w.paused=True;before=self.w.fps_metric.value.text();self.w.apply_theme('death_note');self.assertTrue(self.w.paused);self.assertEqual(self.w.fps_metric.value.text(),before)
