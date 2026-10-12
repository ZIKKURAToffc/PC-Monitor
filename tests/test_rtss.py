import struct,time,unittest,tempfile
from unittest.mock import patch
from rtss_bridge import parse_applications,SIGNATURE,read_application_report
from fps_diagnostics import inspect_fps

def buffer(apps,version=0x20014,size=300,offset=64):
    raw=bytearray(offset+len(apps)*size);struct.pack_into('<5I',raw,0,SIGNATURE,version,size,offset,len(apps))
    for i,(pid,name,start,end,frames) in enumerate(apps):
        p=offset+i*size;struct.pack_into('<I',raw,p,pid);n=name.encode()[:259];raw[p+4:p+4+len(n)]=n;struct.pack_into('<4I',raw,p+268,start,end,frames,10000)
    return bytes(raw)
class RtssParserTests(unittest.TestCase):
    def test_executable_basename_and_fps(self):
        d=parse_applications(buffer([(123,r'C:\Games\Game.exe',9000,10000,144)]),10100)
        self.assertEqual(d['applications'][0]['name'],'Game.exe');self.assertEqual(d['applications'][0]['fps'],144);self.assertEqual(d['applications'][0]['pid'],123)
    def test_recent_zero_is_valid(self):
        self.assertEqual(parse_applications(buffer([(123,'Game.exe',9000,10000,0)]),10100)['applications'][0]['fps'],0)
    def test_inactive_stale_and_uninitialized_excluded(self):
        raw=buffer([(0,'Unused.exe',9000,10000,1),(1,'Old.exe',1,1000,5),(2,'Uninitialized.exe',0,10000,5)])
        self.assertEqual(parse_applications(raw,11000)['applications'],[])
    def test_wraparound(self):
        d=parse_applications(buffer([(1,'Game.exe',0xffffff00,100,30)]),200)
        self.assertEqual(len(d['applications']),1);self.assertEqual(d['applications'][0]['age_ms'],100)
    def test_invalid_signature_version_bounds_and_short_buffers(self):
        good=buffer([(1,'Game.exe',9000,10000,5)])
        for field,value in [(0,0xDEAD),(4,0x30000),(8,100),(12,0),(16,100000)]:
            raw=bytearray(good);struct.pack_into('<I',raw,field,value)
            with self.assertRaises(ValueError):parse_applications(raw,10100)
        for raw in [b'',good[:20],good[:-1]]:
            with self.assertRaises(ValueError):parse_applications(raw,10100)
    def test_unterminated_name_not_published(self):
        raw=bytearray(buffer([(1,'Game.exe',9000,10000,5)]));raw[68:328]=b'X'*260
        self.assertEqual(parse_applications(raw,10100)['applications'],[])
    def test_unavailable_platform_returns_unknown_not_fake_name(self):
        with patch('rtss_bridge.os.name','posix'):self.assertEqual(read_application_report()['applications'],[])
class RtssReaderTests(unittest.TestCase):
    def kernel(self,raw):
        import ctypes
        from types import SimpleNamespace
        from unittest.mock import Mock
        storage=ctypes.create_string_buffer(raw)
        def query(address,info,size):
            info._obj.RegionSize=len(raw);info._obj.State=0x1000;info._obj.Protect=4;return size
        k=SimpleNamespace(OpenFileMappingW=Mock(return_value=123),MapViewOfFile=Mock(return_value=ctypes.addressof(storage)),VirtualQuery=Mock(side_effect=query),UnmapViewOfFile=Mock(return_value=1),CloseHandle=Mock(return_value=1),GetTickCount=Mock(return_value=10100))
        return k,storage
    def test_windows_reader_read_only_and_closes_handles(self):
        k,storage=self.kernel(buffer([(123,'Game.exe',9000,10000,144)]))
        with patch('rtss_bridge.os.name','nt'),patch('ctypes.WinDLL',return_value=k,create=True):
            d=read_application_report()
        self.assertEqual(d['applications'][0]['name'],'Game.exe');k.OpenFileMappingW.assert_called_once_with(4,False,'RTSSSharedMemoryV2');k.MapViewOfFile.assert_called_once_with(123,4,0,0,0);k.UnmapViewOfFile.assert_called_once();k.CloseHandle.assert_called_once_with(123)
    def test_invalid_windows_layout_still_unmaps_and_closes(self):
        raw=bytearray(buffer([(123,'Game.exe',9000,10000,144)]));struct.pack_into('<I',raw,0,0xDEAD);k,storage=self.kernel(bytes(raw))
        with patch('rtss_bridge.os.name','nt'),patch('ctypes.WinDLL',return_value=k,create=True):d=read_application_report()
        self.assertEqual(d['state'],'unavailable');self.assertEqual(d['applications'],[]);k.UnmapViewOfFile.assert_called_once();k.CloseHandle.assert_called_once_with(123)

