import base64
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
from lhm_bridge import parse_tree,formatted_value,read_http,describe_error
from telemetry import Collector

# Synthetic fixture using the official data.json field names, not a real PC dump.
FIXTURE={'Version':'0.9.5','Text':'Sensor','Children':[
 {'Text':'Fixture CPU','HardwareId':'/amdcpu/0','Children':[
  {'SensorId':'/amdcpu/0/temperature/0','Type':'Temperature','Text':'CPU (Tctl/Tdie)','RawValue':47,'Value':'116.6 °F'},
  {'SensorId':'/amdcpu/0/power/0','Type':'Power','Text':'CPU Package','RawValue':67.6,'Value':'67.6 W'}]},
 {'Text':'Nuvoton','HardwareId':'/lpc/nct/0','Children':[
  {'SensorId':'/lpc/nct/0/fan/0','Type':'Fan','Text':'Fan #1','RawValue':1240,'Value':'1240 RPM'},
  {'SensorId':'/lpc/nct/0/fan/1','Type':'Fan','Text':'Fan #2','RawValue':0,'Value':'0 RPM'},
  {'SensorId':'/lpc/nct/0/control/0','Type':'Control','Text':'CPU Fan Control','RawValue':40,'Value':'40 %'},
  {'SensorId':'/lpc/nct/0/temperature/1','Type':'Temperature','Text':'Unavailable','RawValue':None,'Value':'0 °C'}]}]}

class BridgeTests(unittest.TestCase):
    def test_raw_fields_and_null(self):
        rows,devices=parse_tree(FIXTURE)
        self.assertEqual(len(rows),6);self.assertEqual(len(devices),2);self.assertEqual(rows[0]['Value'],47)
        self.assertIsNone(rows[-1]['Value']);self.assertEqual(rows[3]['Value'],0);self.assertEqual(rows[2]['SensorType'],'Fan')
    def test_old_formatted_and_fahrenheit(self):
        self.assertEqual(formatted_value('47,0 °C','Temperature'),47)
        self.assertAlmostEqual(formatted_value('116.6 °F','Temperature'),47)
        self.assertEqual(formatted_value('1 240 RPM','Fan'),1240)
        self.assertIsNone(formatted_value('40 %','Fan'));self.assertIsNone(formatted_value('—','Power'))
    def test_unknown_payload_not_connected(self):
        with self.assertRaises(ValueError):parse_tree({'Text':'not LHM'})
    def test_manual_fan_and_power(self):
        rows,devices=parse_tree(FIXTURE);c=Collector();c.nv=None
        with patch.object(c,'_lhm',return_value=(rows,devices,'fixture')),patch('telemetry.psutil.sensors_temperatures',return_value={},create=True):
            d=c._hardware_once();self.assertIsNone(d['cpu_rpm']);self.assertEqual(d['cpu_power'],67.6);self.assertEqual(d['cpu_temp'],47)
            c.configure(mapping={'cpu_rpm':'/lpc/nct/0/fan/0'});d=c._hardware_once();self.assertIsNone(d['cpu_rpm'])
            rows[2]['Name']='CPU Fan';rows[2]['DisplayName']='CPU Fan';d=c._hardware_once();self.assertEqual(d['cpu_rpm'],1240)
            rows[3]['Name']='CPU OPT Fan';rows[3]['DisplayName']='CPU OPT Fan'
            c.configure(mapping={'cpu_rpm':'/lpc/nct/0/fan/1'});d=c._hardware_once();self.assertEqual(d['cpu_rpm'],0)
            c.configure(mapping={'cpu_rpm':'/lpc/nct/0/control/0'});d=c._hardware_once();self.assertIsNone(d['cpu_rpm'])
    def test_http_success_auth_failure_and_redirect(self):
        class Handler(BaseHTTPRequestHandler):
            mode='ok'
            def do_GET(self):
                if self.mode=='auth' and self.headers.get('Authorization')!='Basic '+base64.b64encode(b'test-user:test-password').decode():self.send_response(401);self.end_headers();return
                if self.mode=='redirect':self.send_response(302);self.send_header('Location','http://example.invalid/');self.end_headers();return
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(FIXTURE).encode())
            def log_message(self,*_):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();port=server.server_port
        try:
            rows,devices,detail=read_http(port);self.assertEqual(detail['version'],'0.9.5');self.assertEqual(len(rows),6)
            Handler.mode='auth'
            try:read_http(port)
            except Exception as e:self.assertIn('401',describe_error(e))
            else:self.fail('Expected 401')
            rows,_,_=read_http(port,'test-user','test-password');self.assertEqual(len(rows),6)
            Handler.mode='redirect'
            with self.assertRaises(Exception):read_http(port)
        finally:server.shutdown();server.server_close();thread.join()
    def test_fallback_and_diagnostic_privacy(self):
        c=Collector();c.configure(password='test-password')
        rows,devices=parse_tree(FIXTURE)
        with patch('telemetry.read_http',side_effect=ConnectionError()),patch.object(c,'_wmi_read',return_value=(rows,devices,{'transport':'WMI'})):
            returned,_,status=c._lhm()
        self.assertEqual(len(returned),6);self.assertEqual(c.diagnostics['source'],'WMI');self.assertNotIn('test-password',json.dumps(c.diagnostics))
    def test_wmi_metadata_failure_keeps_sensor_values(self):
        c=Collector();rows,_=parse_tree(FIXTURE)
        payload=json.dumps({'Sensors':rows,'Hardware':[],'Errors':['Hardware metadata unavailable']})
        with patch('telemetry.os.name','nt'),patch('telemetry.command',return_value=payload):
            returned,devices,detail=c._wmi_read()
        self.assertEqual(len(returned),6);self.assertEqual(devices,[]);self.assertEqual(detail['warnings'],['Hardware metadata unavailable'])

    def test_empty_http_and_wmi_is_failure(self):
        c=Collector()
        with patch('telemetry.read_http',side_effect=ValueError('empty')),patch.object(c,'_wmi_read',side_effect=RuntimeError('0 sensors')):
            rows,_,_=c._lhm()
        self.assertEqual(rows,[]);self.assertFalse(c.diagnostics['connected']);self.assertEqual(len(c.diagnostics['attempts']),2)

if __name__=='__main__':unittest.main()
