import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from telemetry import Collector,finite,normalize_temperatures,temperature_summary
from desktop import MonitorWindow,STYLE

APP=QApplication.instance() or QApplication([])
APP.setStyle('Fusion');APP.setStyleSheet(STYLE)

class SensorTests(unittest.TestCase):
    def rows(self):
        return [dict(Identifier='/intelcpu/0/temperature/0',Parent='/intelcpu/0',SensorType='Temperature',Name='CPU Package',Value=47),
                dict(Identifier='/intelcpu/0/temperature/1',Parent='/intelcpu/0',SensorType='Temperature',Name='CPU Core #1',Value=43),
                dict(Identifier='/intelcpu/0/temperature/2',Parent='/intelcpu/0',SensorType='Temperature',Name='CPU Core #2',Value=45),
                dict(Identifier='/intelcpu/0/temperature/3',SensorType='Temperature',Name='Distance to TjMax',Value=52),
                dict(Identifier='/gpu-nvidia/0/temperature/0',SensorType='Temperature',Name='GPU Core',Value=0),
                dict(Identifier='/gpu-nvidia/0/temperature/1',SensorType='Temperature',Name='GPU Hot Spot',Value=42),
                dict(Identifier='/nvme/0/temperature/0',SensorType='Temperature',Name='Composite',Value=38),
                dict(Identifier='/lpc/chip/temperature/0',SensorType='Temperature',Name='System',Value=29),
                dict(Identifier='/lpc/chip/temperature/1',SensorType='Temperature',Name='Temperature #2',Value='NaN')]
    def test_valid_temperatures_and_devices(self):
        temps=normalize_temperatures(self.rows(),[dict(Identifier='/intelcpu/0',Name='My CPU')])
        self.assertEqual(len(temps),7);self.assertEqual(temps[0]['device'],'My CPU')
        s=temperature_summary(temps);self.assertEqual(s['cpu_temp'],47);self.assertEqual(s['cpu_core_max'],45)
        self.assertEqual(s['gpu_temp'],0);self.assertEqual(s['gpu_hotspot'],42);self.assertEqual(s['disk_temp'],38);self.assertEqual(s['sys_temp'],29)
        self.assertIsNone(s['gpu_mem_temp'])
    def test_missing_not_zero(self):
        self.assertTrue(all(v is None for v in temperature_summary([]).values()))
        self.assertIsNone(finite(float('inf')))
    def test_hardware_without_lhm(self):
        c=Collector();c.nv=None
        with patch.object(c,'_lhm',return_value=([],[],'not connected')),patch('telemetry.psutil.sensors_temperatures',return_value={},create=True):
            d=c._hardware_once()
        self.assertEqual(d['temperatures'],[]);self.assertIsNone(d['cpu_temp']);self.assertIsNone(d['gpu_temp'])
    def test_hardware_lhm_and_nvidia(self):
        c=Collector();c.nv='nvidia-smi'
        with patch.object(c,'_lhm',return_value=(self.rows(),[],'LHM')),patch('telemetry.command',return_value='NVIDIA Card, 12, 37, 28.1, 2587, 1843.2, 12288\n'),patch('telemetry.psutil.sensors_temperatures',return_value={},create=True):
            d=c._hardware_once()
        self.assertEqual(d['cpu_temp'],47);self.assertEqual(d['gpu_temp'],37);self.assertEqual(d['gpu_hotspot'],42)
        self.assertAlmostEqual(d['vram_used'],1.8);self.assertEqual(d['vram_total'],12)
        json.dumps(d,allow_nan=False)
    def test_real_cpu_ram(self):
        c=Collector();c.start()
        try:
            time.sleep(1.3);d=c.snapshot();self.assertGreater(d['ram_total'],0);self.assertTrue(0<=d['cpu_usage']<=100)
        finally:c.close()

class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.w=MonitorWindow(demo=True);self.w.resize(1180,1000);self.w.show();APP.processEvents()
    def tearDown(self):self.w.close();APP.processEvents()
    def test_native_window_and_pause(self):
        self.assertEqual(self.w.tabs.count(),3);self.assertEqual(self.w.table.rowCount(),10)
        self.w.toggle_pause();self.assertTrue(self.w.paused);snapshot=self.w.current;self.w.refresh();self.assertIs(self.w.current,snapshot)
        self.w.toggle_pause();self.assertFalse(self.w.paused)
        self.assertTrue(any(v is None for t,v in self.w.cpu.graph.points))
    def test_filters_peaks_and_threshold(self):
        self.w.group_filter.setCurrentText('CPU');self.assertEqual(self.w.table.rowCount(),5)
        self.w.threshold=44;self.w.update_thermal();self.assertIn('Выше порога: 3',self.w.sensor_count.text())
        self.assertEqual(self.w.peaks['demo/0'],47)
    def test_export_json(self):
        with tempfile.TemporaryDirectory() as td:
            name=str(Path(td)/'metrics.json')
            with patch('desktop.QFileDialog.getSaveFileName',return_value=(name,'JSON')):self.w.export_json()
            data=json.loads(Path(name).read_text());self.assertEqual(data['mode'],'synthetic-demo');self.assertEqual(len(data['metrics']['temperatures']),10)
    def test_absent_sensors(self):
        self.w.tabs.setCurrentIndex(1);self.w.current={'temperatures':[]};self.w.update_thermal();self.assertEqual(self.w.table.rowCount(),0);self.assertTrue(self.w.empty_message.isVisible());self.assertEqual(self.w.thermal_metrics['cpu_temp'].value.text(),'—')

if __name__=='__main__':unittest.main()
