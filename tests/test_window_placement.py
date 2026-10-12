import tempfile,unittest
from unittest.mock import patch
from PySide6.QtCore import QRect,QSettings,Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from window_placement import fitted_rect,RECT_KEY,MAX_KEY

class PlacementRectTests(unittest.TestCase):
    def test_valid_position_unchanged(self):
        rect=QRect(200,120,700,500);self.assertEqual(fitted_rect(rect,[QRect(0,0,1920,1040)]),rect)
    def test_secondary_monitor_with_negative_origin(self):
        rect=QRect(-1600,100,800,600);self.assertEqual(fitted_rect(rect,[QRect(0,0,1920,1040),QRect(-1920,0,1920,1040)]),rect)
    def test_disconnected_monitor_recovers_to_primary(self):
        rect=fitted_rect(QRect(2200,100,800,600),[QRect(0,0,1920,1040)]);self.assertTrue(QRect(0,0,1920,1040).contains(rect))
    def test_changed_resolution_shrinks_and_clamps(self):
        rect=fitted_rect(QRect(1700,800,1180,1000),[QRect(0,0,1280,720)]);self.assertEqual(rect,QRect(100,0,1180,720))
    def test_partial_offscreen_position_clamped(self):
        self.assertEqual(fitted_rect(QRect(-200,-100,800,600),[QRect(0,0,1920,1040)]),QRect(0,0,800,600))
    def test_largest_overlap_selects_monitor(self):
        self.assertEqual(fitted_rect(QRect(1800,100,800,600),[QRect(0,0,1920,1040),QRect(1920,0,1920,1040)]),QRect(1920,100,800,600))

class WindowPlacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.prefs=QSettings(self.tmp.name+'/prefs.ini',QSettings.IniFormat)
        self.patch=patch('desktop.QSettings',return_value=self.prefs);self.patch.start();self.windows=[]
    def tearDown(self):
        for window in self.windows:
            window.close();window.deleteLater()
        self.app.processEvents();self.patch.stop();self.tmp.cleanup()
    def window(self):
        import desktop
        window=desktop.MonitorWindow(demo=True,tray_mode=False);self.windows.append(window);window.timer.stop();window.clock_timer.stop();window.show();self.app.processEvents();return window
    def placed(self):
        w=self.window();area=w.screen().availableGeometry();w.setGeometry(area.x()+80,area.y()+100,600,500);self.app.processEvents();return w
    def test_close_then_relaunch_restores_position_and_size(self):
        w=self.placed();expected=w.geometry();w.close();restored=self.window();self.assertEqual(restored.geometry(),expected);self.assertFalse(restored.isFullScreen());self.assertFalse(restored.isMinimized())
    def test_movement_saved_live_without_close(self):
        w=self.placed();QTest.qWait(450);self.assertEqual(self.prefs.value(RECT_KEY),w.geometry());self.assertFalse(w.placement_timer.isActive())
    def test_resize_saved_live(self):
        w=self.placed();w.resize(650,520);self.app.processEvents();QTest.qWait(450);self.assertEqual(self.prefs.value(RECT_KEY),w.geometry())
    def test_fullscreen_exit_saved_as_previous_normal_position(self):
        w=self.placed();expected=w.geometry();w.toggle_fullscreen();self.app.processEvents();w.close();restored=self.window();self.assertEqual(restored.geometry(),expected);self.assertFalse(restored.isFullScreen());self.assertFalse(restored.windowFlags()&Qt.FramelessWindowHint)
    def test_topmost_change_preserves_saved_position(self):
        w=self.placed();w.apply_window_mode(on_top=True);self.app.processEvents();expected=w.geometry();w.close();restored=self.window();self.assertEqual(restored.geometry(),expected);self.assertTrue(restored.windowFlags()&Qt.WindowStaysOnTopHint)
    def test_corrupt_legacy_geometry_falls_back_visible(self):
        self.prefs.setValue('geometry',b'invalid');w=self.window();self.assertTrue(w.screen().availableGeometry().contains(w.frameGeometry()))
    def test_legacy_qt_geometry_is_not_unconditionally_centered(self):
        w=self.placed();expected=w.geometry();legacy=w.saveGeometry();w.close();self.prefs.remove(RECT_KEY);self.prefs.remove(MAX_KEY);self.prefs.setValue('geometry',legacy);restored=self.window();self.assertEqual(restored.geometry(),expected)
    def test_removed_monitor_restores_in_visible_area(self):
        self.prefs.setValue(RECT_KEY,QRect(20000,20000,600,500));w=self.window();self.assertTrue(w.screen().availableGeometry().contains(w.frameGeometry()))
    def test_maximized_state_restored_without_fullscreen(self):
        w=self.placed();expected=w.geometry();w.showMaximized();self.app.processEvents();w.close();restored=self.window();self.assertTrue(restored.isMaximized());self.assertFalse(restored.isFullScreen());restored.showNormal();self.app.processEvents();self.assertEqual(restored.geometry(),expected)
    def test_fullscreen_does_not_overwrite_live_normal_rectangle(self):
        w=self.placed();expected=w.geometry();w.toggle_fullscreen();self.app.processEvents();QTest.qWait(450);self.assertEqual(self.prefs.value(RECT_KEY),expected)
    def test_no_saved_position_initially_visible(self):
        w=self.window();self.assertTrue(w.screen().availableGeometry().contains(w.frameGeometry()))
