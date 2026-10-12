"""Explicit local diagnostic export. Does not send data anywhere."""
from pathlib import Path
import re
import argparse
from aida_bridge import read_shared_buffer,decode_buffer,parse_shared_memory

def main():
    p=argparse.ArgumentParser(description='Save currently exported AIDA64 XML locally. May contain device labels; inspect before sharing.')
    p.add_argument('--output',default='aida-sensors.xml');args=p.parse_args()
    try:
        raw,meta=read_shared_buffer();text=decode_buffer(raw);rows,devices=parse_shared_memory(text)
        text=re.sub(r'^\s*<\?xml[^?]*\?>','',text,count=1)
        Path(args.output).write_text('<aida_snapshot>'+text+'</aida_snapshot>',encoding='utf-8')
        print('Saved:',args.output,'Sensors:',len(rows),'Transport:',meta['transport'])
        print('This is a snapshot, not a live stream. Inspect before sharing.')
    except Exception as e:
        print('AIDA64:',e);raise SystemExit(1)

if __name__=='__main__':main()
