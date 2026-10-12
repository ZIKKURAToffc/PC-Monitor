"""Read-only AIDA64 Extreme 8.00 shared-memory adapter, Windows x64.

Protocol: NUL-terminated XML fragments in AIDA64_SensorValues.
No AIDA binaries, registry writes, sensor control, or licence modification.
"""
import ctypes
import math
import os
import re
import xml.etree.ElementTree as ET
from lhm_bridge import raw_sensor_value

MAX_BYTES=1024*1024
FILE_MAP_READ=0x0004
MAPPING_NAMES=('AIDA64_SensorValues',r'Global\AIDA64_SensorValues')

class MemoryInfo64(ctypes.Structure):
    _fields_=[('BaseAddress',ctypes.c_void_p),('AllocationBase',ctypes.c_void_p),
              ('AllocationProtect',ctypes.c_uint32),('_partition_and_padding',ctypes.c_uint32),
              ('RegionSize',ctypes.c_size_t),('State',ctypes.c_uint32),('Protect',ctypes.c_uint32),
              ('Type',ctypes.c_uint32),('_padding',ctypes.c_uint32)]

def read_shared_buffer():
    if os.name!='nt':raise RuntimeError('AIDA64 Shared Memory доступна только на Windows.')
    if ctypes.sizeof(ctypes.c_void_p)!=8:raise RuntimeError('Нужен 64-битный Python/EXE для этой сборки.')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenFileMappingW.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_wchar_p];k.OpenFileMappingW.restype=ctypes.c_void_p
    k.MapViewOfFile.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_size_t];k.MapViewOfFile.restype=ctypes.c_void_p
    k.VirtualQuery.argtypes=[ctypes.c_void_p,ctypes.POINTER(MemoryInfo64),ctypes.c_size_t];k.VirtualQuery.restype=ctypes.c_size_t
    k.UnmapViewOfFile.argtypes=[ctypes.c_void_p];k.UnmapViewOfFile.restype=ctypes.c_int
    k.CloseHandle.argtypes=[ctypes.c_void_p];k.CloseHandle.restype=ctypes.c_int
    errors=[]
    for name in MAPPING_NAMES:
        handle=k.OpenFileMappingW(FILE_MAP_READ,False,name)
        if not handle:
            errors.append(ctypes.get_last_error());continue
        address=None
        try:
            address=k.MapViewOfFile(handle,FILE_MAP_READ,0,0,0)
            if not address:raise OSError(ctypes.get_last_error(),'MapViewOfFile: не удалось прочитать AIDA64 Shared Memory.')
            info=MemoryInfo64()
            if not k.VirtualQuery(address,ctypes.byref(info),ctypes.sizeof(info)):
                raise OSError(ctypes.get_last_error(),'VirtualQuery: не удалось проверить размер буфера AIDA64.')
            if info.State!=0x1000 or info.Protect&0x101:raise RuntimeError('Область памяти AIDA64 недоступна для безопасного чтения.')
            size=int(info.RegionSize)
            if size<=0:raise RuntimeError('Пустая область AIDA64 Shared Memory.')
            raw=ctypes.string_at(address,min(size,MAX_BYTES))
            if not raw:raise RuntimeError('AIDA64 ещё не опубликовала данные.')
            return raw,{'mapping':name,'mapped_bytes':size,'read_bytes':len(raw),'transport':'AIDA64 Shared Memory'}
        finally:
            if address:k.UnmapViewOfFile(address)
            k.CloseHandle(handle)
    if 5 in errors:
        raise PermissionError('Shared Memory: доступ запрещён. Запустите AIDA64 и монитор под одним пользователем; проверьте совместимость уровней прав, не отключая защиту ОС.')
    raise RuntimeError('AIDA64_SensorValues не найдена. Запустите AIDA64 Extreme 8.00.8000 и включите Preferences > Hardware Monitoring > External Applications > Enable shared memory.')

