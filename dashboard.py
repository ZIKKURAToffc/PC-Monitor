"""Dashboard selection: explicit IDs, compatible units, no stale-value fallback."""
import math
import re
SLOTS=[('fps','FPS','FPS'),('cpu_temp','Температура CPU','°C'),('cpu_clock','Частота CPU','MHz'),('cpu_usage','Загрузка CPU','%'),('cpu_power','Мощность CPU','W'),('cpu_rpm','Вентилятор CPU','RPM'),('gpu_temp','Температура GPU','°C'),('gpu_clock','Частота GPU','MHz'),('gpu_usage','Загрузка GPU','%'),('gpu_power','Мощность GPU','W'),('gpu_rpm','Вентилятор GPU','RPM'),('gpu_mem_temp','Температура памяти GPU','°C'),('sys_temp','Плата','°C'),('disk_temp','Диск Max','°C'),('ram_used','RAM занято','GiB'),('ram_free','RAM доступно','GiB'),('ram_usage','Загрузка RAM','%'),('vram_used','VRAM занято','GiB'),('vram_free','VRAM свободно','GiB'),('upload','Отправка сети','KiB/s'),('download','Загрузка сети','KiB/s')]

def number(value):
    if isinstance(value,bool):return None
    try:
        value=float(value);return value if math.isfinite(value) else None
    except (ValueError,TypeError,OverflowError):return None

MAX_CUSTOM_CARDS=128

def normalize_config(config):
    if not isinstance(config,dict):return {}
    result={}
    def entry(value):
        if not isinstance(value,dict):return {}
        item={}
        for name,limit in [('sensor',1024),('label',80),('unit',32)]:
            if name in value and isinstance(value[name],str):item[name]=value[name][:limit]
        if 'hidden' in value:item['hidden']=value['hidden'] is True or str(value['hidden']).lower() in ('true','1')
        return item
    if isinstance(config.get('slots'),dict):
        result['slots']={key:entry(value) for key,value in config['slots'].items() if isinstance(key,str) and key in {s[0] for s in SLOTS} and isinstance(value,dict)}
    if isinstance(config.get('custom'),list):
        result['custom']=[entry(item) for item in config['custom'][:MAX_CUSTOM_CARDS] if isinstance(item,dict) and isinstance(item.get('sensor'),str) and item['sensor']]
    return result

def available_rows(snapshot):
    raw_rows=snapshot.get('sensor_rows',[])
    rows=[dict(r) for r in raw_rows if isinstance(r,dict) and isinstance(r.get('id'),str)] if isinstance(raw_rows,list) else []
    for key,label,unit in SLOTS:
        # Only expose truly independent OS/driver readings, not a mapped dashboard slot.
        if key not in ['cpu_usage','ram_used','ram_free','ram_usage','upload','download']:continue
        rows.append(dict(id='system/'+key,name=label,device='ОС / psutil',type='System',unit=unit,value=number(snapshot.get(key)),source='ОС / psutil'))
    for key,label in [('vram_used','VRAM занято'),('vram_free','VRAM свободно')]:
        value=snapshot.get(key)
        if key=='vram_free' and number(snapshot.get('vram_total')) is not None and number(snapshot.get('vram_used')) is not None:value=max(0,number(snapshot['vram_total'])-number(snapshot['vram_used']))
        rows.append(dict(id='driver/'+key,name=label,device='GPU / резервный источник',type='Data',unit='GiB',value=number(value),source=snapshot.get('gpu_source','Недоступно')))
    return rows

def compatible(row,unit):
    return not row.get('is_limit') and row.get('unit','')==unit


