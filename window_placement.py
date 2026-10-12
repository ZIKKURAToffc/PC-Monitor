"""Persistent normal-window placement, with disconnected-monitor recovery."""
from PySide6.QtCore import QRect,Qt
from PySide6.QtWidgets import QApplication

RECT_KEY='window_normal_rect_v1'
MAX_KEY='window_maximized_v1'

def fitted_rect(rect,areas):
    areas=[QRect(a) for a in areas if a.isValid()]
    if not areas:return QRect(rect)
    rect=QRect(rect)
    def overlap(area):
        hit=rect.intersected(area)
        return max(0,hit.width())*max(0,hit.height()) if hit.isValid() else 0
    area=max(areas,key=overlap)
    width=min(rect.width(),area.width());height=min(rect.height(),area.height())
    x=min(max(rect.x(),area.x()),area.right()-width+1)
    y=min(max(rect.y(),area.y()),area.bottom()-height+1)
    return QRect(x,y,width,height)

def screen_areas():
    primary=QApplication.primaryScreen();screens=QApplication.screens()
    if primary in screens:screens=[primary]+[s for s in screens if s is not primary]
    return [s.availableGeometry() for s in screens]

def restore_placement(window,settings):
    raw=settings.value('geometry',b'')
    try:restored=bool(raw) and window.restoreGeometry(raw)
    except (TypeError,ValueError):restored=False
    saved=settings.value(RECT_KEY)
    if isinstance(saved,QRect) and saved.isValid():rect=QRect(saved);restored=True
    else:rect=window.normalGeometry() if restored else QRect()
    maximized=str(settings.value(MAX_KEY,window.isMaximized())).lower() in ('true','1')
    window.setWindowState(window.windowState()&~(Qt.WindowMinimized|Qt.WindowFullScreen|Qt.WindowMaximized))
    areas=screen_areas()
    if not rect.isValid():
        area=areas[0] if areas else QRect(0,0,1180,1000)
        width=min(window.width(),max(520,area.width()-40));height=min(window.height(),max(440,area.height()-60))
        rect=QRect(area.x()+max(0,(area.width()-width)//2),area.y()+max(0,(area.height()-height)//2),width,height)
        maximized=False
    rect=fitted_rect(rect,areas);window.setGeometry(rect)
    if maximized:window.setWindowState(window.windowState()|Qt.WindowMaximized)
    return QRect(rect),maximized

def ensure_frame_visible(window):
    if window.isFullScreen() or window.isMaximized() or window.isMinimized():return
    frame=window.frameGeometry();fixed=fitted_rect(frame,screen_areas())
    if frame==fixed:return
    geometry=window.geometry();left=geometry.x()-frame.x();top=geometry.y()-frame.y()
    horizontal=frame.width()-geometry.width();vertical=frame.height()-geometry.height()
    window.setGeometry(fixed.x()+left,fixed.y()+top,max(window.minimumWidth(),fixed.width()-horizontal),max(window.minimumHeight(),fixed.height()-vertical))