class RtssFpsTests(unittest.TestCase):
    def snapshot(self,apps):
        return {'fps':144,'fps_source':'AIDA64 / RTSS','rtss_applications':{'checked_at':100,'applications':apps}}
    def app(self,name='Game.exe',pid=123):return {'name':name,'pid':pid,'age_ms':100,'fps':144}
    def test_single_rtss_name_does_not_claim_export_link(self):
        d=inspect_fps(self.snapshot([self.app()]),now=101);self.assertEqual(d['application']['name'],'Game.exe');self.assertEqual(d['application']['fps_link'],'unconfirmed');self.assertEqual(d['value'],144);self.assertEqual(d['game_detection'],'unknown')
    def test_multiple_no_arbitrary_pick(self):
        d=inspect_fps(self.snapshot([self.app(),self.app('Other.exe',456)]),now=101);self.assertEqual(d['application']['state'],'multiple');self.assertIsNone(d['application']['name']);self.assertEqual(len(d['application']['candidates']),2)
    def test_zero_known_app_status_does_not_deny_known_name(self):
        from fps_diagnostics import status_caption
        s=self.snapshot([self.app()]);s['fps']=0;d=inspect_fps(s,now=101)
        self.assertEqual(status_caption(d),'FPS = 0 — проверьте RTSS');self.assertEqual(d['value'],0)
    def test_stale_context_clears_name(self):
        d=inspect_fps(self.snapshot([self.app()]),now=110);self.assertIsNone(d['application']['name'])
    def test_unrelated_selected_source_not_labelled_rtss(self):
        s=self.snapshot([self.app()]);s['sensor_rows']=[{'id':'custom/fps','unit':'FPS','name':'Other FPS','type':'FPS','source':'Other'}]
        d=inspect_fps(s,{'slots':{'fps':{'sensor':'custom/fps'}}},now=101);self.assertEqual(d['application']['state'],'other-fps-source');self.assertIsNone(d['application']['name'])
class RtssQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def test_name_updates_is_plain_and_clears_on_missing(self):
        import desktop,i18n
        from PySide6.QtCore import QSettings,Qt
        with tempfile.TemporaryDirectory() as t,patch('desktop.QSettings',return_value=QSettings(t+'/p.ini',QSettings.IniFormat)):
            w=desktop.MonitorWindow(demo=True)
            try:
                d={'fps':144,'fps_source':'AIDA64 / RTSS','rtss_applications':{'checked_at':time.time(),'applications':[{'name':'<Game>.exe','pid':123,'age_ms':10}]}}
                w.update_fps_reading(d);self.assertEqual(w.fps_application.text(),'RTSS: <Game>');self.assertEqual(w.fps_application.textFormat(),Qt.PlainText);self.assertEqual(w.fps_metric.value.text(),'144')
                d['rtss_applications']['applications']=[]
                for code,expected in [('ru','Приложение FPS: не определено'),('uk','Програма FPS: не визначена'),('en','FPS application: unknown')]:
                    i18n.set_language(code);w.update_fps_reading(d);self.assertEqual(w.fps_application.text(),expected)
            finally:w.close();i18n.set_language('ru')

