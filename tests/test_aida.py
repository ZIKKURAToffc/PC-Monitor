import ctypes
import unittest
from unittest.mock import patch,MagicMock
import aida_bridge as ab
from telemetry import Collector,normalize_temperatures,temperature_summary

def fixture(clock='4200',temp='52.5',fan='1300',power='75'):
    items=[('sys','SCPUCLK','CPU Clock',clock),('temp','TCPUPKG','CPU Package',temp),('temp','TCC-1-1','CPU Core 1','50'),('temp','TMOBO','Motherboard','32'),('temp','TGPU1','GPU Diode','40'),('temp','TGPU1HOT','GPU Hotspot','47'),('temp','TGPU1MEM','GPU Memory','44'),('temp','THDD1','SSD Test','38'),('fan','FCPU','CPU Fan',fan),('pwr','PCPUPKG','CPU Package',power),('fan','FGPU1','GPU Fan','0'),('pwr','PGPU1','GPU Power','30'),('pwr','PGPU1TDPP','GPU TDP','20'),('duty','DCPU','CPU PWM','45'),('sys','SGPU1CLK','GPU Clock','2000'),('sys','SGPU1UTI','GPU Utilization','5')]
    return ''.join(f'<{tag}><id>{sid}</id><label>{label}</label><value>{val}</value></{tag}>' for tag,sid,label,val in items)

class AidaTests(unittest.TestCase):
    def test_parse_and_units(self):
        rows,devices=ab.parse_shared_memory(fixture());r={r['AidaId']:r for r in rows}
        self.assertEqual(len(rows),16);self.assertEqual(r['FCPU']['Value'],1300);self.assertEqual(r['FGPU1']['Value'],0)
        self.assertEqual(r['PGPU1TDPP']['Unit'],'%');self.assertEqual(r['DCPU']['SensorType'],'Control')
        s=temperature_summary(normalize_temperatures(rows,devices));self.assertEqual(s['cpu_temp'],52.5);self.assertEqual(s['cpu_core_max'],50);self.assertEqual(s['sys_temp'],32);self.assertEqual(s['gpu_hotspot'],47);self.assertEqual(s['disk_temp'],38)
    def test_missing_and_localized(self):
        rows,_=ab.parse_shared_memory(fixture(clock='4 200 MHz',temp='52,5 °C',fan='N/A',power='TRIAL'))
        r={r['AidaId']:r for r in rows};self.assertEqual(r['SCPUCLK']['Value'],4200);self.assertEqual(r['TCPUPKG']['Value'],52.5);self.assertIsNone(r['FCPU']['Value']);self.assertIsNone(r['PCPUPKG']['Value'])
    def test_buffers(self):
        s=fixture();self.assertEqual(ab.decode_buffer(s.encode()+b'\0JUNK'),s);self.assertEqual(ab.decode_buffer(s.encode('utf-16-le')+b'\0\0'),s)
        rows,_=ab.parse_shared_memory(s.replace('SSD Test','SSD &amp; Test'));self.assertTrue(any(r['OriginalLabel']=='SSD & Test' for r in rows))
    def test_reject(self):
        for raw in ['', '<!DOCTYPE a [<!ENTITY x "x">]>', '<sys>']:
            with self.assertRaises(ValueError):ab.parse_shared_memory(raw)
    def test_duty_override(self):
        self.assertEqual(ab.classify('DCPU','CPU Fan','fan')[0],'Control')
    def test_two_polls_and_no_http(self):
        c=Collector();c.nv=None;c.configure('aida')
        def poll(data):
            rows,dev=ab.parse_shared_memory(data)
            with patch('telemetry.read_aida64',return_value=(rows,dev,{})),patch('telemetry.read_http') as http:
                snap=c._hardware_once();http.assert_not_called();return snap
        a=poll(fixture());b=poll(fixture('4500','61','1700','110'))
        self.assertEqual(a['cpu_clock'],4200);self.assertEqual(b['cpu_clock'],4500);self.assertEqual(b['cpu_temp'],61);self.assertEqual(b['cpu_rpm'],1700);self.assertEqual(b['cpu_power'],110);self.assertEqual(b['cpu_clock_source'],'AIDA64')
    def test_nvidia_only_fills_missing(self):
        c=Collector();c.nv='nvidia';c.configure('aida');rows,dev=ab.parse_shared_memory(fixture())
        with patch('telemetry.read_aida64',return_value=(rows,dev,{})),patch('telemetry.command',return_value='Test GPU, 90, 80, 100, 1000, 2048, 8192'):
            h=c._hardware_once()
        self.assertEqual(h['gpu_temp'],40);self.assertEqual(h['gpu_clock'],2000);self.assertEqual(h['gpu_power'],30);self.assertEqual(h['vram_used'],2)
    def test_failed_aida_no_lhm_fallback(self):
        c=Collector();c.configure('aida')
        with patch('telemetry.read_aida64',side_effect=RuntimeError('not found')),patch('telemetry.read_http') as http:
            rows,_,_=c._lhm();http.assert_not_called()
        self.assertEqual(rows,[]);self.assertFalse(c.diagnostics['connected'])
    def test_win64_readonly_cleanup(self):
        raw=fixture().encode()+b'\0';buf=ctypes.create_string_buffer(raw);address=ctypes.addressof(buf);handle=2**40+1;k=MagicMock();k.OpenFileMappingW.return_value=handle;k.MapViewOfFile.return_value=address
        def query(addr,ptr,size):
            info=ctypes.cast(ptr,ctypes.POINTER(ab.MemoryInfo64)).contents;info.RegionSize=len(buf);info.State=0x1000;info.Protect=2;return size
        k.VirtualQuery.side_effect=query
        with patch.object(ab.os,'name','nt'),patch.object(ab.ctypes,'WinDLL',return_value=k,create=True):
            got,meta=ab.read_shared_buffer()
        self.assertEqual(ab.decode_buffer(got),fixture());self.assertEqual(ctypes.sizeof(ab.MemoryInfo64),48)
        k.OpenFileMappingW.assert_called_once_with(ab.FILE_MAP_READ,False,'AIDA64_SensorValues');k.UnmapViewOfFile.assert_called_once_with(address);k.CloseHandle.assert_called_once_with(handle)
    def test_win64_cleanup_error(self):
        k=MagicMock();k.OpenFileMappingW.return_value=2**40;k.MapViewOfFile.return_value=2**41;k.VirtualQuery.return_value=0
        with patch.object(ab.os,'name','nt'),patch.object(ab.ctypes,'WinDLL',return_value=k,create=True),patch.object(ab.ctypes,'get_last_error',return_value=5,create=True):
            with self.assertRaises(OSError):ab.read_shared_buffer()
        k.UnmapViewOfFile.assert_called_once_with(2**41);k.CloseHandle.assert_called_once_with(2**40)
    def test_not_windows(self):
        with patch.object(ab.os,'name','posix'):
            with self.assertRaises(RuntimeError):ab.read_shared_buffer()

if __name__=='__main__':unittest.main()
