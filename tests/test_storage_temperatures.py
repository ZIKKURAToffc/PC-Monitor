import copy
import unittest
from unittest.mock import patch
from lhm_bridge import parse_tree
from telemetry import Collector,normalize_temperatures,temperature_summary,is_temperature_limit

FIXTURE={'Children':[{'HardwareId':'/nvme/0','Text':'Synthetic NVMe SSD','Children':[
 {'SensorId':'/nvme/0/temperature/0','Type':'Temperature','Text':'Composite Temperature','RawValue':'30,0 °C'},
 {'SensorId':'/nvme/0/temperature/1','Type':'Temperature','Text':'Temperature #1','RawValue':'29,9 °C'},
 {'SensorId':'/nvme/0/temperature/2','Type':'Temperature','Text':'Temperature #2','RawValue':'43,9 °C'},
 {'SensorId':'/nvme/0/temperature/10','Type':'Temperature','Text':'Warning Temperature','RawValue':'82,0 °C'},
 {'SensorId':'/nvme/0/temperature/11','Type':'Temperature','Text':'Critical Temperature','RawValue':'89,0 °C'}]}]}

class StorageTemperatureTests(unittest.TestCase):
 def test_limits_are_not_live_temperatures(self):
  rows,devices=parse_tree(FIXTURE);temps=normalize_temperatures(rows,devices)
  self.assertEqual(len(temps),3);self.assertEqual(temperature_summary(temps)['disk_temp'],43.9)
  self.assertFalse(any(t['value']>=85 for t in temps))
 def test_max_is_not_automatically_a_limit(self):
  self.assertTrue(is_temperature_limit('Critical Temperature'))
  self.assertTrue(is_temperature_limit('Warning Composite Temperature'))
  self.assertFalse(is_temperature_limit('Temperature #2'))
  self.assertFalse(is_temperature_limit('Temperature Max'))
  self.assertFalse(is_temperature_limit('GPU Hot Spot'))
 def test_two_polls_update_current_temperature_not_firmware_limits(self):
  changed=copy.deepcopy(FIXTURE);changed['Children'][0]['Children'][2]['RawValue']='45,1 °C'
  first,devices=parse_tree(FIXTURE);second,_=parse_tree(changed)
  c=Collector();c.nv=None
  with patch.object(c,'_lhm',side_effect=[(first,devices,'fixture'),(second,devices,'fixture')]),patch('telemetry.psutil.sensors_temperatures',return_value={},create=True):
   a=c._hardware_once();b=c._hardware_once()
  self.assertEqual(a['disk_temp'],43.9);self.assertEqual(b['disk_temp'],45.1)
  self.assertEqual(sum(r['is_limit'] for r in b['sensor_rows']),2)
 def test_limit_cannot_be_assigned_as_cpu_temperature(self):
  rows,_=parse_tree(FIXTURE);c=Collector();c.configure(mapping={'cpu_temp':'/nvme/0/temperature/11'})
  value,label=c.choose_sensor(rows,'cpu_temp','Temperature','cpu',['Package'])
  self.assertIsNone(value)
 def test_limit_index_is_not_hard_coded(self):
  changed=copy.deepcopy(FIXTURE);changed['Children'][0]['Children'][4]['SensorId']='/nvme/0/temperature/7'
  rows,devices=parse_tree(changed);temps=normalize_temperatures(rows,devices)
  self.assertEqual(len(temps),3)

if __name__=='__main__':unittest.main()
