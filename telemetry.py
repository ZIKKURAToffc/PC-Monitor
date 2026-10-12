"""Local system data and hardware sensors. No HTTP server, no cloud connection."""
import json
import math
import os
import platform
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
import psutil
from lhm_bridge import read_http, describe_error, UNITS
from aida_bridge import read_aida64
from rtss_bridge import ApplicationReader
from settings_validation import bounded_int,source_mode

GIB = 1024 ** 3

def finite(value):
    if isinstance(value,bool):return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None

def command(args, timeout=7):
    return subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace',
                          timeout=timeout, check=True, creationflags=0x08000000 if os.name == 'nt' else 0).stdout

def group_for(identifier):
    identifier = identifier.lower()
    if '/gpu' in identifier:
        return 'GPU'
    if 'cpu' in identifier and '/lpc/' not in identifier:
        return 'CPU'
    if any(s in identifier for s in ['/hdd/', '/ssd/', '/nvme/', '/storage/']):
        return 'Накопитель'
    if any(s in identifier for s in ['/lpc/', '/mainboard/', '/superio/']):
        return 'Плата'
    return 'Другое'

def is_temperature_limit(name):
    """NVMe Warning/Critical Temperature are firmware limits, NOT live readings.

    Use the explicit name, not sensor index 10/11: identifiers vary by device.
    Max/Average alone may be measured sensors and must not be discarded.
    """
    label=' '.join(str(name).casefold().split())
    return ('temperature' in label and bool(re.search(r'\b(?:warning|critical|threshold|limit|trip)\b',label)))

def normalize_temperatures(sensors, hardware=()):
    """Keep real Celsius sensors only; distance-to-TjMax is NOT a temperature."""
    devices = {h.get('Identifier'):h.get('Name') for h in hardware}
    result = []
    for s in sensors:
        val = finite(s.get('Value'))
        name = str(s.get('Name') or 'Температура')
        if s.get('SensorType') != 'Temperature' or val is None:
            continue
        if is_temperature_limit(name) or 'distance' in name.lower() or 'tjmax' in name.lower():
            continue
        identifier = str(s.get('Identifier') or '')
        parent = s.get('Parent') or identifier.rsplit('/temperature/', 1)[0]
        group = group_for(identifier)
        result.append(dict(id=identifier, group=group, device=devices.get(parent) or parent or group,
                           name=name, value=val, source=s.get('Source') or 'LHM WMI'))
    return result

def find_value(rows, group, typ, names):
    candidates = [s for s in rows if group in str(s.get('Identifier','')).lower()
                  and s.get('SensorType') == typ and finite(s.get('Value')) is not None]
    for name in names:
        for s in candidates:
            if name.casefold() in str(s.get('Name','')).casefold():
                return finite(s['Value'])
    return None

def temperature_summary(temperatures):
    def pick(group, names):
        rows=[t for t in temperatures if t['group']==group]
        for name in names:
            for t in rows:
                if name.casefold() in t['name'].casefold():
                    return t['value']
        return None
    cores=[t['value'] for t in temperatures if t['group']=='CPU' and
           (re.search(r'\bcore\s*#?\s*\d+\b',t['name'],re.I) or t['name'].strip().casefold() in ['core max','cpu core max'])]
    disks=[t['value'] for t in temperatures if t['group']=='Накопитель']
    return dict(cpu_temp=pick('CPU',['CPU Package','Tctl','Tdie','Core Average','Package','CPU']),
                cpu_core_max=max(cores) if cores else None,
                gpu_temp=pick('GPU',['GPU Core']),
                gpu_hotspot=pick('GPU',['Hot Spot','Hotspot']),
                gpu_mem_temp=pick('GPU',['Memory Junction','GPU Memory']),
                sys_temp=pick('Плата',['System','Motherboard']),
                disk_temp=max(disks) if disks else None)

def is_core_clock_name(name):
    label=' '.join(str(name).casefold().split())
    averages={'cores (average)','cores (average effective)','core average','cpu core average','cpu average','core average effective','cpu clock','cpu core'}
    return label in averages or bool(re.match(r'^(?:cpu\s+)?core\s*#?\s*\d+\b',label))

