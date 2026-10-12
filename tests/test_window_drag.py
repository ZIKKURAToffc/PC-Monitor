import tempfile,unittest,copy
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QEvent,QPoint,QPointF,QSettings
from PySide6.QtGui import QMouseEvent

class WindowDragTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        import desktop
        self.tmp=tempfile.TemporaryDirectory();self.prefs=QSettings(self.tmp.name+'/p.ini',QSettings.IniFormat);self.p=patch('desktop.QSettings',return_value=self.prefs);self.p.start();self.w=desktop.MonitorWindow(demo=True,tray_mode=False);self.w.timer.stop();self.w.clock_timer.stop();self.w.setGeometry(30,30,700,600);self.w.show();self.app.processEvents();self.c=self.w.header_drag;self.native=patch.object(self.c,'native_move',return_value=False);self.mock_native=self.native.start()
    def tearDown(self):self.c.cancel();self.w.close();self.w.deleteLater();self.native.stop();self.p.stop();self.tmp.cleanup()
    def event(self,widget,kind,point=None,global_point=None,button=Qt.LeftButton,buttons=Qt.LeftButton):
        point=point or QPoint(8,8);global_point=global_point or widget.mapToGlobal(point);event=QMouseEvent(kind,QPointF(point),QPointF(global_point),button,buttons,Qt.NoModifier);QApplication.sendEvent(widget,event)
    def start(self,widget=None):
        widget=widget or self.w.brand_label;pos=widget.mapToGlobal(QPoint(8,8));self.event(widget,QEvent.MouseButtonPress,global_point=pos);return widget,pos
    def test_drag_title_uses_global_delta_then_release(self):
        before=self.w.pos();widget,p=self.start();self.assertTrue(self.c.dragging);self.event(widget,QEvent.MouseMove,global_point=p+QPoint(40,25),button=Qt.NoButton);self.assertEqual(self.w.pos(),before+QPoint(40,25));self.event(widget,QEvent.MouseButtonRelease,global_point=p+QPoint(40,25),buttons=Qt.NoButton);self.assertFalse(self.c.dragging)
    def test_blank_header_is_draggable(self):
        root=self.w.centralWidget();point=QPoint(root.width()-20,3);before=self.w.pos();p=root.mapToGlobal(point);self.event(root,QEvent.MouseButtonPress,point,p);self.event(root,QEvent.MouseMove,point,p+QPoint(20,10),Qt.NoButton);self.assertEqual(self.w.pos(),before+QPoint(20,10))
    def test_clock_and_status_labels_are_draggable(self):
        for widget in (self.w.clock,self.w.clock_date,self.w.clock_zone,self.w.connection,self.w.version_label):
            self.start(widget);self.assertTrue(self.c.dragging);self.c.cancel()
    def test_native_system_move_is_preferred(self):
        with patch.object(self.c,'native_move',return_value=True) as native:
            self.start();native.assert_called_once();self.assertFalse(self.c.dragging)
    def test_controls_and_data_are_excluded(self):
        root=self.w.centralWidget();self.assertNotIn(self.w.gear_button,self.c.targets);self.assertNotIn(self.w.cpu.graph,self.c.targets);self.assertNotIn(self.w.table,self.c.targets);self.assertFalse(self.c.in_header(root,QPoint(100,root.height()-20)));self.assertFalse(self.c.in_header(self.w.gear_button,QPoint(10,10)));self.event(root,QEvent.MouseButtonPress,QPoint(100,root.height()-20));self.assertFalse(self.c.dragging);self.mock_native.assert_not_called()
    def test_right_button_does_not_drag(self):
        self.event(self.w.brand_label,QEvent.MouseButtonPress,button=Qt.RightButton,buttons=Qt.RightButton);self.assertFalse(self.c.dragging);self.mock_native.assert_not_called()
    def test_fullscreen_does_not_move(self):
        self.w.toggle_fullscreen();before=self.w.pos();self.start();self.assertFalse(self.c.dragging);self.assertEqual(self.w.pos(),before);self.mock_native.assert_not_called();self.assertTrue(self.w.windowFlags()&Qt.FramelessWindowHint)
    def test_topmost_window_can_move_without_losing_flag(self):
        self.w.apply_window_mode(on_top=True);before=self.w.pos();widget,p=self.start();self.event(widget,QEvent.MouseMove,global_point=p+QPoint(30,20),button=Qt.NoButton);self.assertEqual(self.w.pos(),before+QPoint(30,20));self.assertTrue(self.w.windowFlags()&Qt.WindowStaysOnTopHint)
    def test_manual_drag_restores_maximized_window(self):
        self.w.showMaximized();self.app.processEvents();self.start();self.assertFalse(self.w.isMaximized());self.assertFalse(self.w.isFullScreen());self.assertTrue(self.c.dragging)
    def test_lost_button_cancels_drag(self):
        widget,p=self.start();widget.setMouseTracking(True);before=self.w.pos();self.event(widget,QEvent.MouseMove,global_point=p+QPoint(100,50),button=Qt.NoButton,buttons=Qt.NoButton);self.assertFalse(self.c.dragging);self.assertEqual(self.w.pos(),before)
    def test_mode_switch_cancels_drag_and_updates_cursor(self):
        self.start();self.w.toggle_fullscreen();self.assertFalse(self.c.dragging);self.assertEqual(self.w.brand_label.cursor().shape(),Qt.ArrowCursor);self.w.escape();self.assertEqual(self.w.brand_label.cursor().shape(),Qt.OpenHandCursor)
    def test_drag_does_not_change_monitoring_or_size(self):
        data=copy.deepcopy(self.w.current);config=copy.deepcopy(self.w.dashboard_config);size=self.w.size();widget,p=self.start();self.event(widget,QEvent.MouseMove,global_point=p+QPoint(20,20),button=Qt.NoButton);self.assertEqual(self.w.current,data);self.assertEqual(self.w.dashboard_config,config);self.assertEqual(self.w.size(),size)