def matches_slot(row,key):
    """Conservative semantic match for a built-in card, independent of UI captions."""
    from telemetry import group_for,is_core_clock_name,is_temperature_limit
    definition=next((x for x in SLOTS if x[0]==key),None)
    # Hotspot remains a distinct raw reading, not a configurable dashboard card.
    if key=='gpu_hotspot':definition=('gpu_hotspot','GPU Hotspot','°C')
    if key=='cpu_core_max':definition=('cpu_core_max','CPU Core Max','°C')
    if not definition or not compatible(row,definition[2]):return False
    sid=str(row.get('id','')).lower();name=str(row.get('canonical_name') or row.get('name','')).strip().casefold()
    name=re.sub(r'\s+',' ',name);typ=str(row.get('type','')).casefold();device=str(row.get('device','')).casefold()
    if typ=='temperature' and is_temperature_limit(name):return False
    # Independent virtual rows have an exact role; equal units do not make them interchangeable.
    if sid.startswith(('system/','driver/')):
        independent={'cpu_usage','ram_used','ram_free','ram_usage','upload','download','vram_used','vram_free'}
        return key in independent and sid==('driver/' if key.startswith('vram_') else 'system/')+key
    group=str(row.get('group') or group_for(sid))
    if group=='Другое':
        if re.search(r'\bgpu\b|geforce|radeon|graphics',name+' '+device):group='GPU'
        elif re.search(r'\bcpu\b|ryzen|processor',name+' '+device):group='CPU'
        elif re.search(r'\b(?:nvme|ssd|hdd|drive)\b',name+' '+device):group='Накопитель'
        elif re.search(r'motherboard|mainboard|материн|материнсь',name+' '+device):group='Плата'
    cpu=group=='CPU';gpu=group=='GPU'
    # Super-I/O can publish CPU cooling and socket sensors under the motherboard.
    board_cpu=group in ('Плата','Другое') and bool(re.search(r'\bcpu\b|processor|процессор|процесор',name))
    if key=='fps':return typ=='fps'
    if key=='cpu_temp':return typ=='temperature' and (cpu or board_cpu)
    if key=='cpu_core_max':return typ=='temperature' and cpu and bool(re.search(r'\b(?:cpu )?core\s*#?\s*\d+\b|\b(?:cpu )?core(?:s)? max\b|\bmax(?:imum)? core|coremax',name))
    if key=='cpu_clock':return typ=='clock' and cpu and is_core_clock_name(name)
    if key=='cpu_power':return typ=='power' and (cpu or board_cpu)
    if key=='cpu_rpm':return typ=='fan' and (cpu or board_cpu)
    if key=='cpu_usage':return typ in ('load','system') and cpu and bool(re.fullmatch(r'cpu(?: total| load| usage| utilization| utilisation| average)?|total|processor(?: load| usage| utilization)?',name))
    if key.startswith('gpu_'):
        if not gpu:return False
        if key=='gpu_power':return typ=='power'
        if key=='gpu_rpm':return typ=='fan'
        hot=bool(re.search(r'hot\s*spot|hotspot|горяч|гаряч',name))
        memory=bool(re.search(r'memory|vram|памят|пам’ят|пам\x27ят',name))
        if key=='gpu_hotspot':return typ=='temperature' and hot
        if key=='gpu_mem_temp':return typ=='temperature' and memory and not hot
        core=bool(re.fullmatch(r'(?:gpu )?(?:core(?: \(diode\))?|diode|temperature|graphics(?: clock)?|gpu clock|gpu)|(?:gpu )?core temperature',name))
        if key=='gpu_temp':return typ=='temperature' and core and not hot and not memory
        if key=='gpu_clock':return typ=='clock' and core and not memory
        if key=='gpu_usage':return typ in ('load','system') and not memory and bool(re.fullmatch(r'(?:gpu )?core|gpu(?: load| usage| utilization| utilisation| total)?|graphics(?: load| usage)?',name))
        return False
    if key=='sys_temp':return typ=='temperature' and group=='Плата' and bool(re.fullmatch(r'(?:system|motherboard|mainboard|board)(?: temperature| temp|\s*#?\d+)?|материнская плата|материнська плата|плата',name))
    if key=='disk_temp':return typ=='temperature' and group=='Накопитель'
    # Only explicitly identified memory/network roles are accepted; no number guessing.
    ram=bool(re.search(r'/(?:ram|memory)/',sid)) or (group!='GPU' and bool(re.search(r'physical memory|system memory|оперативн',name+' '+device)))
    used=bool(re.search(r'\bused\b|занято|використано',name));free=bool(re.search(r'free|available|доступно|свободно|вільно',name))
    if key in ('ram_used','ram_free'):return typ in ('data','smalldata','system') and ram and (used and not free if key=='ram_used' else free and not used)
    if key=='ram_usage':return typ in ('load','system') and ram and bool(re.search(r'load|usage|utilization|utilisation|загруз|завантаж',name) or re.fullmatch(r'(?:system |physical )?memory|ram',name))
    if key in ('vram_used','vram_free'):return typ in ('data','smalldata','system') and gpu and bool(re.search(r'memory|vram',name)) and (used and not free if key=='vram_used' else free and not used)
    network=bool(re.search(r'/(?:network|nic|ethernet)/',sid)) or bool(re.search(r'network|ethernet|сеть|мереж',device))
    if key=='upload':return typ in ('throughput','system') and network and bool(re.search(r'upload|transmit|\btx\b|sent|send|отправ|надсил',name)) and not bool(re.search(r'download|receive|\brx\b',name))
    if key=='download':return typ in ('throughput','system') and network and bool(re.search(r'download|receive|\brx\b|received|загруз|завантаж',name)) and not bool(re.search(r'upload|transmit|\btx\b',name))
    return False

def apply_config(snapshot,config):
    config=normalize_config(config)
    result=dict(snapshot);result['sensor_labels']=dict(snapshot.get('sensor_labels') or {})
    lookup={r['id']:r for r in available_rows(snapshot)};result['mapping_status']={}
    if 'vram_free' not in result and number(result.get('vram_total')) is not None and number(result.get('vram_used')) is not None:result['vram_free']=max(0,number(result['vram_total'])-number(result['vram_used']))
    for key,label,unit in SLOTS:
        setting=config.get('slots',{}).get(key,{})
        sid=setting.get('sensor','')
        if not sid:continue
        row=lookup.get(sid)
        valid=bool(row and matches_slot(row,key));result[key]=number(row.get('value')) if valid else None
        result['mapping_status'][key]='selected' if valid else 'incompatible' if row else 'missing'
        result['sensor_labels'][key]=(row['name']+' · '+row.get('source','')) if valid else 'Датчик не соответствует карточке' if row else 'Выбранный датчик недоступен'
        if key=='cpu_clock':result['cpu_clock_kind']='custom'
        if key=='fps':result['fps_source']=(row.get('source') or 'Недоступно') if valid else 'Недоступно'
    return result