def decode_buffer(raw):
    if isinstance(raw,str):return raw.split('\0',1)[0].lstrip('\ufeff')
    if not isinstance(raw,(bytes,bytearray)):raise ValueError('Неверный тип буфера AIDA64.')
    raw=bytes(raw)
    if len(raw)>MAX_BYTES:raise ValueError('Дамп AIDA64 превышает лимит 1 MiB.')
    # Documented char* format; also accept a UTF-16 dump for diagnostics.
    utf16=raw.startswith((b'\xff\xfe',b'\xfe\xff')) or raw.startswith(b'<\0')
    if utf16:
        start=2 if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 0
        encoding='utf-16-be' if raw.startswith(b'\xfe\xff') else 'utf-16-le'
        end=next((i for i in range(start,len(raw)-1,2) if raw[i:i+2]==b'\0\0'),len(raw))
        return raw[start:end].decode(encoding).lstrip('\ufeff')
    payload=raw.split(b'\0',1)[0]
    try:return payload.decode('utf-8-sig')
    except UnicodeDecodeError:
        try:return payload.decode('mbcs')
        except (LookupError,UnicodeDecodeError):return payload.decode('cp1252',errors='replace')

def classify(sid,label,tag):
    """Canonical units/roles from documented sensor IDs, not label guessing."""
    typ=None;name=label or sid;parent='/aida/other/0'
    if sid.startswith('T') or tag=='temp':typ='Temperature'
    elif sid.startswith('F') or tag=='fan':typ='Fan'
    elif sid.startswith('D') or tag=='duty':typ='Control'
    elif sid.startswith('V') or tag=='volt':typ='Voltage'
    elif sid.startswith('C') or tag=='curr':typ='Current'
    elif sid.startswith('P') or tag in ['pwr','power']:typ='Power'
    if sid.startswith('D') or re.fullmatch(r'PGPU\d+TDPP',sid):typ='Control'
    if sid=='SCPUCLK':typ='Clock';name='CPU Clock';parent='/aida/cpu/0'
    m=re.fullmatch(r'SCC-(\d+)-(\d+)',sid)
    if m:typ='Clock';parent=f'/aida/cpu/{int(m[1])-1}';name=f'CPU Core #{int(m[2])}'
    if sid in ['SCPUUTI','SCPU1UTI']:typ='Load';name='CPU Total';parent='/aida/cpu/0'
    m=re.fullmatch(r'SGPU(\d+)(CLK|MEMCLK|SHDCLK|UTI|MCUTI|VEUTI|BIUTI)',sid)
    if m:
        parent=f'/aida/gpu/{int(m[1])-1}';kind=m[2];typ='Clock' if kind.endswith('CLK') else 'Load'
        name={'CLK':'GPU Core','MEMCLK':'GPU Memory','SHDCLK':'GPU Shader','UTI':'GPU Core','MCUTI':'GPU Memory Controller','VEUTI':'GPU Video Engine','BIUTI':'GPU Bus'}[kind]
    if sid=='SRTSSFPS':typ='FPS';name='RTSS FPS';parent='/aida/application/0'
    if re.fullmatch(r'SCPU\d+UTI',sid):typ='Load';name=label or sid;parent='/aida/cpu/0'
    if sid in ['SMEMUTI','SVIRTMEMUTI','SVMEMUSAGE']:typ='Load';parent='/aida/system/0'
    if typ is None and tag=='sys':typ='System';parent='/aida/system/0'
    if typ is None:return None
    m=re.match(r'^[TPFD]GPU(\d+)',sid)
    if m:
        index=int(m[1])-1;parent=f'/aida/gpu/{index}';suffix=sid[m.end():]
        if typ=='Temperature':
            name={'':'GPU Core','DIO':'GPU Core (Diode)','HOT':'GPU Hotspot','MEM':'GPU Memory'}.get(suffix,label or sid)
        elif typ=='Fan':name='GPU Fan' if not suffix else label or sid
        elif typ=='Power':name='GPU Package' if not suffix else label or sid
    elif re.match(r'^[TPFD]CPU',sid):
        match=re.match(r'^[TPFD]CPU([1-4])',sid);index=int(match[1])-1 if match else 0;parent=f'/aida/cpu/{index}'
        known={'TCPU':'CPU','TCPUPKG':'CPU Package','TCPUTCTL':'CPU Tctl','TCPUDIO':'CPU Diode','TCPUSOCK':'CPU Socket',
               'PCPU':'CPU Total','PCPUPKG':'CPU Package','PCPUIAC':'CPU IA Cores','PCPUGTC':'CPU GT Cores',
               'FCPU':'CPU Fan','FCPUOPT':'CPU OPT Fan','DCPU':'CPU Fan PWM'}
        name=known.get(sid,label or sid)
    m=re.fullmatch(r'TCC-(\d+)-(\d+)',sid)
    if m:parent=f'/aida/cpu/{int(m[1])-1}';name=f'CPU Core #{int(m[2])}'
    if re.fullmatch(r'TCCD\d+',sid):parent='/aida/cpu/0';name=label or sid
    m=re.fullmatch(r'THDD(\d+)(TS\d+)?',sid)
    if m:parent=f'/aida/storage/{int(m[1])-1}';name='Drive Temperature' if not m[2] else 'Drive Temperature '+m[2]
    if typ in ['Temperature','Fan','Control','Voltage','Current','Power'] and parent=='/aida/other/0':parent='/aida/lpc/0'
    if sid=='TMOBO':name='Motherboard';parent='/aida/lpc/0'
    unit={'Temperature':'°C','Fan':'RPM','Power':'W','Clock':'MHz','Load':'%','Control':'%','Voltage':'V','Current':'A','FPS':'FPS','System':''}[typ]
    return typ,name,parent,unit