def select_cpu_clock(rows,chosen=''):
    """MHz from LHM only: do not mistake Bus/Fabric/Memory clocks for CPU.

    Prefer the reported core average. Fallback averages only like-for-like
    per-core readings of the first supported CPU, never reported + effective.
    """
    clocks=[r for r in rows if r.get('SensorType')=='Clock' and group_for(str(r.get('Identifier','')))=='CPU' and is_core_clock_name(r.get('Name',''))]
    if chosen:
        r=next((r for r in clocks if r.get('Identifier')==chosen),None)
        if not r:return None,'Выбранный CPU Clock недоступен','unavailable'
        v=finite(r.get('Value'));label=str(r.get('Name') or chosen)
        return v,label,'effective' if 'effective' in label.casefold() else 'reported'
    valid=[r for r in clocks if finite(r.get('Value')) is not None]
    for name in ['cores (average)','core average','cpu core average','cpu average','cpu clock','cpu core','cores (average effective)','core average effective']:
        r=next((r for r in valid if ' '.join(str(r.get('Name','')).casefold().split())==name),None)
        if r:return finite(r['Value']),str(r['Name']),'effective' if 'effective' in name else 'reported'
    per_core=[r for r in valid if re.match(r'^(?:cpu\s+)?core\s*#?\s*\d+\b',str(r.get('Name','')).casefold())]
    for effective in [False,True]:
        selected=[r for r in per_core if ('effective' in str(r.get('Name','')).casefold())==effective]
        if not selected:continue
        parent=selected[0].get('Parent') or str(selected[0].get('Identifier','')).rsplit('/',2)[0]
        selected=[r for r in selected if (r.get('Parent') or str(r.get('Identifier','')).rsplit('/',2)[0])==parent]
        label=('Средняя эффективная частота' if effective else 'Средняя частота')+f' доступных ядер ({len(selected)}, расчёт)'
        return sum(finite(r['Value']) for r in selected)/len(selected),label,'effective' if effective else 'reported'
    return None,'LHM: нет доступного CPU Clock','unavailable'

def resolve_cpu_clock(snapshot,os_frequency=None,allow_os_fallback=False):
    """Merge without overwriting a live LHM Clock with a nominal OS value."""
    value=finite(snapshot.get('cpu_clock'))
    label=str((snapshot.get('sensor_labels') or {}).get('cpu_clock') or 'LHM: частота недоступна')
    if value is not None:
        return value,label,snapshot.get('cpu_clock_source') or 'LHM',snapshot.get('cpu_clock_kind') or 'reported'
    if allow_os_fallback and finite(os_frequency) is not None:
        return finite(os_frequency),'ОС / psutil (резервный источник)','ОС / psutil','os'
    return None,label,'Недоступно','unavailable'

