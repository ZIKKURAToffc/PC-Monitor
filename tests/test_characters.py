import unittest,tempfile,copy,sys
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QCheckBox,QComboBox
from PySide6.QtCore import QSettings,QTimer,QPoint,Qt,QRectF
from PySide6.QtGui import QPixmap,QPainter
from characters import CHARACTERS,portrait,resource_path,header_region,draw_portrait
class CharacterAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_all_six_portraits_and_bundle_resources(self):
        self.assertEqual(len(CHARACTERS),6)
        for key in CHARACTERS:
            self.assertTrue(resource_path(key).is_file());self.assertFalse(portrait(key).isNull());self.assertEqual(portrait(key).width(),230)
        with patch.object(sys,'_MEIPASS','/example/bundle',create=True):self.assertEqual(str(resource_path('frieren')),'/example/bundle/assets/characters/frieren.png')
        self.assertIn(str(Path('assets').resolve())+';assets',__import__('build_windows').pyinstaller_command(Path.cwd(),Path('/scratch'),'python.exe'));self.assertTrue(Path('ASSET-CREDITS.md').is_file())
    def test_missing_image_fails_gracefully(self):
        portrait.cache_clear()
        try:
            with patch('characters.resource_path',return_value=Path('/not-found/portrait.png')):self.assertTrue(portrait('frieren').isNull())
        finally:portrait.cache_clear()
    def test_header_space_rejects_tiny_regions(self):
        self.assertTrue(header_region(500,600,10,110).isEmpty());self.assertTrue(header_region(100,500,10,70).isEmpty());self.assertFalse(header_region(350,900,10,116).isEmpty())
    def test_portrait_drawing_is_clipped_to_assigned_rect(self):
        pix=QPixmap(100,100);pix.fill(Qt.transparent);p=QPainter(pix);self.assertTrue(draw_portrait(p,'frieren',QRectF(10,10,80,80),square=True));p.end();image=pix.toImage()
        self.assertEqual(image.pixelColor(0,0).alpha(),0);self.assertGreater(image.pixelColor(50,50).alpha(),0)
class CharacterUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        import desktop
        self.tmp=tempfile.TemporaryDirectory();self.prefs=QSettings(self.tmp.name+'/p.ini',QSettings.IniFormat);self.p=patch('desktop.QSettings',return_value=self.prefs);self.p.start();self.w=desktop.MonitorWindow(demo=True);self.w.timer.stop();self.w.resize(1366,768);self.w.show();self.app.processEvents()
    def tearDown(self):
        self.w.apply_theme('classic',persist=False);self.w.close();self.w.deleteLater();self.p.stop();self.tmp.cleanup()
    def test_portraits_never_overlap_header_controls_or_data(self):
        root=self.w.centralWidget()
        for key in CHARACTERS:
            self.w.apply_theme(key,persist=False);self.app.processEvents();self.w.update_character_placement();overlay=self.w.character_overlay;self.assertTrue(overlay.isVisible(),key);area=overlay.geometry()
            for widget in [self.w.brand_label,self.w.version_label,self.w.connection,self.w.gear_button,self.w.theme_badge,self.w.clock_widget,self.w.tabs]:
                if not widget.isHidden():self.assertFalse(area.intersects(widget.rect().translated(widget.mapTo(root,QPoint(0,0)))),key)
            self.assertTrue(overlay.testAttribute(Qt.WA_TransparentForMouseEvents))
    def test_small_window_and_non_anime_theme_hide_portrait(self):
        self.w.apply_theme('frieren');self.w.resize(520,600);self.w.adapt_layout();self.app.processEvents();self.w.update_character_placement();self.assertTrue(self.w.character_overlay.isHidden())
        self.w.resize(1366,768);self.w.apply_theme('arctic');self.app.processEvents();self.w.update_character_placement();self.assertTrue(self.w.character_overlay.isHidden())
    def test_picker_toggle_saved_restored_and_cancel_preserves(self):
        import desktop
        errors=[]
        def choose(accept):
            d=QApplication.activeModalWidget()
            try:
                d.findChild(QComboBox,'interfaceTheme').setCurrentIndex(d.findChild(QComboBox,'interfaceTheme').findData('frieren'));d.findChild(QCheckBox,'showCharacters').setChecked(False)
                d.accept() if accept else d.reject()
            except Exception as e:errors.append(e);d.reject()
        QTimer.singleShot(30,lambda:choose(False));self.w.choose_theme();self.assertTrue(self.w.characters_enabled)
        QTimer.singleShot(30,lambda:choose(True));self.w.choose_theme();self.assertFalse(self.w.characters_enabled);self.w.update_character_placement();self.assertTrue(self.w.character_overlay.isHidden())
        other=desktop.MonitorWindow(demo=True)
        try:self.assertFalse(other.characters_enabled);self.assertEqual(other.theme_id,'frieren')
        finally:other.close();other.deleteLater()
        if errors:raise errors[0]
    def test_character_toggle_preserves_monitoring_state(self):
        before=copy.deepcopy(self.w.dashboard_config);points=list(self.w.cpu.graph.points);value=self.w.cpu.temp.text();self.w.paused=True
        self.w.apply_theme('naruto');self.app.processEvents();self.w.characters_enabled=False;self.w.update_character_placement()
        self.assertEqual(self.w.dashboard_config,before);self.assertEqual(self.w.cpu.graph.points,points);self.assertEqual(self.w.cpu.temp.text(),value);self.assertTrue(self.w.paused)