def parse_shared_memory(raw):
    text=decode_buffer(raw).strip()
    if not text:raise ValueError('AIDA64 Shared Memory пуста. Подождите и проверьте список экспортируемых датчиков.')
    if len(text)>MAX_BYTES:raise ValueError('Слишком большой XML AIDA64.')
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b',text,re.I):raise ValueError('DTD/ENTITY в XML AIDA64 запрещены.')
    text=re.sub(r'^\s*<\?xml[^?]*\?>','',text,count=1)
    try:root=ET.fromstring('<aida_root>'+text+'</aida_root>')
    except ET.ParseError as e:raise ValueError('Некорректный XML AIDA64; возможно, буфер обновлялся во время чтения. Повторите опрос. '+str(e)) from e
    rows={};devices={}
    for node in root.iter():
        fields={child.tag.rsplit('}',1)[-1].lower():(child.text or '').strip() for child in node}
        sid=fields.get('id','').upper();label=fields.get('label','');value=fields.get('value','')
        if not re.fullmatch(r'[A-Z0-9_-]{1,80}',sid):continue
        spec=classify(sid,label,node.tag.rsplit('}',1)[-1].lower())
        if spec is None:continue
        typ,name,parent,unit=spec
        numeric=raw_sensor_value(value,typ)
        if typ=='FPS' and numeric is None:numeric=raw_sensor_value(re.sub(r'\s*FPS\s*$','',value,flags=re.I),typ)
        # The shared-memory values are normally unitless canonical numbers.
        if typ in ['Voltage','Current'] and numeric is None:
            clean=re.sub(r'\s*[VA]\s*$','',value,flags=re.I).replace(',','.')
            try:numeric=float(clean);numeric=numeric if math.isfinite(numeric) else None
            except ValueError:pass
        identifier=parent+'/'+typ.lower()+'/'+sid
        display=name if not label or label.casefold()==name.casefold() else name+' ['+label+']'
        rows[sid]={'Identifier':identifier,'Parent':parent,'Name':name,'DisplayName':display,'SensorType':typ,
                   'Value':numeric,'TextValue':value,'Source':'AIDA64 Shared Memory','AidaId':sid,'Unit':unit,'OriginalLabel':label}
        if parent.startswith('/aida/storage/'):
            device=label or 'Накопитель #'+str(int(parent.rsplit('/',1)[1])+1)+' / AIDA64'
            if parent not in devices:devices[parent]=device
        elif parent.startswith('/aida/cpu/'):devices[parent]='CPU #'+str(int(parent.rsplit('/',1)[1])+1)+' / AIDA64'
        elif parent.startswith('/aida/gpu/'):devices[parent]='GPU #'+str(int(parent.rsplit('/',1)[1])+1)+' / AIDA64'
        else:devices[parent]='Плата / AIDA64'
    if not rows:raise ValueError('В AIDA64 Shared Memory нет поддерживаемых датчиков. Отметьте температуры, кулеры, мощность и System/CPU Clock в External Applications.')
    return list(rows.values()),[{'Identifier':k,'Name':v} for k,v in devices.items()]

def read_aida64():
    raw,info=read_shared_buffer()
    rows,devices=parse_shared_memory(raw)
    return rows,devices,{**info,'sensor_count':len(rows),'hardware_count':len(devices),'target':'AIDA64 Extreme 8.00.8000 (версия не определяется по XML)'}
