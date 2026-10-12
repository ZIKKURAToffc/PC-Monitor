import unittest,tempfile
from unittest.mock import patch

class OriginalCompactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        import desktop
        from PySide6.QtCore import QSettings
        self.dir=tempfile.TemporaryDirectory();self.settings=QSettings(self.dir.name+'/prefs.ini',QSettings.IniFormat);self.p=patch('desktop.QSettings',return_value=self.settings);self.p.start();self.w=desktop.MonitorWindow(demo=True);self.w.show()
    def tearDown(self):self.w.close();self.p.stop();self.dir.cleanup()
    def test_default_preserves_sections_and_graphs(self):
        from PySide6.QtWidgets import QScrollArea,QBoxLayout
        self.assertTrue(self.w.compact_mode);self.assertIsInstance(self.w.tabs.widget(0),QScrollArea)
        self.w.resize(1920,1080);self.w.adapt_layout();self.app.processEvents()
        self.assertEqual(self.w.cpu.responsive_row.direction(),QBoxLayout.LeftToRight);self.assertTrue(self.w.cpu.graph.isVisible());self.assertTrue(self.w.gpu.graph.isVisible());self.assertTrue(self.w.ram_graph.isVisible());self.assertEqual(len(self.w.cpu.metrics),4)
        graph=self.w.cpu.graph;metric=self.w.cpu.metrics['cpu_clock'];self.assertLess(graph.mapTo(self.w,graph.rect().topRight()).x(),metric.mapTo(self.w,metric.rect().topLeft()).x())
    def test_whole_original_overview_fits(self):
        self.w.dashboard_config={'slots':{},'custom':[{'sensor':'demo/fan/0','label':'Корпус','unit':'RPM'},{'sensor':'demo/9','label':'SSD','unit':'°C'}]};self.w.rebuild_custom_cards()
        for width,height in [(1920,1080),(1366,768)]:
            self.w.resize(width,height);self.w.adapt_layout();self.w.refresh();self.app.processEvents();self.app.processEvents()
            self.assertEqual(self.w.overview_scroll.verticalScrollBar().maximum(),0)
            viewport=self.w.overview_scroll.viewport()
            for _,card in self.w.custom_widgets:
                self.assertTrue(viewport.rect().contains(card.mapTo(viewport,card.rect().bottomRight())))
    def test_density_and_preference(self):
        self.assertLess(self.w.cpu.metrics['cpu_clock'].minimumHeight(),85)
        self.w.compact_button.setChecked(False);self.w.toggle_compact();self.assertEqual(self.w.cpu.metrics['cpu_clock'].minimumHeight(),85);self.assertFalse(self.settings.value('compact_original'))
        self.w.compact_button.setChecked(True);self.w.toggle_compact();self.assertTrue(self.settings.value('compact_original'))
    def test_alert_color_survives_resize_on_pause(self):
        from desktop import RED
        self.w.thermal_metrics['cpu_temp'].update_value(100,1,True);self.w.paused=True;self.w.resize(1366,768);self.w.adapt_layout();self.assertIn(RED,self.w.thermal_metrics['cpu_temp'].value.styleSheet())
    def test_full_height_without_custom_cards(self):
        self.w.resize(1920,1080);self.w.adapt_layout();self.w.refresh();self.app.processEvents();self.app.processEvents()
        viewport=self.w.overview_scroll.viewport();bottom=self.w.download.mapTo(viewport,self.w.download.rect().bottomRight()).y()
        self.assertEqual(self.w.overview_scroll.verticalScrollBar().maximum(),0)
        self.assertLessEqual(viewport.height()-1-bottom,8)
        self.assertGreaterEqual(self.w.cpu.graph.height(),170);self.assertGreaterEqual(self.w.gpu.graph.height(),170);self.assertGreaterEqual(self.w.ram_graph.height(),170)
    def test_graphs_grow_with_window_height(self):
        self.w.resize(1366,768);self.w.adapt_layout();self.w.refresh();self.app.processEvents();self.app.processEvents()
        small=[g.height() for g in self.w.graphs.values()]
        self.w.resize(1366,1080);self.w.adapt_layout();self.w.refresh();self.app.processEvents();self.app.processEvents()
        large=[g.height() for g in self.w.graphs.values()]
        self.assertTrue(all(b>a for a,b in zip(small,large)))
