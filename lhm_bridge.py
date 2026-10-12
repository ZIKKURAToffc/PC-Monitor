"""Read-only LHM transport: current local HTTP API + optional legacy WMI."""
import base64
import json
import math
import re
import urllib.error
import urllib.request

TYPES={'temperature':'Temperature','fan':'Fan','power':'Power','clock':'Clock','load':'Load','smalldata':'SmallData','data':'Data','control':'Control','voltage':'Voltage'}
UNITS={'Temperature':'°C','Fan':'RPM','Power':'W','Clock':'MHz','Load':'%','Control':'%','SmallData':'MB','Data':'GB'}

def numeric(value):
    if isinstance(value, bool):return None
    try:
        result=float(value)
        return result if math.isfinite(result) else None
    except (TypeError,ValueError,OverflowError):return None

def formatted_value(value,typ):
    """Compatibility with old data.json: only explicit units, never assume null=0."""
    if isinstance(value,(int,float)):return numeric(value)
    if not isinstance(value,str):return None
    clean=value.strip().replace('\u00a0','').replace('\u202f','')
    if not clean or clean in ['-','—']:return None
    unit=re.sub(r'[\d.,\s+\-]','',clean).casefold()
    allowed={'Temperature':{'°c','°f'},'Fan':{'rpm'},'Power':{'w'},'Clock':{'mhz'},'Load':{'%'},'Control':{'%'},'SmallData':{'mb'},'Data':{'gb'}}
    if typ not in allowed or unit not in allowed[typ]:return None
    match=re.match(r'^\s*([+-]?[\d.,\s]+)',clean)
    if not match:return None
    raw=match.group(1).replace(' ','').strip()
    if typ=='Fan' and re.fullmatch(r'[+-]?\d{1,3}(?:,\d{3})+',raw):raw=raw.replace(',','')
    elif ',' in raw and '.' not in raw:raw=raw.replace(',','.')
    elif ',' in raw and '.' in raw:raw=raw.replace('.','').replace(',','.') if raw.rfind(',')>raw.rfind('.') else raw.replace(',','')
    v=numeric(raw)
    if v is not None and typ=='Temperature' and unit=='°f':v=(v-32)*5/9
    return v

def raw_sensor_value(value,typ):
    """RawValue may be a number OR a localized string with explicit units.

    Explicit null/NaN remains missing: do not substitute Value for a present
    but unavailable RawValue. Unit-bearing Fahrenheit is converted to Celsius.
    """
    result=numeric(value)
    if result is not None:return result
    if not isinstance(value,str):return None
    clean=value.strip()
    if re.fullmatch(r'[+-]?\d+,\d+',clean):return numeric(clean.replace(',','.'))
    return formatted_value(value,typ)

def parse_tree(data):
    if not isinstance(data,dict):raise ValueError('Ожидался JSON-объект LHM.')
    rows=[];devices=[]
    def visit(node,hardware=None):
        if not isinstance(node,dict):return
        hid=node.get('HardwareId')
        if hid:
            hardware=str(hid);devices.append({'Identifier':hardware,'Name':str(node.get('Text') or hardware)})
        sid=node.get('SensorId')
        if sid:
            sid=str(sid);parts=sid.rsplit('/',2);typ=str(node.get('Type') or TYPES.get(parts[-2].lower() if len(parts)>1 else '', ''))
            value=raw_sensor_value(node['RawValue'],typ) if 'RawValue' in node else formatted_value(node.get('Value'),typ)
            rows.append({'Identifier':sid,'Parent':hardware or sid.rsplit('/',2)[0],'Name':str(node.get('Text') or sid),
                         'SensorType':typ,'Value':value,'Source':'LHM HTTP'})
        children=node.get('Children',[])
        if isinstance(children,list):
            for child in children:visit(child,hardware)
    visit(data)
    if not rows:raise ValueError('Ответ получен, но в data.json нет датчиков SensorId. Проверьте, что это сервер LHM и в его окне есть показания.')
    return rows,devices

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None

def read_http(port=8085,username='',password='',timeout=2):
    port=int(port)
    if not 1<=port<=65535:raise ValueError('Некорректный порт LHM.')
    # Never use a proxy, follow a redirect, or send a password outside loopback.
    url=f'http://127.0.0.1:{port}/data.json'
    req=urllib.request.Request(url,headers={'Accept':'application/json'})
    if username or password:
        req.add_header('Authorization','Basic '+base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('ascii'))
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(req,timeout=timeout) as r:
        raw=r.read(5*1024*1024+1)
        if len(raw)>5*1024*1024:raise ValueError('Ответ LHM слишком большой.')
    data=json.loads(raw.decode('utf-8-sig'))
    rows,devices=parse_tree(data)
    return rows,devices,{'transport':'HTTP','endpoint':url,'version':str(data.get('Version') or 'не указана'),'sensor_count':len(rows),'hardware_count':len(devices)}

def describe_error(error):
    if isinstance(error,urllib.error.HTTPError):
        if error.code==401:return 'HTTP 401: LHM требует логин/пароль. Укажите их в настройках подключения; пароль не сохраняется.'
        if error.code==403:return 'HTTP 403: LHM запретил доступ.'
        if error.code==404:return 'HTTP 404: /data.json отсутствует. Проверьте порт сервера LHM.'
        return f'HTTP {error.code}: запрос не выполнен (перенаправления не разрешены).'
    if isinstance(error,urllib.error.URLError):return 'Сервер LHM не отвечает. Включите Remote Web Server > Run и проверьте порт.'
    if isinstance(error,(TimeoutError,ConnectionError)):return 'Тайм-аут или разрыв соединения с локальным LHM.'
    if isinstance(error,json.JSONDecodeError):return 'Ответ сервера не является корректным JSON LHM.'
    return str(error)[:800]
