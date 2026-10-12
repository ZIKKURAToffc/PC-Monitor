"""Drag a normal window from non-interactive header areas, never from data/controls."""
from PySide6.QtCore import QObject,QEvent,Qt,QPoint
from PySide6.QtWidgets import QWidget

class HeaderDragController(QObject):
    def __init__(self,window,root,targets):
        super().__init__(window);self.window=window;self.root=root;self.targets=set(targets);self.dragging=False;self.grabber=None;self.offset=QPoint();self.old_cursor=None
        window.installEventFilter(self)
        for widget in self.targets:widget.installEventFilter(self)
        self.update_cursors()
    def allowed(self):return not (self.window.isFullScreen() or getattr(self.window,'_fullscreen_requested',False))
    def update_cursors(self):
        for widget in self.targets:
            if widget is not self.root:widget.setCursor(Qt.OpenHandCursor if self.allowed() else Qt.ArrowCursor)
    def in_header(self,widget,point):
        if widget not in self.targets:return False
        local=widget.mapTo(self.root,point)
        bottom=self.window.gear_button.mapTo(self.root,QPoint(0,self.window.gear_button.height())).y()
        return 0<=local.y()<=bottom and 0<=local.x()<self.root.width()
    def native_move(self):
        handle=self.window.windowHandle()
        if handle is None:return False
        try:return bool(handle.startSystemMove())
        except (RuntimeError,AttributeError):return False
    def begin_manual(self,widget,global_position):
        if self.window.isMaximized():
            old=self.window.frameGeometry();ratio=(global_position.x()-old.left())/max(1,old.width());dy=min(48,max(0,global_position.y()-old.top()))
            self.window.showNormal();self.window.move(global_position.x()-round(self.window.width()*ratio),global_position.y()-dy)
        self.offset=global_position-self.window.pos();self.dragging=True;self.grabber=widget;self.old_cursor=widget.cursor();widget.setCursor(Qt.ClosedHandCursor);widget.grabMouse()
    def cancel(self):
        widget=self.grabber;self.dragging=False;self.grabber=None
        if widget is not None:
            if self.old_cursor is not None:widget.setCursor(self.old_cursor)
            if QWidget.mouseGrabber() is widget:widget.releaseMouse()
        self.old_cursor=None
    def eventFilter(self,widget,event):
        kind=event.type()
        if kind==QEvent.UngrabMouse and widget is self.grabber:
            self.cancel();return False
        if kind in (QEvent.Hide,QEvent.WindowDeactivate) and widget is self.window:
            self.cancel();return False
        if kind==QEvent.MouseButtonRelease and self.dragging and event.button()==Qt.LeftButton:
            self.cancel();return True
        if kind==QEvent.MouseMove and self.dragging:
            if not self.allowed() or not (event.buttons()&Qt.LeftButton):self.cancel();return False
            self.window.move(event.globalPosition().toPoint()-self.offset);return True
        if kind==QEvent.MouseButtonPress and event.button()==Qt.LeftButton and self.allowed() and self.in_header(widget,event.position().toPoint()):
            self.cancel()
            if not self.native_move():self.begin_manual(widget,event.globalPosition().toPoint())
            return True
        return super().eventFilter(widget,event)
