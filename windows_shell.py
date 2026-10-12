"""Windows shell integration without hiding or minimizing the application window."""
import ctypes,os
GWL_EXSTYLE=-20
WS_EX_TOOLWINDOW=0x00000080
WS_EX_APPWINDOW=0x00040000
SWP_NO_SIZE_MOVE_ACTIVATE=0x0001|0x0002|0x0004|0x0010|0x0020

def taskbar_style(original):
    return (original|WS_EX_TOOLWINDOW)&~WS_EX_APPWINDOW

def hide_taskbar_entry(hwnd):
    if os.name!='nt':return {'state':'unsupported','hidden_from_taskbar':False}
    original=None;changed=False;setter=None
    try:
        u=ctypes.WinDLL('user32',use_last_error=True)
        getter=u.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p)==8 else u.GetWindowLongW
        setter=u.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p)==8 else u.SetWindowLongW
        getter.argtypes=[ctypes.c_void_p,ctypes.c_int];getter.restype=ctypes.c_ssize_t
        setter.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_ssize_t];setter.restype=ctypes.c_ssize_t
        u.SetWindowPos.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_uint32];u.SetWindowPos.restype=ctypes.c_int
        ctypes.set_last_error(0);original=getter(hwnd,GWL_EXSTYLE)
        if not original and ctypes.get_last_error():raise OSError(ctypes.get_last_error(),'GetWindowLongPtr')
        desired=taskbar_style(original)
        if desired!=original:
            ctypes.set_last_error(0);previous=setter(hwnd,GWL_EXSTYLE,desired)
            if not previous and ctypes.get_last_error():raise OSError(ctypes.get_last_error(),'SetWindowLongPtr')
            changed=True
            if not u.SetWindowPos(hwnd,None,0,0,0,0,SWP_NO_SIZE_MOVE_ACTIVATE):raise OSError(ctypes.get_last_error(),'SetWindowPos')
        return {'state':'applied','hidden_from_taskbar':True}
    except Exception as e:
        if changed and setter is not None and original is not None:
            try:setter(hwnd,GWL_EXSTYLE,original)
            except Exception:pass
        return {'state':'failed','hidden_from_taskbar':False,'error':type(e).__name__}
