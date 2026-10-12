"""Optional local CLI probe; credentials must be entered in the native application."""
import json,sys
from pathlib import Path
from telemetry import Collector
from app_metadata import APP_VERSION

def main():
    c=Collector()
    try:
        d=c._hardware_once()
        report={'app_version':APP_VERSION,'diagnostics':d.get('diagnostics'),'sensor_labels':d.get('sensor_labels'),'sensors':d.get('sensor_rows',[])}
        path=Path.cwd()/'lhm-diagnostics.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Report saved: '+str(path));print(json.dumps(d.get('diagnostics'),ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError,RuntimeError) as e:
        print('Diagnostic report could not be saved: '+str(e),file=sys.stderr);return 1
    finally:c.close()

if __name__=='__main__':raise SystemExit(main())
