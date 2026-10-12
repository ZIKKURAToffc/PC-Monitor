"""Validate persistent values without resetting unrelated user preferences."""
import math

def bounded_int(value,default,low,high,choices=None):
    try:
        if isinstance(value,bool):raise ValueError('boolean is not an interval')
        number=float(value)
        if not math.isfinite(number) or not number.is_integer():raise ValueError('not an integer')
        result=int(number)
    except (TypeError,ValueError,OverflowError):return default
    if not low<=result<=high or choices is not None and result not in choices:return default
    return result

def source_mode(value):return value if isinstance(value,str) and value in ('aida','auto','http','wmi') else 'aida'