class Collector:
    def __init__(self):
        self.lock=threading.Lock()
        self.stop=threading.Event()
        self.state={}
        self.hardware={}
        self.poll_ms=500;self.system_period=0.25
        self._nv_checked=float('-inf');self._nv_cache=None
        self.threads=[];self.generation=0
        self.source_mode="auto";self.port=8085;self.username="";self.password="";self.mapping={};self.diagnostics={}
        self.rtss_reader=ApplicationReader()
        self.transport="Недоступно"
        self.nv=shutil.which('nvidia-smi')
        if not self.nv and os.name=='nt':
            p=Path(os.environ.get('ProgramFiles','C:/Program Files'))/'NVIDIA Corporation/NVSMI/nvidia-smi.exe'
            if p.exists():self.nv=str(p)

    def start(self):
        if any(t.is_alive() for t in self.threads):return
        self.stop.clear();self.threads=[]
        for target in [self._hardware_loop,self._system_loop]:
            t=threading.Thread(target=target,daemon=True)
            self.threads.append(t);t.start()

    def close(self):
        self.stop.set()

    def snapshot(self):
        with self.lock:
            return dict(self.state)

    def configure(self,mode='auto',port=8085,username='',password='',mapping=None):
        with self.lock:
            mode=source_mode(mode);port=bounded_int(port,8085,1,65535)
            mapping=dict(mapping) if isinstance(mapping,dict) else {}
            if (self.source_mode,self.port,self.username,self.password,self.mapping)!=(mode,port,username,password,mapping):
                self.generation+=1;self.hardware={};self.state={};self.transport='Недоступно';self.diagnostics={}
            self.source_mode=mode;self.port=port;self.username=username;self.password=password;self.mapping=mapping

    def set_poll_interval(self,milliseconds):
        try:
            if isinstance(milliseconds,bool):raise ValueError('not a polling interval')
            value=int(milliseconds)
        except (TypeError,ValueError,OverflowError):value=500
        with self.lock:self.poll_ms=max(250,min(5000,value))

    def effective_poll_ms(self):
        with self.lock:value=self.poll_ms
        if self.transport=='WMI':value=max(value,2000)
        if self.diagnostics.get('connected') is False:value=max(value,2000)
        return value

    def _nvidia_output(self):
        now=time.monotonic()
        if now-self._nv_checked<1:
            if self._nv_cache is None:raise OSError('NVIDIA query temporarily unavailable')
            return self._nv_cache
        self._nv_checked=now;self._nv_cache=None
        output=command([self.nv,'--query-gpu=name,utilization.gpu,temperature.gpu,power.draw,clocks.gr,memory.used,memory.total','--format=csv,noheader,nounits'])
        self._nv_cache=output;return output

    def _wmi_read(self):
        if os.name!='nt':raise RuntimeError('WMI доступен только в Windows.')
        script="""[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;
$ErrorActionPreference = 'Stop';
$errs = @(); $s = @(); $h = @();
try { $s = @(Get-CimInstance -Namespace root/LibreHardwareMonitor -ClassName Sensor | Select-Object Identifier,Parent,Name,SensorType,Value) }
catch { $errs += ('Sensor: ' + $_.Exception.Message) }
try { $h = @(Get-CimInstance -Namespace root/LibreHardwareMonitor -ClassName Hardware | Select-Object Identifier,Name) }
catch { $errs += ('Hardware: ' + $_.Exception.Message) }
@{Sensors=$s;Hardware=$h;Errors=$errs} | ConvertTo-Json -Depth 5 -Compress"""
        data=json.loads(command(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],10))
        rows=data.get('Sensors') or [];devices=data.get('Hardware') or []
        if isinstance(rows,dict):rows=[rows]
        if isinstance(devices,dict):devices=[devices]
        if not rows:raise RuntimeError('WMI вернул 0 датчиков. В LHM 0.9.5 WMI удалён; используйте HTTP. '+ '; '.join(data.get('Errors') or []))
        for r in rows:r['Source']='LHM WMI'
        return rows,devices,{'transport':'WMI','sensor_count':len(rows),'hardware_count':len(devices),'warnings':data.get('Errors') or []}

    def _set_backend_report(self,report,transport,generation):
        with self.lock:
            if generation==self.generation:self.diagnostics=report;self.transport=transport

    def _lhm(self):
        with self.lock:mode,port,user,password,generation=self.source_mode,self.port,self.username,self.password,self.generation
        if mode=='aida':
            try:
                rows,devices,detail=read_aida64()
                self._set_backend_report({'checked_at':time.time(),'connected':True,'source':'AIDA64 Shared Memory','attempts':[{'backend':'AIDA64','ok':True,**detail}]},'AIDA64 Shared Memory',generation)
                return rows,devices,f'AIDA64: {len(rows)} датчиков, {len(normalize_temperatures(rows,devices))} температур.'
            except Exception as e:
                self._set_backend_report({'checked_at':time.time(),'connected':False,'source':'AIDA64 Shared Memory','attempts':[{'backend':'AIDA64','ok':False,'error':str(e)}]},'Недоступно',generation)
                return [],[], 'Нет связи с AIDA64. Включите Shared Memory; подробности — «Подключить датчики».'
        attempts=[]
        backends=['HTTP','WMI'] if mode=='auto' else ['WMI'] if mode=='wmi' else ['HTTP']
        for backend in backends:
            try:
                rows,devices,detail=read_http(port,user,password) if backend=='HTTP' else self._wmi_read()
                attempts.append({'backend':backend,'ok':True,**detail})
                self._set_backend_report({'checked_at':time.time(),'attempts':attempts,'connected':True,'source':backend},backend,generation)
                return rows,devices,f'LHM {backend}: {len(rows)} датчиков, {len(normalize_temperatures(rows,devices))} температур.'
            except Exception as e:
                if isinstance(e,subprocess.CalledProcessError):msg=(e.stderr or str(e))[:1800]
                else:msg=describe_error(e)
                attempts.append({'backend':backend,'ok':False,'error':msg})
        self._set_backend_report({'checked_at':time.time(),'attempts':attempts,'connected':False,'source':None},'Недоступно',generation)
        return [],[], 'Нет связи с LHM. Включите Remote Web Server > Run; подробности — «Подключить датчики». '

    def choose_sensor(self,rows,key,typ,group,names):
        from dashboard import matches_slot
        def eligible(r):
            normalized={'id':str(r.get('Identifier','')),'name':str(r.get('Name','')),'canonical_name':str(r.get('Name','')),
                        'type':str(r.get('SensorType','')),'unit':r.get('Unit') or UNITS.get(r.get('SensorType'),'')}
            return matches_slot(normalized,key)
        with self.lock:chosen=self.mapping.get(key)
        if chosen:
            r=next((r for r in rows if r.get('Identifier')==chosen and eligible(r)),None)
            return finite(r.get('Value')) if r else None, str(r.get('Name')) if r else 'Выбранный датчик недоступен'
        for name in names:
            r=next((r for r in rows if eligible(r) and group in str(r.get('Identifier','')).lower()
                    and name.casefold() in str(r.get('Name','')).casefold() and finite(r.get('Value')) is not None),None)
            if r:return finite(r['Value']),str(r.get('Name'))
        return None,'Нет подходящего датчика; выберите вручную'

    def _hardware_once(self):
        rows,devices,status=self._lhm()
        aida=any(r.get("Source")=="AIDA64 Shared Memory" for r in rows)
        provider="AIDA64" if aida else "LHM"
        temps=normalize_temperatures(rows,devices)
        # Avoid mixing overview metrics from different GPUs. Full sensor table keeps all GPUs.
        gpu_ids=sorted({str(r.get('Identifier','')).rsplit('/',2)[0] for r in rows if '/gpu' in str(r.get('Identifier',''))})
        preferred=next((i for i in gpu_ids if 'gpu-nvidia' in i),None) if self.nv else None
        primary=preferred or (gpu_ids[0] if gpu_ids else None)
        overview_rows=[r for r in rows if '/gpu' not in str(r.get('Identifier','')) or (primary and str(r.get('Identifier','')).startswith(primary+'/'))]
        overview_temps=[t for t in temps if t['group']!='GPU' or (primary and t['id'].startswith(primary+'/'))]
        h=temperature_summary(overview_temps)
        h.update(status=status, temperatures=temps, cpu_power=None,
                 cpu_rpm=None, gpu_usage=find_value(overview_rows,'/gpu','Load',['GPU Core']),
                 gpu_clock=find_value(overview_rows,'/gpu','Clock',['GPU Core']),gpu_power=find_value(overview_rows,'/gpu','Power',['GPU Package','GPU Power','GPU']),
                 gpu_rpm=None,gpu_name=None,vram_used=None,vram_total=None,
                 gpu_source=provider if primary else 'Недоступно')
        selections={}
        for key,typ,group,names in [
            ('cpu_temp','Temperature','cpu',['CPU Package','Tctl','Tdie','Core Average','Package']),
            ('cpu_power','Power','cpu',['CPU Package','Package','CPU PPT','PPT','CPU Total']),
            ('cpu_rpm','Fan','',['CPU Fan','CPU','Processor']),
            ('gpu_rpm','Fan','/gpu',['GPU','Fan'])]:
            value,label=self.choose_sensor(overview_rows,key,typ,group,names)
            # Keep a computed CPU temperature fallback if no manual mapping was selected.
            with self.lock:manual=bool(self.mapping.get(key))
            if key!='cpu_temp' or value is not None or manual:h[key]=value
            selections[key]=label
        with self.lock:chosen_clock=self.mapping.get('cpu_clock','')
        h['cpu_clock'],selections['cpu_clock'],h['cpu_clock_kind']=select_cpu_clock(overview_rows,chosen_clock)
        h['cpu_clock_source']=provider if h['cpu_clock'] is not None else 'Недоступно'
        h['fps']=find_value(rows,'/aida/application/','FPS',['RTSS FPS'])
        h['fps_source']='AIDA64 / RTSS' if h['fps'] is not None else 'Недоступно'
        h['sensor_labels']=selections
        h['sensor_rows']=[{'id':str(r.get('Identifier','')),'device':next((d.get('Name') for d in devices if d.get('Identifier')==r.get('Parent')),r.get('Parent') or ''),
                           'name':str(r.get('DisplayName') or r.get('Name','')),'canonical_name':str(r.get('Name','')),'text_value':r.get('TextValue',''),'type':str(r.get('SensorType','')),'value':finite(r.get('Value')),
                           'unit':r.get('Unit') or UNITS.get(r.get('SensorType'),''),'source':r.get('Source') or 'LHM','is_limit':r.get('SensorType')=='Temperature' and is_temperature_limit(r.get('Name',''))} for r in rows]
        h['diagnostics']=dict(self.diagnostics)
        h['lhm_transport']=self.transport
        if primary:
            h['gpu_name']=next((d.get('Name') for d in devices if d.get('Identifier')==primary),None)
        if not aida and os.name!='nt' and hasattr(psutil,'sensors_temperatures'):
            try:
                for driver,sensors in psutil.sensors_temperatures().items():
                    for i,s in enumerate(sensors):
                        v=finite(s.current)
                        if v is None:continue
                        grp='CPU' if driver in ['coretemp','k10temp','cpu_thermal'] else 'Накопитель' if 'nvme' in driver else 'Другое'
                        temps.append(dict(id=f'os/{driver}/{i}',group=grp,device=driver,name=s.label or f'Датчик {i+1}',value=v,source='psutil / ОС'))
                h.update(temperature_summary(temps))
            except (OSError, RuntimeError):pass
        if self.nv:
            try:
                output=self._nvidia_output()
                name,usage,temp,power,clock,used,total=[s.strip() for s in output.splitlines()[0].split(',')]
                driver={'gpu_usage':finite(usage),'gpu_clock':finite(clock),'gpu_power':finite(power),'gpu_temp':finite(temp)}
                for key,value in driver.items():
                    if not aida or h.get(key) is None:h[key]=value
                h.update(gpu_name=name,vram_used=finite(used)/1024 if finite(used) is not None else None,
                         vram_total=finite(total)/1024 if finite(total) is not None else None,
                         gpu_source=provider+' + NVIDIA' if primary else 'NVIDIA driver')
                if finite(temp) is not None and (not aida or not any(t['group']=='GPU' and 'GPU Core' in t['name'] for t in temps)):
                    if not any(t['source']=='NVIDIA driver' for t in temps):
                        temps.append(dict(id='nvidia/0/temperature',group='GPU',device=name,name='GPU Core',value=finite(temp),source='NVIDIA driver'))
            except (subprocess.SubprocessError,OSError,ValueError,IndexError):
                h['gpu_source']=provider if primary else 'NVIDIA недоступна'
        if h['vram_total'] is None:
            used=find_value(overview_rows,'/gpu','SmallData',['GPU Memory Used'])
            free=find_value(overview_rows,'/gpu','SmallData',['GPU Memory Free'])
            if used is not None and free is not None:h['vram_used'],h['vram_total']=used/1024,(used+free)/1024
        h['temperatures']=temps
        h['updated']=time.time()
        return h

    def _hardware_loop(self):
        while not self.stop.is_set():
            started=time.monotonic();failed=False
            with self.lock:generation=self.generation
            try:
                h=self._hardware_once()
            except Exception as e:
                failed=True
                h={'status':f'Ошибка чтения датчиков: {type(e).__name__}', 'temperatures':[], 'diagnostics':dict(self.diagnostics), 'updated':time.time()}
            elapsed=time.monotonic()-started;h['hardware_read_duration_ms']=round(elapsed*1000,1)
            with self.lock:
                if generation==self.generation:self.hardware=h
            period=max(self.effective_poll_ms()/1000,2 if failed else 0)
            self.stop.wait(max(0.05,period-elapsed))

    def _system_loop(self):
        previous=None;last=time.monotonic()
        slow_at=float('-inf');rtss_at=float('-inf');disks=[];mhz=None;rtss_report={}
        host=platform.node();cpu_name='Processor';cores=None;threads=None;boot=None
        while not self.stop.wait(self.system_period):
            try:
                now=time.monotonic();net=psutil.net_io_counters();delta=max(now-last,.001);ram=psutil.virtual_memory()
                if previous is None:previous=net
                if boot is None:
                    boot=psutil.boot_time();cores=psutil.cpu_count(logical=False);threads=psutil.cpu_count();cpu_name=platform.processor() or 'Processor'
                if now-slow_at>=1:
                    mhz=None
                    if os.name!='nt':
                        try:freq=psutil.cpu_freq();mhz=finite(freq.current) if freq else None
                        except (OSError,NotImplementedError):pass
                    disks=[];seen=set()
                    for part in psutil.disk_partitions(all=False):
                        if part.mountpoint in seen or not part.fstype or 'cdrom' in part.opts or not os.path.isdir(part.mountpoint):continue
                        try:
                            d=psutil.disk_usage(part.mountpoint)
                            disks.append(dict(mount=part.mountpoint,free=d.free/GIB,total=d.total/GIB,percent=d.percent));seen.add(part.mountpoint)
                        except (OSError,PermissionError):pass
                    slow_at=now
                with self.lock:s=dict(self.hardware);manual_clock=bool(self.mapping.get('cpu_clock'));generation=self.generation
                if s.get('updated') and time.time()-s['updated']>20:s={'status':'Данные датчиков устарели.','temperatures':[]}
                clock,label,source,kind=resolve_cpu_clock(s,mhz,allow_os_fallback=os.name!='nt' and not manual_clock)
                s['sensor_labels']=dict(s.get('sensor_labels') or {});s['sensor_labels']['cpu_clock']=label
                s.update(timestamp=time.time(),hostname=host,cpu_name=cpu_name,
                         cpu_usage=psutil.cpu_percent(None),cpu_clock=clock,cpu_clock_source=source,cpu_clock_kind=kind,cores=cores,threads=threads,
                         ram_used=(ram.total-ram.available)/GIB,ram_free=ram.available/GIB,ram_total=ram.total/GIB,ram_usage=ram.percent,
                         upload=max(0,net.bytes_sent-previous.bytes_sent)/delta/1024 if net is not None and previous is not None else None,download=max(0,net.bytes_recv-previous.bytes_recv)/delta/1024 if net is not None and previous is not None else None,
                         disks=disks,uptime=time.time()-boot)
                if now-rtss_at>=0.5:rtss_report=self.rtss_reader.poll();rtss_at=now
                s['rtss_applications']=rtss_report
                s['polling']={'requested_ms':self.poll_ms,'effective_hardware_ms':self.effective_poll_ms(),'system_ms':int(self.system_period*1000),'nvidia_minimum_ms':1000,'rtss_ms':500,'hardware_read_duration_ms':s.get('hardware_read_duration_ms')}
                with self.lock:
                    if generation==self.generation:self.state=s
                last,previous=now,net
            except Exception as e:
                with self.lock:self.state={'timestamp':time.time(),'status':f'Ошибка системного мониторинга: {type(e).__name__}','temperatures':[]}