class RtssStabilityTests(unittest.TestCase):
    def report(self,name='Game.exe',checked=100):
        return {'state':'available','checked_at':checked,'applications':[{'pid':123,'name':name,'age_ms':100,'fps':100}]}
    def test_continuous_counters_do_not_reject_identity(self):
        raw=buffer([(123,'Game.exe',9000,10000,144)]);changed=bytearray(raw);struct.pack_into('<4I',changed,64+268,9000,10001,150,9000)
        k,storage=RtssReaderTests().kernel(raw)
        with patch('rtss_bridge.os.name','nt'),patch('ctypes.WinDLL',return_value=k,create=True),patch('rtss_bridge.ctypes.string_at',side_effect=[raw[:36],raw,bytes(changed),raw[:36]]):
            d=read_application_report()
        self.assertEqual(d['state'],'available');self.assertEqual(d['applications'][0]['name'],'Game.exe');self.assertEqual(d['read_attempts'],1)
    def test_identity_race_retries_and_uses_only_stable_new_name(self):
        raw=buffer([(123,'Game.exe',9000,10000,144)]);changed=buffer([(456,'Other.exe',9000,10000,120)]);k,storage=RtssReaderTests().kernel(raw)
        with patch('rtss_bridge.os.name','nt'),patch('ctypes.WinDLL',return_value=k,create=True),patch('rtss_bridge.ctypes.string_at',side_effect=[raw[:36],raw,changed,changed[:36],changed,changed,changed[:36]]):d=read_application_report()
        self.assertEqual(d['applications'][0]['name'],'Other.exe');self.assertEqual(d['read_attempts'],2)
    def test_repeated_identity_race_fails_closed_after_three_attempts(self):
        raw=buffer([(123,'Game.exe',9000,10000,144)]);changed=buffer([(456,'Other.exe',9000,10000,120)]);k,storage=RtssReaderTests().kernel(raw)
        with patch('rtss_bridge.os.name','nt'),patch('ctypes.WinDLL',return_value=k,create=True),patch('rtss_bridge.ctypes.string_at',side_effect=[raw[:36],raw,changed]*3):d=read_application_report()
        self.assertEqual(d['state'],'unavailable');self.assertEqual(d['applications'],[]);k.CloseHandle.assert_called_once()
    def test_transient_failure_preserves_name_with_explicit_cache_provenance(self):
        from rtss_bridge import ApplicationReader
        reader=ApplicationReader(read=lambda:self.report(),clock=lambda:0);reader.poll()
        reader.read=lambda:{'state':'unavailable','checked_at':102,'applications':[],'error':'RuntimeError'};reader.clock=lambda:2;cached=reader.poll()
        d=inspect_fps({'fps':119,'fps_source':'AIDA64 / RTSS','rtss_applications':cached},now=102)
        self.assertEqual(d['application']['name'],'Game.exe');self.assertTrue(d['application']['cached']);self.assertEqual(cached['checked_at'],100);self.assertEqual(d['value'],119)
    def test_extended_failure_clears_name_without_renewing_cache(self):
        from rtss_bridge import ApplicationReader
        reader=ApplicationReader(read=lambda:self.report(),clock=lambda:0);reader.poll();reader.read=lambda:{'state':'unavailable','applications':[]};reader.clock=lambda:4
        self.assertEqual(reader.poll()['applications'],[]);self.assertIsNone(reader.last_good)
    def test_explicit_empty_table_clears_immediately_and_new_app_replaces(self):
        from rtss_bridge import ApplicationReader
        reader=ApplicationReader(read=lambda:self.report(),clock=lambda:0);reader.poll();reader.read=lambda:{'state':'no-active-app','checked_at':101,'applications':[]};reader.clock=lambda:1
        self.assertEqual(reader.poll()['applications'],[]);reader.read=lambda:self.report('Other.exe',102);self.assertEqual(reader.poll()['applications'][0]['name'],'Other.exe')
    def test_cached_snapshot_cannot_be_shown_indefinitely_if_polling_stops(self):
        report=self.report();report.update(state='cached',cached=True)
        d=inspect_fps({'fps':119,'rtss_applications':report},now=104);self.assertIsNone(d['application']['name']);self.assertEqual(d['value'],119)

class ApplicationDisplayNameTests(unittest.TestCase):
    def test_only_terminal_exe_is_hidden(self):
        from desktop import display_application_name
        for raw,wanted in [('PathOfExile.exe','PathOfExile'),('Game.EXE','Game'),('Game.Exe','Game'),('My.Game.exe','My.Game'),('Game.exe.backup','Game.exe.backup'),('Game','Game')]:
            self.assertEqual(display_application_name(raw),wanted)
        s={'fps':100,'rtss_applications':{'checked_at':100,'applications':[{'pid':123,'name':'Game.exe','age_ms':100}]}}
        self.assertEqual(inspect_fps(s,now=101)['application']['name'],'Game.exe')
