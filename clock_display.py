"""Local wall clock from the OS timezone; no network time or inferred location."""
from PySide6.QtCore import QDateTime,QTimeZone

def clock_data(instant=None,zone=None):
    instant=instant if instant is not None else QDateTime.currentDateTimeUtc()
    if zone is None:
        # Construct from the OS ID explicitly. Some Qt builds with an empty system
        # timezone ID return a spurious fixed +1-second zone from systemTimeZone().
        system_zone=QTimeZone(QTimeZone.systemTimeZoneId())
        local=instant.toTimeZone(system_zone) if system_zone.isValid() else instant.toLocalTime()
        identifier=bytes(system_zone.id()).decode('utf-8',errors='replace') if system_zone.isValid() else local.timeZoneAbbreviation()
    else:
        if not zone.isValid():zone=QTimeZone.utc()
        local=instant.toTimeZone(zone);identifier=bytes(zone.id()).decode('utf-8',errors='replace')
    seconds=local.offsetFromUtc();sign='+' if seconds>=0 else '-';seconds=abs(seconds)
    offset=f'UTC{sign}{seconds//3600:02d}:{seconds%3600//60:02d}'
    if seconds%60:offset+=f':{seconds%60:02d}'
    return {'time':local.toString('HH:mm:ss'),'date':local.toString('dd.MM.yyyy'),
            'zone':identifier or offset,'abbreviation':local.timeZoneAbbreviation(),'offset':offset}
