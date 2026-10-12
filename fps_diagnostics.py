"""Explain the published FPS reading; no frame capture or game hooks."""
import math,time

def numeric(value):
    if isinstance(value,bool):return None
    try:
        v=float(value);return v if math.isfinite(v) else None
    except (TypeError,ValueError,OverflowError):return None

def application_context(snapshot,selected,row,now):
    report=snapshot.get('rtss_applications') or {}
    if not isinstance(report,dict):report={}
    checked=numeric(report.get('checked_at'))
    result={'state':'unknown','name':None,'pid':None,'candidates':[],'source':'RTSSSharedMemoryV2','fps_link':'unconfirmed','cached':bool(report.get('cached',False)),'metadata_age_seconds':round(max(0,now-checked),2) if checked is not None else None}
    if checked is None or now-checked>(3 if result['cached'] else 5) or checked-now>2:return result
    if selected and not (row and (str(row.get('id','')).upper().endswith('/SRTSSFPS') or 'rtss' in str(row.get('name','')).lower())):
        result['state']='other-fps-source';return result
    applications=report.get('applications',[])
    if not isinstance(applications,list):applications=[]
    apps=[a for a in applications if isinstance(a,dict) and isinstance(a.get('name'),str) and a.get('pid') and numeric(a.get('age_ms')) is not None and 0<=numeric(a.get('age_ms'))+max(0,now-checked)*1000<=5000]
    result['candidates']=[{'name':a['name'],'pid':a['pid']} for a in apps]
    if len(apps)>1:result['state']='multiple';return result
    if not apps:return result
    app=apps[0];result.update(state='tracked',name=app['name'],pid=app['pid'])
    # RTSS has no pointer binding its application row to the AIDA64 export.
    return result

def inspect_fps(snapshot,config=None,now=None):
    from dashboard import normalize_config
    selected=normalize_config(config).get('slots',{}).get('fps',{}).get('sensor','')
    raw_rows=snapshot.get('sensor_rows',[])
    rows=[r for r in raw_rows if isinstance(r,dict)] if isinstance(raw_rows,list) else []
    export=next((r for r in rows if r.get('type')=='FPS' and str(r.get('id','')).upper().endswith('/SRTSSFPS')),None)
    row=next((r for r in rows if r.get('id')==selected),None) if selected else export
    value=numeric(snapshot.get('fps'));source=(row.get('source') if row else snapshot.get('fps_source')) or 'Недоступно'
    result={'state':'missing','reason':'not-published','value':None,'source':source,'selected_sensor_id':selected or None,
            'sensor_id':row.get('id') if row else None,'hardware_age_seconds':None,
            'aida_export':{'present':export is not None,'value':numeric(export.get('value')) if export else None,'raw_text':str(export.get('text_value','')) if export else None},
            'game_detection':'unknown','capture_method':'AIDA64 SRTSSFPS export or explicit dashboard sensor; no direct RTSS capture'}
    result['application']=application_context(snapshot,selected,row,time.time() if now is None else now)
    if selected and (row is None or row.get('unit')!='FPS' or row.get('is_limit')):
        result['reason']='selected-unavailable' if row is None else 'incompatible-unit';return result
    if value is None:return result
    if value<0:result['state']='invalid';result['reason']='negative-value';return result
    updated=numeric(snapshot.get('updated'))
    if updated is not None:
        age=max(0,(time.time() if now is None else now)-updated);result['hardware_age_seconds']=round(age,1)
        if age>20:result['state']='stale';result['reason']='hardware-data-stale';return result
    result['value']=value
    if 'DEMO' in str(source).upper():result['state']='demo';result['reason']='synthetic'
    elif value==0:result['state']='zero';result['reason']='exported-zero'
    else:result['state']='available';result['reason']='published-positive'
    return result

FPS_GUIDE='''Программа читает FPS, опубликованный AIDA64 (SRTSSFPS), а не измеряет кадры игры напрямую. 0 означает: источник передал ноль. Это не подтверждает, что игра обнаружена, и не позволяет установить причину по одному значению.

1. Запустите RTSS (RivaTuner Statistics Server) и игру. В профиле RTSS выберите исполняемый файл самой игры, не лаунчер; Application detection level не должен быть None. Используйте обычные разрешённые настройки мониторинга.
2. Проверьте, показывает ли сам RTSS ненулевой FPS во время игры. Если RTSS не видит кадры, наша программа через AIDA64 тоже их не получит.
3. В AIDA64 → Preferences → Hardware Monitoring → External Applications → Enable shared memory включите экспорт RTSS FPS (SRTSSFPS). Оставьте AIDA64 открытой.
4. В «Датчики панели» проверьте выбор FPS: Авто либо RTSS FPS с единицей FPS. Подождите обновления AIDA64 (примерно 3 секунды), затем обновите список.
5. Если RTSS показывает FPS, а в диагностике AIDA64 SRTSSFPS остаётся 0, проверяйте передачу RTSS → AIDA64. Если оба показывают 0 или отсутствуют, проверяйте обнаружение игры в RTSS.

Некоторые игры или античит могут не разрешать сторонний мониторинг. Не отключайте защиту игры и не пытайтесь обходить ограничения; используйте разрешённый игрой счётчик FPS. Программа не вычисляет FPS из загрузки GPU и не заменяет ноль выдуманным значением.'''
STATUS={'available':'FPS опубликован источником','demo':'Синтетические данные','zero':'Источник игры не определён — проверьте RTSS','missing':'FPS недоступен — проверьте источник','invalid':'Некорректный FPS от источника','stale':'Показание FPS устарело'}


def status_caption(report):
    if report['state']=='zero' and report.get('application',{}).get('state')=='tracked':return 'FPS = 0 — проверьте RTSS'
    return STATUS[report['state']]
