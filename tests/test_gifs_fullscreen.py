import unittest,tempfile,copy,sys
from pathlib import Path
from unittest.mock import patch
from PIL import Image,ImageSequence
from PySide6.QtWidgets import QApplication,QCheckBox
from PySide6.QtCore import QSettings,QTimer,Qt
from PySide6.QtGui import QMovie
from PySide6.QtTest import QTest
from characters import PROFILES,PortraitPlayer,animation_path
from themes import ThemePreview

class GifAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_all_sixteen_are_real_animated_gifs(self):
        for key in PROFILES:
            path=animation_path(key);self.assertTrue(path.is_file(),key)
            with Image.open(path) as im:
                self.assertEqual(im.format,'GIF');self.assertGreater(im.n_frames,1,key);self.assertLessEqual(max(im.size),320)
                samples=set()
                for frame in ImageSequence.Iterator(im):
                    self.assertGreaterEqual(frame.info.get('duration',0),40,key);samples.add(frame.convert('RGB').tobytes())
                self.assertGreater(len(samples),1,key)
    def test_landscape_gif_is_cropped_not_stretched_in_tall_preview(self):
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import QRectF
        from unittest.mock import MagicMock
        from characters import draw_portrait
        image=QPixmap(320,180);image.fill(Qt.red);painter=MagicMock();target=QRectF(0,0,120,180)
        self.assertTrue(draw_portrait(painter,'nami',target,image=image));source=painter.drawPixmap.call_args.args[2]
        self.assertAlmostEqual(source.width()/source.height(),target.width()/target.height());self.assertLessEqual(source.right(),image.width());self.assertLessEqual(source.bottom(),image.height())
    def test_bundle_gif_path_and_assets_flag(self):
        with patch.object(sys,'_MEIPASS','/bundle',create=True):self.assertEqual(str(animation_path('misa')),'/bundle/assets/characters/misa.gif')
        self.assertIn(str(Path('assets').resolve())+';assets',__import__('build_windows').pyinstaller_command(Path.cwd(),Path('/scratch'),'python.exe'))
    def test_movie_missing_or_invalid_falls_back(self):
        from PySide6.QtWidgets import QWidget
        owner=QWidget();player=PortraitPlayer(owner)
        with patch('characters.animation_path',return_value=Path('/missing.gif')):player.set_profile('fern')
        self.assertIsNone(player.movie);self.assertFalse(player.image().isNull())
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.gif';p.write_bytes(b'not an image')
            with patch('characters.animation_path',return_value=p):player.set_profile('nami')
            self.assertIsNone(player.movie);self.assertFalse(player.image().isNull())
        owner.deleteLater()

class GifAndWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        import desktop
        self.tmp=tempfile.TemporaryDirectory();self.prefs=QSettings(self.tmp.name+'/p.ini',QSettings.IniFormat);self.p=patch('desktop.QSettings',return_value=self.prefs);self.p.start();self.w=desktop.MonitorWindow(demo=True,tray_mode=False);self.w.timer.stop();self.w.clock_timer.stop();self.w.resize(1366,768);self.w.show();self.app.processEvents()
    def tearDown(self):self.w.apply_theme('classic',persist=False);self.w.close();self.w.deleteLater();self.p.stop();self.tmp.cleanup()
    def test_gif_plays_and_changes_frames_without_changing_data(self):
        self.w.apply_theme('frieren');p=self.w.character_overlay.player;self.assertEqual(p.movie.cacheMode(),QMovie.CacheNone);seen=[];p.movie.frameChanged.connect(seen.append);data=copy.deepcopy(self.w.current);history=list(self.w.cpu.graph.points);QTest.qWait(350);self.assertGreater(len(set(seen)),1);self.assertEqual(self.w.current,data);self.assertEqual(self.w.cpu.graph.points,history)
    def test_gif_pauses_hidden_disabled_and_stops_on_close(self):
        self.w.apply_theme('naruto');p=self.w.character_overlay.player;self.assertEqual(p.movie.state(),QMovie.Running)
        self.w.resize(520,600);self.app.processEvents();self.w.update_character_placement();self.assertEqual(p.movie.state(),QMovie.Paused)
        self.w.resize(1366,768);self.w.animation_enabled=False;self.w.apply_theme('naruto');self.assertNotEqual(p.movie.state(),QMovie.Running)
        self.w.animation_enabled=True;self.w.apply_theme('naruto');self.assertEqual(p.movie.state(),QMovie.Running);self.w.close();self.assertEqual(p.movie.state(),QMovie.NotRunning)
    def test_effects_off_does_not_disable_gif(self):
        self.w.effects_enabled=False;self.w.animation_enabled=True;self.w.apply_theme('titan');o=self.w.character_overlay;self.assertFalse(o.effect_timer.isActive());self.assertEqual(o.player.movie.state(),QMovie.Running)
    def test_profile_switch_stops_old_movie(self):
        self.w.apply_theme('one_piece');p=self.w.character_overlay.player;old=p.movie;self.w.character_choices['one_piece']='robin';self.w.apply_theme('one_piece');self.assertEqual(old.state(),QMovie.NotRunning);self.assertEqual(p.key,'robin');self.assertEqual(p.movie.state(),QMovie.Running)
    def test_preview_player_works_and_stops_when_hidden(self):
        p=ThemePreview('one_punch');p.resize(640,500);p.set_character('fubuki');p.show();self.app.processEvents();self.assertEqual(p.player.movie.state(),QMovie.Running);p.hide();self.assertEqual(p.player.movie.state(),QMovie.Paused);p.player.stop();p.deleteLater()
    def test_fullscreen_is_frameless_with_or_without_topmost(self):
        self.w.toggle_fullscreen();self.app.processEvents();self.assertTrue(self.w.isFullScreen());self.assertTrue(self.w.windowFlags()&Qt.FramelessWindowHint)
        for value in (True,False,True):
            self.w.apply_window_mode(on_top=value);self.app.processEvents();self.assertTrue(self.w.isFullScreen());self.assertTrue(self.w.windowFlags()&Qt.FramelessWindowHint);self.assertEqual(bool(self.w.windowFlags()&Qt.WindowStaysOnTopHint),value)
    def test_settings_save_keeps_fullscreen_topmost_and_no_titlebar(self):
        self.w.toggle_fullscreen();errors=[]
        def change():
            d=QApplication.activeModalWidget()
            try:d.findChild(QCheckBox,'alwaysOnTop').setChecked(True);d.accept()
            except Exception as e:errors.append(e);d.reject()
        QTimer.singleShot(30,change);self.w.show_settings();self.app.processEvents()
        if errors:raise errors[0]
        self.assertTrue(self.w.isFullScreen());self.assertTrue(self.w.windowFlags()&Qt.WindowStaysOnTopHint);self.assertTrue(self.w.windowFlags()&Qt.FramelessWindowHint)
    def test_escape_restores_normal_geometry_and_topmost(self):
        self.w.setGeometry(30,30,700,600);self.app.processEvents();size=self.w.size();self.w.apply_window_mode(on_top=True);self.w.toggle_fullscreen();self.w.escape();self.app.processEvents();self.assertFalse(self.w.isFullScreen());self.assertFalse(self.w.windowFlags()&Qt.FramelessWindowHint);self.assertTrue(self.w.windowFlags()&Qt.WindowStaysOnTopHint);self.assertEqual(self.w.size(),size)
    def test_topmost_in_normal_mode_keeps_normal_titlebar(self):
        self.w.apply_window_mode(on_top=True);self.assertFalse(self.w.isFullScreen());self.assertFalse(self.w.windowFlags()&Qt.FramelessWindowHint);self.assertTrue(self.w.isVisible())
    def test_tray_restore_preserves_fullscreen(self):
        self.w.toggle_fullscreen();self.w.showMinimized();self.w.show_from_tray();self.app.processEvents();self.assertTrue(self.w.isFullScreen());self.assertFalse(self.w.isMinimized());self.assertTrue(self.w.windowFlags()&Qt.FramelessWindowHint)
    def test_topmost_persisted_and_startup_normal(self):
        import desktop
        self.w.apply_window_mode(on_top=True);self.w.toggle_fullscreen();self.w.close();other=desktop.MonitorWindow(demo=True,tray_mode=False)
        try:self.assertTrue(other.windowFlags()&Qt.WindowStaysOnTopHint);self.assertFalse(other.windowFlags()&Qt.FramelessWindowHint);self.assertFalse(other.isFullScreen())
        finally:other.close();other.deleteLater()
    def test_fullscreen_style_changes_keep_window_flags(self):
        self.w.apply_window_mode(on_top=True);self.w.toggle_fullscreen();self.w.apply_theme('death_note');self.assertTrue(self.w.isFullScreen());self.assertTrue(self.w.windowFlags()&Qt.FramelessWindowHint);self.assertTrue(self.w.windowFlags()&Qt.WindowStaysOnTopHint)
