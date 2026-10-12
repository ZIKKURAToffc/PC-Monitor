"""Read-only RTSS v2 application metadata. No injection, hooks or OSD writes.

Layout reference: RTSSSharedMemoryNET/RTSSSharedMemory.h (v2 prefix).
The RTSS application table is independent of AIDA64's aggregate FPS export.
"""
import ctypes,os,struct,time,copy
from aida_bridge import MemoryInfo64
SIGNATURE=0x52545353
MAX_BYTES=8*1024*1024
MAX_APPS=4096
HEADER_SIZE=36
ENTRY_PREFIX=284
MAX_AGE_MS=5000

def layout(raw):
    if len(raw)<HEADER_SIZE:raise ValueError('RTSS header truncated')
    signature,version,size,offset,count=struct.unpack_from('<5I',raw)
    if signature!=SIGNATURE:raise ValueError('RTSS memory not initialized')
    if version>>16!=2:raise ValueError('Unsupported RTSS memory version')
    if not ENTRY_PREFIX<=size<=65536 or not HEADER_SIZE<=offset<=MAX_BYTES or count>MAX_APPS:
        raise ValueError('Invalid RTSS application layout')
    end=offset+count*size
    if end>MAX_BYTES:raise ValueError('RTSS application table too large')
    return version,size,offset,count,end

def parse_applications(raw,now_ms):
    version,size,offset,count,end=layout(raw)
    if end>len(raw):raise ValueError('RTSS application table truncated')
    apps=[]
    for i in range(count):
        pos=offset+i*size;pid=struct.unpack_from('<I',raw,pos)[0]
        if not pid:continue
        name_bytes=raw[pos+4:pos+264]
        if b'\0' not in name_bytes:continue
        name_bytes=name_bytes.split(b'\0',1)[0]
        try:name=name_bytes.decode('utf-8')
        except UnicodeDecodeError:name=name_bytes.decode('mbcs' if os.name=='nt' else 'cp1252',errors='replace')
        name=name.replace('\\','/').rsplit('/',1)[-1]
        name=''.join(c for c in name if c.isprintable()).strip()[:260]
        if not name:continue
        time0,time1,frames,frame_time=struct.unpack_from('<4I',raw,pos+268)
        age=(int(now_ms)-time1)&0xffffffff;period=(time1-time0)&0xffffffff
        if not time0 or not time1 or age>MAX_AGE_MS or not 0<period<=60000:continue
        apps.append({'pid':pid,'name':name,'age_ms':age,'fps':round(1000*frames/period,3)})
    return {'state':'available' if apps else 'no-active-app','applications':apps,'version':version,'checked_at':time.time(),'source':'RTSSSharedMemoryV2'}

def identity_signature(raw):
    """Only PID/executable identity must stay stable, not per-frame statistics."""
    _,size,offset,count,end=layout(raw)
    if end>len(raw):raise ValueError('RTSS application table truncated')
    return (raw[:20],tuple(raw[offset+i*size:offset+i*size+264] for i in range(count)))

def read_application_report():
    if os.name!='nt':return {'state':'unsupported','applications':[],'checked_at':time.time()}
    handle=None;address=None
    try:
        if ctypes.sizeof(ctypes.c_void_p)!=8:raise RuntimeError('64-bit RTSS reader required')
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.OpenFileMappingW.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_wchar_p];k.OpenFileMappingW.restype=ctypes.c_void_p
        k.MapViewOfFile.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_size_t];k.MapViewOfFile.restype=ctypes.c_void_p
        k.VirtualQuery.argtypes=[ctypes.c_void_p,ctypes.POINTER(MemoryInfo64),ctypes.c_size_t];k.VirtualQuery.restype=ctypes.c_size_t
        k.UnmapViewOfFile.argtypes=[ctypes.c_void_p];k.UnmapViewOfFile.restype=ctypes.c_int
        k.CloseHandle.argtypes=[ctypes.c_void_p];k.CloseHandle.restype=ctypes.c_int
        k.GetTickCount.argtypes=[];k.GetTickCount.restype=ctypes.c_uint32
        handle=k.OpenFileMappingW(0x0004,False,'RTSSSharedMemoryV2')
        if not handle:raise OSError(ctypes.get_last_error(),'RTSS mapping unavailable')
        address=k.MapViewOfFile(handle,0x0004,0,0,0)
        if not address:raise OSError(ctypes.get_last_error(),'RTSS mapping unreadable')
        info=MemoryInfo64()
        if not k.VirtualQuery(address,ctypes.byref(info),ctypes.sizeof(info)) or info.State!=0x1000 or info.Protect&0x101 or info.RegionSize<HEADER_SIZE:
            raise RuntimeError('RTSS mapping region unavailable')
        for attempt in range(3):
            header=ctypes.string_at(address,HEADER_SIZE);_,_,_,_,end=layout(header)
            if end>info.RegionSize:raise ValueError('RTSS table exceeds mapped region')
            raw=ctypes.string_at(address,end)
            if raw[:20]!=header[:20]:continue
            check=ctypes.string_at(address,end)
            # Counters and frame times change continuously; they cannot invalidate a name.
            if check[:20]!=header[:20]:continue
            if identity_signature(raw)!=identity_signature(check):continue
            final_header=ctypes.string_at(address,HEADER_SIZE)
            if final_header[:20]!=header[:20]:continue
            report=parse_applications(check,k.GetTickCount());report['read_attempts']=attempt+1
            return report
        raise RuntimeError('RTSS identity changed during read')
    except Exception as e:
        return {'state':'unavailable','applications':[],'checked_at':time.time(),'error':type(e).__name__}
    finally:
        if address:k.UnmapViewOfFile(address)
        if handle:k.CloseHandle(handle)

class ApplicationReader:
    """Bounded last-good identity grace for transient read failures only."""
    def __init__(self,read=None,clock=None):
        self.read=read or read_application_report;self.clock=clock or time.monotonic
        self.last_good=None;self.last_good_at=None
    def poll(self):
        report=self.read();now=self.clock()
        if report.get('state')=='available' and report.get('applications'):
            self.last_good=copy.deepcopy(report);self.last_good_at=now;return report
        if report.get('state')=='unavailable' and self.last_good is not None:
            age=now-self.last_good_at
            if 0<=age<=3:
                cached=copy.deepcopy(self.last_good);cached.update(state='cached',cached=True,cached_for_seconds=round(age,2),read_error=report.get('error','unavailable'))
                return cached
        # Explicit empty table, unsupported platform, or extended failure: clear immediately.
        self.last_good=None;self.last_good_at=None
        return report
