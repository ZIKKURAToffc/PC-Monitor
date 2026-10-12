import unittest,tempfile,copy
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QComboBox,QCheckBox
from PySide6.QtCore import QSettings,QTimer,Qt,QRectF,QPoint
from PySide6.QtGui import QPixmap,QPainter
from characters import PROFILES,THEME_PROFILES,valid_character,portrait,character_name
from themes import THEMES,theme_css,contrast,blend,set_visual_effects,set_active_theme
from effects import paint_scene

class HeroineAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_all_added_images_and_source_credits(self):
        keys=['fern','nami','robin','tatsumaki','fubuki','hinata','sakura','misa','mikasa','annie']
        for key in keys:
            self.assertFalse(portrait(key).isNull(),key);self.assertEqual(portrait(key).width(),230);self.assertIn('/'+key+'.png',Path('ASSET-CREDITS.md').read_text())
        self.assertEqual(len(PROFILES),16)
    def test_profiles_belong_to_correct_series(self):
        for theme,profiles in THEME_PROFILES.items():
            for key in profiles:self.assertEqual(PROFILES[key]['theme'],theme)
        self.assertEqual(valid_character('one_piece','mikasa'),'nami');self.assertEqual(valid_character('death_note','tatsumaki'),'misa');self.assertIsNone(valid_character('classic','nami'))
    def test_names_localized(self):
        for key in PROFILES:
            for code in ('ru','uk','en'):self.assertTrue(character_name(key,code))
        self.assertEqual(character_name('tatsumaki'),'Тацумаки');self.assertEqual(character_name('misa','en'),'Misa Amane')
    def test_scene_painting_clipped_for_all_anime(self):
        for key in THEME_PROFILES:
            pix=QPixmap(160,160);pix.fill(Qt.transparent);p=QPainter(pix);paint_scene(p,QRectF(30,30,100,100),key,THEMES[key]['palette'],.5);p.end();im=pix.toImage();self.assertEqual(im.pixelColor(0,0).alpha(),0);self.assertEqual(im.pixelColor(29,80).alpha(),0);self.assertGreater(im.pixelColor(80,80).alpha(),0)
    def test_rich_gradients_can_be_disabled(self):
        try:
            set_visual_effects(True);self.assertIn('qlineargradient',theme_css('QFrame {background:#0b1510;}', 'naruto'))
            self.assertNotIn('qlineargradient',theme_css('QFrame {background:#0b1510;}','classic'))
            set_visual_effects(False);self.assertNotIn('qlineargradient',theme_css('QFrame {background:#0b1510;}', 'naruto'))
        finally:set_visual_effects(True)
    def test_gradient_endpoints_keep_contrast(self):
        for key in THEME_PROFILES:
            p=THEMES[key]['palette'];self.assertGreaterEqual(contrast(p['strip_text'],blend(p['accent'],'#ffffff',.10)),7)
            for role in ('panel','input'):
                c=blend(p[role],p['chart'],.045);self.assertGreaterEqual(contrast(c,p['muted']),4.5,key);self.assertGreaterEqual(contrast(c,p['accent']),4.5,key)

class HeroineUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        import desktop
        self.tmp=tempfile.TemporaryDirectory();self.settings=QSettings(self.tmp.name+'/p.ini',QSettings.IniFormat);self.patch=patch('desktop.QSettings',return_value=self.settings);self.patch.start();self.w=desktop.MonitorWindow(demo=True);self.w.timer.stop();self.w.resize(1366,768);self.w.show();self.app.processEvents()
    def tearDown(self):self.w.apply_theme('classic',persist=False);self.w.close();self.w.deleteLater();self.patch.stop();self.tmp.cleanup();set_visual_effects(True);set_active_theme('classic')
    def edit_picker(self,accept=True):
        errors=[]
        def change():
            d=QApplication.activeModalWidget()
            try:
                d.findChild(QComboBox,'interfaceTheme').setCurrentIndex(d.findChild(QComboBox,'interfaceTheme').findData('naruto'))
                box=d.findChild(QComboBox,'themeCharacter');self.assertEqual([box.itemData(i) for i in range(box.count())],['hinata','sakura','naruto']);box.setCurrentIndex(box.findData('sakura'))
                d.findChild(QCheckBox,'animeEffects').setChecked(False);d.findChild(QCheckBox,'animeAnimation').setChecked(False)
                d.accept() if accept else d.reject()
            except Exception as e:errors.append(e);d.reject()
        QTimer.singleShot(30,change);self.w.choose_theme()
        if errors:raise errors[0]
    def test_picker_saves_profile_and_effect_flags(self):
        import desktop
        self.edit_picker();self.assertEqual(self.w.character_overlay.key,'sakura');self.assertFalse(self.w.effects_enabled);self.assertFalse(self.w.animation_enabled);self.assertEqual(self.settings.value('theme_character/naruto'),'sakura')
        other=desktop.MonitorWindow(demo=True)
        try:self.assertEqual(other.character_choices['naruto'],'sakura');self.assertFalse(other.effects_enabled)
        finally:other.close();other.deleteLater()
    def test_cancel_keeps_all_choices_and_flags(self):
        before=dict(self.w.character_choices);self.edit_picker(False);self.assertEqual(self.w.theme_id,'classic');self.assertEqual(self.w.character_choices,before);self.assertTrue(self.w.effects_enabled);self.assertTrue(self.w.animation_enabled);self.assertIsNone(self.settings.value('theme_character/naruto'))
    def test_all_profiles_respect_reserved_empty_header(self):
        root=self.w.centralWidget()
        for theme,profiles in THEME_PROFILES.items():
            for profile in profiles:
                self.w.character_choices[theme]=profile;self.w.apply_theme(theme,persist=False);self.app.processEvents();self.w.update_character_placement();o=self.w.character_overlay;self.assertEqual(o.key,profile);self.assertTrue(o.isVisible());self.assertTrue(o.testAttribute(Qt.WA_TransparentForMouseEvents))
                for widget in (self.w.brand_label,self.w.version_label,self.w.connection,self.w.gear_button,self.w.clock_widget,self.w.tabs):
                    self.assertFalse(o.geometry().intersects(widget.rect().translated(widget.mapTo(root,QPoint(0,0)))))
    def test_animation_stops_hidden_disabled_and_close(self):
        self.w.apply_theme('one_punch');o=self.w.character_overlay;self.assertTrue(o.effect_timer.isActive());self.w.resize(520,600);self.app.processEvents();self.w.update_character_placement();self.assertTrue(o.isHidden());self.assertFalse(o.effect_timer.isActive())
        self.w.resize(1366,768);self.w.animation_enabled=False;self.w.apply_theme('one_punch');self.assertFalse(o.effect_timer.isActive());self.assertTrue(o.effects_enabled)
        self.w.animation_enabled=True;self.w.apply_theme('one_punch');self.assertTrue(o.effect_timer.isActive());self.w.close();self.assertFalse(o.effect_timer.isActive())
    def test_animation_does_not_change_data_or_history(self):
        self.w.apply_theme('titan');data=copy.deepcopy(self.w.current);history=list(self.w.cpu.graph.points);config=copy.deepcopy(self.w.dashboard_config)
        for _ in range(20):self.w.character_overlay.advance_effect()
        self.assertEqual(self.w.current,data);self.assertEqual(self.w.cpu.graph.points,history);self.assertEqual(self.w.dashboard_config,config)
    def test_invalid_saved_profile_falls_back_within_anime(self):
        import desktop
        self.settings.setValue('theme_character/frieren','nami');other=desktop.MonitorWindow(demo=True)
        try:self.assertEqual(other.character_choices['frieren'],'frieren')
        finally:other.close();other.deleteLater()
