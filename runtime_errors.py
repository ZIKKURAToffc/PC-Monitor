"""Local bounded error logs for GUI builds without a console; no telemetry uploads."""
import logging,logging.handlers,os,sys,tempfile,threading,time
from pathlib import Path
LOGGER=logging.getLogger('pc_monitor.errors')
LOG_PATH=None
_LAST_DIALOG=float('-inf')

def setup_log(base=None):
    global LOG_PATH
    if LOGGER.handlers and base is None:return LOG_PATH
    for handler in list(LOGGER.handlers):handler.close();LOGGER.removeHandler(handler)
    candidates=[Path(base)] if base is not None else [Path(os.environ.get('LOCALAPPDATA') or Path.home())/'PC-Monitor'/'logs',Path(tempfile.gettempdir())/'PC-Monitor-logs']
    LOG_PATH=None;LOGGER.propagate=False;LOGGER.setLevel(logging.ERROR)
    for directory in candidates:
        try:
            directory.mkdir(parents=True,exist_ok=True);path=directory/'errors.log'
            handler=logging.handlers.RotatingFileHandler(path,maxBytes=256*1024,backupCount=2,encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'));LOGGER.addHandler(handler);LOG_PATH=path;break
        except OSError:continue
    if not LOGGER.handlers:LOGGER.addHandler(logging.NullHandler())
    return LOG_PATH

def report_exception(kind,value,tb):
    global _LAST_DIALOG
    if issubclass(kind,(KeyboardInterrupt,SystemExit)):return
    try:LOGGER.error('Unhandled exception',exc_info=(kind,value,tb))
    except Exception:pass
    now=time.monotonic()
    if now-_LAST_DIALOG<60:return
    try:
        from PySide6.QtWidgets import QApplication,QMessageBox
        from PySide6.QtCore import QThread
        app=QApplication.instance()
        if app is not None and QThread.currentThread()==app.thread():
            _LAST_DIALOG=now
            message='An unexpected error occurred. Restart PC Monitor.\n'+('Error log: '+str(LOG_PATH) if LOG_PATH else 'The error log could not be written.')
            QMessageBox.warning(None,'PC Monitor',message)
    except Exception:pass

def install_hooks():
    setup_log();sys.excepthook=report_exception
    threading.excepthook=lambda args:report_exception(args.exc_type,args.exc_value,args.exc_traceback)
