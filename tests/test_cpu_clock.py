import unittest
from unittest.mock import patch
from lhm_bridge import parse_tree
from telemetry import Collector,select_cpu_clock,resolve_cpu_clock

def clock(identifier,name,value,parent='/amdcpu/0'):
 return {'Identifier':identifier,'Parent':parent,'SensorType':'Clock','Name':name,'Value':value}

class CpuClockTests(unittest.TestCase):
 def rows(self):
  return [clock('/amdcpu/0/clock/0','Bus Speed',100),clock('/amdcpu/0/clock/1','Cores (Average)',4066),
          clock('/amdcpu/0/clock/2','Cores (Average Effective)',545),clock('/amdcpu/0/clock/3','Fabric',1667),
          clock('/amdcpu/0/clock/4','Memory',1667),clock('/amdcpu/0/clock/5','Core #1',4900),
          clock('/amdcpu/0/clock/6','Core #1 (Effective)',912.5),clock('/gpu-nvidia/0/clock/0','GPU Core',2632,'/gpu-nvidia/0')]
 def test_reported_average_has_priority(self):
  value,label,kind=select_cpu_clock(self.rows());self.assertEqual(value,4066);self.assertEqual(label,'Cores (Average)');self.assertEqual(kind,'reported')
 def test_manual_effective_and_individual_core(self):
  value,label,kind=select_cpu_clock(self.rows(),'/amdcpu/0/clock/2');self.assertEqual(value,545);self.assertEqual(kind,'effective')
  self.assertEqual(select_cpu_clock(self.rows(),'/amdcpu/0/clock/5')[0],4900)
 def test_bus_memory_fabric_gpu_are_not_cpu_core_frequency(self):
  rows=[r for r in self.rows() if r['Name'] in ['Bus Speed','Fabric','Memory','GPU Core']]
  self.assertIsNone(select_cpu_clock(rows)[0]);self.assertIsNone(select_cpu_clock(self.rows(),'/amdcpu/0/clock/0')[0])
 def test_calculated_average_does_not_mix_effective_or_other_cpu(self):
  rows=[clock('/intelcpu/0/clock/0','CPU Core #1',4000,'/intelcpu/0'),clock('/intelcpu/0/clock/1','CPU Core #2',5000,'/intelcpu/0'),
        clock('/intelcpu/0/clock/2','CPU Core #1 (Effective)',500,'/intelcpu/0'),clock('/intelcpu/1/clock/0','CPU Core #1',9000,'/intelcpu/1')]
  value,label,kind=select_cpu_clock(rows);self.assertEqual(value,4500);self.assertIn('2, расчёт',label);self.assertEqual(kind,'reported')
 def test_live_clock_is_never_overwritten_by_nominal_os_value(self):
  s={'cpu_clock':4066,'cpu_clock_kind':'reported','cpu_clock_source':'LHM','sensor_labels':{'cpu_clock':'Cores (Average)'}}
  self.assertEqual(resolve_cpu_clock(s,3401,True)[0],4066);self.assertEqual(resolve_cpu_clock(s,3401,False)[0],4066)
 def test_missing_and_zero_effective(self):
  self.assertIsNone(resolve_cpu_clock({},3401,False)[0]);self.assertEqual(resolve_cpu_clock({},3401,True)[2],'ОС / psutil')
  s={'cpu_clock':0,'cpu_clock_kind':'effective'};self.assertEqual(resolve_cpu_clock(s,3401,True)[0],0)
  self.assertIsNone(select_cpu_clock(self.rows(),'/amdcpu/0/clock/not-present')[0])
 def test_two_polls_update_lhm_clock_with_fixed_os_clock(self):
  def fixture(value):return {'Children':[{'HardwareId':'/amdcpu/0','Text':'Synthetic CPU','Children':[{'SensorId':'/amdcpu/0/clock/1','Type':'Clock','Text':'Cores (Average)','RawValue':value}]}]}
  first,devices=parse_tree(fixture('4066,0 MHz'));second,_=parse_tree(fixture('4490,0 MHz'))
  c=Collector();c.nv=None
  with patch.object(c,'_lhm',side_effect=[(first,devices,'fixture'),(second,devices,'fixture')]),patch('telemetry.psutil.sensors_temperatures',return_value={},create=True):
   a=c._hardware_once();b=c._hardware_once()
  self.assertEqual(resolve_cpu_clock(a,3401,False)[0],4066);self.assertEqual(resolve_cpu_clock(b,3401,False)[0],4490)

if __name__=='__main__':unittest.main()
