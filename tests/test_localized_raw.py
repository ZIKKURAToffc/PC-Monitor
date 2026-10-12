import unittest
from lhm_bridge import parse_tree,raw_sensor_value
from telemetry import temperature_summary,normalize_temperatures,Collector

class LocalizedRawTests(unittest.TestCase):
    def test_formatted_raw_celsius_watts_and_rpm(self):
        self.assertEqual(raw_sensor_value('32,5 °C','Temperature'),32.5)
        self.assertEqual(raw_sensor_value('101,4 W','Power'),101.4)
        self.assertEqual(raw_sensor_value('1594 RPM','Fan'),1594)
        self.assertEqual(raw_sensor_value('0 RPM','Fan'),0)
        self.assertEqual(raw_sensor_value('4066,0 MHz','Clock'),4066)
        self.assertEqual(raw_sensor_value('2211,0 MB','SmallData'),2211)
    def test_null_does_not_fall_back_to_formatted_value(self):
        rows,_=parse_tree({'Children':[{'SensorId':'/amdcpu/0/temperature/0','Type':'Temperature','Text':'Core (Tctl/Tdie)','RawValue':None,'Value':'0 °C'}]})
        self.assertIsNone(rows[0]['Value'])
        self.assertIsNone(raw_sensor_value('NaN','Temperature'))
        self.assertIsNone(raw_sensor_value(False,'Power'))
    def test_localized_numeric_strings_and_fahrenheit(self):
        self.assertEqual(raw_sensor_value('32,5','Temperature'),32.5)
        self.assertAlmostEqual(raw_sensor_value('116,6 °F','Temperature'),47)
        self.assertEqual(raw_sensor_value('1,594 RPM','Fan'),1594)
        self.assertIsNone(raw_sensor_value('40 %','Fan'))
    def test_cpu_package_aggregate_is_not_per_core_max(self):
        rows,_=parse_tree({'Children':[{'SensorId':'/amdcpu/0/temperature/0','Type':'Temperature','Text':'Core (Tctl/Tdie)','RawValue':'54,1 °C'}]})
        result=temperature_summary(normalize_temperatures(rows))
        self.assertEqual(result['cpu_temp'],54.1);self.assertIsNone(result['cpu_core_max'])

if __name__=='__main__':unittest.main()
