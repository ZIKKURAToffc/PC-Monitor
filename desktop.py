"""PC Monitor Desktop: native Qt widgets, no browser or HTTP server."""
import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from PySide6.QtCore import Qt, QPoint, QRect, QTimer, QSettings, QProcess, QUrl, QSize
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QPainterPath, QIcon, QPixmap, QDesktopServices, QShortcut, QKeySequence, QActionGroup, QLinearGradient
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QBoxLayout, QTabWidget, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QComboBox, QSpinBox,
    QDialogButtonBox, QFileDialog, QMessageBox, QCheckBox, QFrame, QLineEdit, QPlainTextEdit, QSizePolicy, QToolButton, QMenu, QSystemTrayIcon)
from i18n import t as tr, set_language, localize_tree
import i18n
from telemetry import Collector, finite, group_for
from fps_diagnostics import inspect_fps, FPS_GUIDE, status_caption
from shiboken6 import isValid
from characters import CharacterPortrait,CHARACTERS,THEME_PROFILES,valid_character,character_name,header_region,portrait
from windows_shell import hide_taskbar_entry
from window_drag import HeaderDragController
from window_placement import restore_placement,ensure_frame_visible,RECT_KEY,MAX_KEY
from autostart import current_status as autostart_status,set_enabled as set_autostart
from clock_display import clock_data
from themes import THEMES,valid_theme,set_active_theme,theme_color,style_widget,restyle_widgets,theme_name,theme_description,emblem,ThemePreview,set_visual_effects,effects_active
from dashboard import SLOTS, available_rows, compatible, matches_slot, apply_config,normalize_config,MAX_CUSTOM_CARDS
from settings_validation import bounded_int,source_mode
from runtime_errors import install_hooks

from app_metadata import APP_VERSION
DEFAULT_TITLE='PC MONITOR'
DEVELOPER_NAME='ZIKKURAT'

CYAN='#18ffe0'; RED='#ff442d'; WARNING='#ff7777'; BG='#060b09'; MUTED='#99b5ab'
STYLE='''
QWidget {background:#060b09;color:#18ffe0;font-family:Arial;font-size:13px;}
QMainWindow {background:#060b09;}
Metric QLabel {background:transparent;}
QLabel#subtle {color:#99b5ab;font-family:Consolas;font-size:12px;}
QLabel#brand {font-size:34px;font-weight:900;letter-spacing:3px;}
QLabel#clock {font-family:Consolas;font-size:23px;font-weight:bold;}
QPushButton {border:1px solid #32574a;background:#0b1711;padding:10px 15px;min-height:20px;}
QPushButton:hover {border-color:#18ffe0;background:#123a2a;}
QPushButton:focus {border:1px solid #18ffe0;}
QPushButton:checked {background:#174631;}
QTabWidget::pane {border:0;}
QTabBar::tab {padding:12px 20px;background:#0b1711;color:#99b5ab;border-bottom:2px solid #254337;margin-right:6px;}
QTabBar::tab:selected {color:#18ffe0;border-bottom:2px solid #18ffe0;background:#143328;}
QScrollArea {border:0;}
QScrollBar:vertical {background:#101e17;width:10px;margin:0;}
QScrollBar::handle:vertical {background:#3b6654;min-height:30px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QTableWidget {border:1px solid #32574a;gridline-color:#214130;background:#0a140f;alternate-background-color:#102219;selection-background-color:#21523f;}
QHeaderView::section {background:#163529;color:#18ffe0;border:0;border-bottom:1px solid #32574a;padding:10px;font-size:12px;}
QTableWidget::item {padding:7px;}
QLineEdit {padding:9px;background:#11251b;border:1px solid #426851;min-height:22px;}
QPlainTextEdit {border:1px solid #32574a;padding:8px;}
QComboBox,QSpinBox {padding:9px;background:#11251b;border:1px solid #426851;min-height:22px;}
QComboBox QAbstractItemView {background:#11251b;selection-background-color:#27503c;}
QDialog {background:#0a140f;}
QToolTip {background:#15372a;color:#18ffe0;border:1px solid #18ffe0;padding:8px;}
QToolButton#controlGear {border:0;outline:0;background:transparent;padding:0;color:#18ffe0;}
QToolButton#controlGear:hover,QToolButton#controlGear:focus,QToolButton#controlGear:pressed,QToolButton#controlGear:checked {background:transparent;border:0;outline:0;}
QToolButton#controlGear::menu-indicator {image:none;width:0;height:0;}
QMenu {background:#0a140f;border:1px solid #426851;padding:4px;font-size:14px;}
QMenu::item {padding:14px 30px 14px 14px;color:#18ffe0;}
QMenu::item:selected {background:#174631;}
QMenu::indicator {width:14px;height:14px;}
QCheckBox {spacing:8px;}
QCheckBox::indicator {width:16px;height:16px;border:1px solid #99b5ab;background:#0b1711;}
QCheckBox::indicator:checked {background:#18ffe0;border:1px solid #18ffe0;}
'''

def strip_font(px,color='#06100b'):
    return f'background:transparent;font-family:Arial;font-size:{px}px;font-weight:900;color:{color};'

def fmt(value,dec=0):
    v=finite(value)
    return '—' if v is None else f'{v:,.{dec}f}'.replace(',',' ').replace('.',',' if i18n.LANG!='en' else '.')

def text(value,subtle=False):
    w=QLabel(value);w.setTextFormat(Qt.PlainText)
    if subtle:w.setObjectName('subtle')
    return w

def gear_icon():
    pix=QPixmap(48,48);pix.fill(Qt.transparent)
    p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing)
    path=QPainterPath()
    for i in range(64):
        angle=2*math.pi*i/64;radius=20 if i%8 in (2,3,4,5) else 16
        x=24+radius*math.cos(angle);y=24+radius*math.sin(angle)
        if i==0:path.moveTo(x,y)
        else:path.lineTo(x,y)
    path.closeSubpath();path.addEllipse(17,17,14,14);path.setFillRule(Qt.OddEvenFill)
    p.fillPath(path,QColor(theme_color(CYAN)));p.end();return QIcon(pix)

def clean_nickname(value):
    return ' '.join(str(value).split())[:48] or DEFAULT_TITLE

def clean_hardware_name(value):
    return ' '.join(str(value).split())[:80]

def display_application_name(name):
    name=str(name)
    return name[:-4] if name.lower().endswith('.exe') else name

class GearButton(QToolButton):
    """Paint only the icon: no button background or native focus/menu frame."""
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setPen(Qt.NoPen)
        size=self.iconSize();self.icon().paint(p,(self.width()-size.width())//2,(self.height()-size.height())//2,size.width(),size.height())

class ElideLabel(QLabel):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.setTextFormat(Qt.PlainText)
    compact=False
    def paintEvent(self,event):
        if not self.compact:return super().paintEvent(event)
        p=QPainter(self);p.setFont(self.font());p.setPen(QColor(theme_color(getattr(self,'text_color',MUTED))));caption=self.fontMetrics().elidedText(self.text(),Qt.ElideRight,self.width())
        p.drawText(self.rect(),Qt.AlignLeft|Qt.AlignVCenter,caption)

class Metric(QFrame):
    def __init__(self,label,unit,parent=None):
        super().__init__(parent)
        style_widget(self,'Metric {border:1px solid #ff442d;border-top:2px solid #ff442d;border-radius:6px;background:#0b1510;}')
        layout=QVBoxLayout(self);layout.setContentsMargins(14,10,14,10);layout.setSpacing(4)
        row=QHBoxLayout();self.label=ElideLabel(label);self.label.setObjectName('subtle');self.label.setWordWrap(True);self.label.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred);self.label.setMinimumHeight(18);row.addWidget(self.label,1);row.addWidget(text(unit,True));layout.addLayout(row)
        self.value_px=30;self.last_hot=False;self.value=text('—');style_widget(self.value,'font-family:Consolas;font-size:30px;font-weight:bold;')
        layout.addWidget(self.value)
        self.setMinimumHeight(85)
    def set_density(self,compact,tight=False):
        self.value_px=(20 if tight else 24) if compact else 30
        self.layout().setContentsMargins(10 if compact else 14,2 if tight else 4 if compact else 10,10 if compact else 14,2 if tight else 4 if compact else 10)
        self.layout().setSpacing(0 if compact else 4);self.setMinimumHeight((44 if tight else 56) if compact else 85)
        self.label.compact=compact;self.label.setWordWrap(not compact);self.label.setMinimumHeight(14 if compact else 18);self.label.update()
        style_widget(self.value,f'font-family:Consolas;font-size:{self.value_px}px;font-weight:bold;color:{WARNING if self.last_hot else CYAN};')

    def update_value(self,v,dec=0,hot=False):
        self.last_hot=hot;self.value.setText(fmt(v,dec));style_widget(self.value,f'font-family:Consolas;font-size:{self.value_px}px;font-weight:bold;color:{WARNING if hot else CYAN};')

class Graph(QWidget):
    def __init__(self,label,key,parent=None):
        super().__init__(parent);self.label=label;self.key=key;self.points=[];self.span=60;self.latest=None;self.now=time.time()
        self.setMinimumHeight(150);self.setMinimumWidth(280)
        self.setAccessibleName(label+' — история в процентах от 0 до 100')
    def push(self,t,v):
        t=finite(t);t=time.time() if t is None else t;v=finite(v)
        self.now=t;self.latest=v;self.points.append((t,v));self.points=[p for p in self.points if p[0]>=t-300];self.update()
        self.setToolTip(f'{self.label}\nСейчас: {fmt(v,1)} %\nИстория: {self.span} секунд. Шкала: 0–100 %.')
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);w=self.width();h=self.height()
        p.fillRect(self.rect(),QColor(theme_color('#090f0b')));p.setPen(QPen(QColor(theme_color(RED)),1));p.drawRect(0,0,w-1,h-1)
        p.setFont(QFont('Consolas',10));p.setPen(QColor(theme_color(MUTED)));p.drawText(12,18 if getattr(self,'compact',False) else 22,tr(self.label))
        p.setPen(QColor(theme_color(RED)));p.drawText(w-100,10 if getattr(self,'compact',False) else 22,88,20,Qt.AlignRight,fmt(self.latest,1)+' %')
        left=32 if getattr(self,'compact',False) else 36;right=w-12;top=30 if getattr(self,'compact',False) else 40;bottom=h-27
        p.setFont(QFont('Consolas',8))
        for val in [0,25,50,75,100]:
            y=bottom-val/100*(bottom-top);p.setPen(QPen(QColor(theme_color('#5e3021')),1,Qt.DotLine));p.drawLine(left,int(y),right,int(y))
            if val%50==0:p.setPen(QColor(theme_color(MUTED)));p.drawText(6,int(y+4),str(val))
        p.setPen(QColor(theme_color(MUTED)));p.drawText(12,h-9,f'−{self.span} '+('s' if i18n.LANG=='en' else 'с'));p.drawText(w-75,h-9,tr('СЕЙЧАС'))
        points=[pt for pt in self.points if pt[0]>=self.now-self.span];segments=[];segment=[]
        for t,v in points:
            if finite(v) is None:
                if segment:segments.append(segment);segment=[]
                continue
            x=left+(t-(self.now-self.span))/self.span*(right-left);y=bottom-max(0,min(100,v))/100*(bottom-top);segment.append((x,y))
        if segment:segments.append(segment)
        if not segments:
            p.setPen(QColor(theme_color(MUTED)));p.setFont(QFont('Arial',10));p.drawText(left,top,right-left,bottom-top,Qt.AlignCenter,tr('Нет данных'));return
        for segment in segments:
            path=QPainterPath();path.moveTo(*segment[0])
            for pt in segment[1:]:path.lineTo(*pt)
            p.setPen(QPen(QColor(theme_color(RED)),1.5));p.drawPath(path)
            area=QPainterPath(path);area.lineTo(segment[-1][0],bottom);area.lineTo(segment[0][0],bottom);area.closeSubpath();p.fillPath(area,QColor(theme_color('#33190f')))
            if effects_active():
                gradient=QLinearGradient(0,top,0,bottom);glow=QColor(theme_color(RED));glow.setAlpha(85);gradient.setColorAt(0,glow);glow.setAlpha(8);gradient.setColorAt(1,glow);p.fillPath(area,gradient)
                glow.setAlpha(45);p.setPen(QPen(glow,4));p.drawPath(path)
            p.setPen(QPen(QColor(theme_color(RED)),1.5));p.drawPath(path)

class HardwareSection(QWidget):
    def __init__(self,title,metrics,graph_key,graph_label):
        super().__init__();self.key=graph_key
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(12)
        header=QFrame();style_widget(header,'QFrame {background:#18ffe0;} QLabel {background:#18ffe0;color:#06100b;}')
        h=QHBoxLayout(header);self.header_layout=h;h.setContentsMargins(16,7,16,7)
        name=ElideLabel(title);name.compact=True;name.text_color='#06100b';name.setTextFormat(Qt.PlainText);name.setProperty('no_translate',True);name.setMinimumWidth(45);name.setMaximumWidth(500);self.title_label=name;style_widget(name,strip_font(24));h.addWidget(name);slashes=text('//////');self.slash_label=slashes;style_widget(slashes,strip_font(24));h.addWidget(slashes)
        self.temp_px=24;self.temp_hot=False;self.temp=text('— °C');style_widget(self.temp,strip_font(24));h.addWidget(self.temp)
        h.addStretch();self.detail=text('');style_widget(self.detail,strip_font(24));h.addWidget(self.detail);layout.addWidget(header)
        row=QHBoxLayout();self.responsive_row=row;row.setSpacing(16);self.graph=Graph(graph_label,graph_key);row.addWidget(self.graph,3)
        grid=QGridLayout();self.metric_grid=grid;grid.setSpacing(10);self.metrics={}
        for i,(key,label,unit) in enumerate(metrics):
            metric=Metric(label,unit);grid.addWidget(metric,i//2,i%2);self.metrics[key]=metric
        grid_widget=QWidget();grid_widget.setLayout(grid);grid.setContentsMargins(0,0,0,0);row.addWidget(grid_widget,2);layout.addLayout(row,1)
    def set_density(self,compact,tight=False):
        self.temp_px=18 if compact else 24
        self.layout().setSpacing(6 if compact else 12);self.responsive_row.setSpacing(10 if compact else 16);self.metric_grid.setSpacing(4 if compact else 10)
        self.header_layout.setContentsMargins(12 if compact else 16,3 if compact else 7,12 if compact else 16,3 if compact else 7)
        style_widget(self.title_label,strip_font(self.temp_px));style_widget(self.slash_label,strip_font(self.temp_px));style_widget(self.detail,strip_font(self.temp_px))
        style_widget(self.temp,strip_font(self.temp_px,'#942014' if self.temp_hot else '#06100b'))
        self.graph.compact=compact;self.graph.setMinimumHeight((88 if tight else 110) if compact else 150);self.graph.setMinimumWidth(200 if compact else 280)

    def update_data(self,d,threshold):
        self.temp_hot=(finite(d.get(self.key+'_temp')) or -999)>=threshold
        self.temp.setText(fmt(d.get(self.key+'_temp'))+' °C')
        style_widget(self.temp,strip_font(self.temp_px,'#942014' if self.temp_hot else '#06100b'))
        for key,metric in self.metrics.items():metric.update_value(d.get(key),1 if key.endswith('power') or key.startswith('ram_') else 0)
        if self.key=='cpu':self.detail.setProperty('no_translate',True);self.detail.setText(f'{d.get("cores") or "—"} '+tr('ядер')+f' / {d.get("threads") or "—"} '+tr('потоков'))
        else:
            self.detail.setProperty('no_translate',True);self.detail.setText(tr('ПАМЯТЬ GPU')+' '+fmt(d.get('gpu_mem_temp'))+' °C')
            self.detail.setToolTip(tr('Температура памяти GPU')+'\n'+tr('Источник')+': '+str(d.get('sensor_labels',{}).get('gpu_mem_temp') or tr('Авто / стандартный источник')))

class MonitorWindow(QMainWindow):
    def __init__(self,demo=False,collector=None,tray_mode=None):
        super().__init__();self._placement_ready=False;self._mode_changing=False;self._first_placement_show=True;self._last_normal_rect=None;self.demo=demo;self.collector=collector or Collector();self.current={};self.paused=False;self.last_timestamp=None
        self.tray_requested=(os.name=='nt') if tray_mode is None else bool(tray_mode);self.tray_icon=None;self.tray_enabled=False;self.shell_report={'state':'normal-window','hidden_from_taskbar':False}
        self.settings=QSettings('Zikkurat','DesktopMonitor');self._fullscreen_requested=False;self._normal_window_geometry=None;self._normal_was_maximized=False;mode=source_mode(self.settings.value('sensor_source_mode',self.settings.value('lhm_mode','aida')));prefix='aida_sensor_' if mode=='aida' else 'sensor_';self.collector.configure(mode=mode,port=bounded_int(self.settings.value('lhm_port',8085),8085,1,65535),mapping={k:str(self.settings.value(prefix+k,'')) for k in ['cpu_temp','cpu_clock','cpu_power','cpu_rpm','gpu_rpm']});self.interval=bounded_int(self.settings.value('interval',500),500,250,5000,(250,500,1000,2000,5000));self.history_span=bounded_int(self.settings.value('history',60),60,60,300,(60,120,300));self.threshold=bounded_int(self.settings.value('threshold',85),85,30,120);self.peaks={};self.troughs={}
        self.theme_id=valid_theme(str(self.settings.value('interface_theme','classic')));set_active_theme(self.theme_id)
        self.characters_enabled=str(self.settings.value('show_characters','true')).lower() not in ('false','0')
        self.effects_enabled=str(self.settings.value('anime_effects','true')).lower() not in ('false','0')
        self.animation_enabled=str(self.settings.value('anime_animation','true')).lower() not in ('false','0')
        self.character_choices={key:valid_character(key,self.settings.value('theme_character/'+key)) for key in THEME_PROFILES}
        set_visual_effects(self.effects_enabled)
        self.collector.set_poll_interval(self.settings.value('sensor_poll_ms',500))
        self.hardware_names={key:clean_hardware_name(self.settings.value('display_hardware_'+key,'')) for key in ('cpu','gpu','board')}
        # Preserve the legacy settings namespace; only migrate the former default title once.
        if str(self.settings.value('neutral_branding_v1','false')).lower() not in ('true','1'):
            if clean_nickname(self.settings.value('display_name',DEFAULT_TITLE)).casefold()==DEVELOPER_NAME.casefold():self.settings.setValue('display_name',DEFAULT_TITLE)
            self.settings.setValue('neutral_branding_v1',True)
        self.language=str(self.settings.value('language','ru'));set_language(self.language);self.language=i18n.LANG;self.nickname=clean_nickname(self.settings.value('display_name',DEFAULT_TITLE));self.setProperty('no_translate',True);self.setWindowTitle(self.nickname+' Desktop '+APP_VERSION+' — '+tr('Мониторинг ПК'));self.resize(1180,1000);self.setMinimumSize(520,440)
        icon=QPixmap(64,64);icon.fill(QColor(theme_color(BG)));p=QPainter(icon);p.setPen(QPen(QColor(theme_color(CYAN)),6));p.drawLine(12,12,52,52);p.drawLine(52,12,12,52);p.end();self.setWindowIcon(QIcon(icon))
        try:self.dashboard_config=json.loads(str(self.settings.value('dashboard_config_v1','{}')))
        except (ValueError,TypeError):self.dashboard_config={}
        self.dashboard_config=normalize_config(self.dashboard_config)
        # Migrate old five backend selections to the single validated dashboard mapping.
        legacy=dict(self.collector.mapping)
        if any(legacy.values()):
            slots=self.dashboard_config.setdefault('slots',{})
            for key,sid in legacy.items():
                if sid:slots.setdefault(key,{}).setdefault('sensor',sid)
            self.settings.setValue('dashboard_config_v1',json.dumps(self.dashboard_config,ensure_ascii=False))
            for key in legacy:self.settings.setValue(prefix+key,'')
            self.collector.configure(self.collector.source_mode,self.collector.port,self.collector.username,self.collector.password,{})
        self.custom_widgets=[];self.compact_mode=str(self.settings.value('compact_original','true')).lower()!='false'
        self.build_ui();self.apply_theme(self.theme_id,persist=False);self.update_hardware_titles()
        self.setWindowFlag(Qt.WindowStaysOnTopHint,str(self.settings.value('always_on_top','false')).lower() in ('true','1'))
        self.placement_timer=QTimer(self);self.placement_timer.setSingleShot(True);self.placement_timer.setInterval(400);self.placement_timer.timeout.connect(self.save_window_placement)
        self.rebuild_custom_cards();self.adapt_layout();self.apply_span();self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(self.interval)
        self.clock_timer=QTimer(self);self.clock_timer.timeout.connect(self.update_clock);self.clock_timer.start(1000);self.update_clock()
        for key,slot in [('F11',self.toggle_fullscreen),('Escape',self.escape),('Space',self.toggle_pause)]:QShortcut(QKeySequence(key),self,activated=slot)
        if self.demo:
            now=time.time()
            for g in self.graphs.values():
                for i in range(60,0,-1):g.push(now-i,24+8*math.sin(i*.7) if g.key=='cpu' else 10+4*math.sin(i*.3) if g.key=='gpu' else 23.8)
        else:self.collector.start()
        self.setup_tray();self._last_normal_rect,self._normal_was_maximized=restore_placement(self,self.settings);self.refresh();self._initial_placement_size=self.size();self._placement_ready=True

    def setup_tray(self):
        if not self.tray_requested or not QSystemTrayIcon.isSystemTrayAvailable():return
        self.tray_menu=QMenu(self);self.tray_menu.setObjectName('trayMenu')
        self.tray_show=self.tray_menu.addAction('Показать окно');self.tray_show.triggered.connect(self.show_from_tray)
        self.tray_pause=self.tray_menu.addAction('Пауза');self.tray_pause.triggered.connect(self.toggle_pause)
        self.tray_settings=self.tray_menu.addAction('Настройки');self.tray_settings.triggered.connect(self.show_settings)
        self.tray_menu.addSeparator();self.tray_exit=self.tray_menu.addAction('Выход');self.tray_exit.triggered.connect(self.request_exit)
        self.tray_menu.aboutToShow.connect(self.sync_tray_menu)
        self.tray_icon=QSystemTrayIcon(self.windowIcon(),self);self.tray_icon.setContextMenu(self.tray_menu);self.tray_icon.setToolTip(self.nickname+' '+APP_VERSION)
        self.tray_icon.activated.connect(self.tray_activated);self.tray_icon.show();self.tray_enabled=True
        # Keep a normal visible window frame, but prevent accidental title-bar minimization.
        self.setWindowFlag(Qt.WindowMinimizeButtonHint,False)
        self.sync_tray_menu()

    def sync_tray_menu(self):
        if not self.tray_enabled:return
        self.tray_pause.setText('Продолжить' if self.paused else 'Пауза');localize_tree(self.tray_menu)
        self.tray_icon.setToolTip(self.nickname+' '+APP_VERSION)

    def tray_activated(self,reason):
        if reason in (QSystemTrayIcon.Trigger,QSystemTrayIcon.DoubleClick):self.show_from_tray()

    def show_from_tray(self):
        if self._fullscreen_requested:self.showFullScreen()
        elif self.isMinimized():self.showNormal()
        else:self.show()
        self.apply_shell_style();self.raise_();self.activateWindow()

    def request_exit(self):
        if self.close():QApplication.instance().quit()

    def apply_shell_style(self):
        if not isValid(self) or not self.tray_enabled:return
        self.shell_report=hide_taskbar_entry(int(self.winId()))

    def showEvent(self,event):
        super().showEvent(event)
        self.apply_shell_style()
        if self._placement_ready and self._first_placement_show:
            self._first_placement_show=False
            # Only constrain the startup placement, not an explicit resize requested before show.
            if self.size()==self._initial_placement_size:
                QTimer.singleShot(0,lambda:ensure_frame_visible(self) if isValid(self) and self.size()==self._initial_placement_size else None)

    def track_window_placement(self):
        if not self._placement_ready or self._mode_changing:return
        if not (self._fullscreen_requested or self.isFullScreen() or self.isMaximized() or self.isMinimized()):
            self._last_normal_rect=QRect(self.geometry())
        self.placement_timer.start()

    def save_window_placement(self):
        if not self._placement_ready or self._mode_changing:return
        full=self._fullscreen_requested or self.isFullScreen()
        if not full and not self.isMaximized() and not self.isMinimized():self._last_normal_rect=QRect(self.geometry())
        rect=self._last_normal_rect
        if rect is not None and rect.isValid():self.settings.setValue(RECT_KEY,rect)
        self.settings.setValue(MAX_KEY,self._normal_was_maximized if full else self.isMaximized())
        self.settings.setValue('geometry',self._normal_window_geometry if full and self._normal_window_geometry else self.saveGeometry())
        self.settings.sync()

    def moveEvent(self,event):
        super().moveEvent(event);self.track_window_placement()

    def build_ui(self):
        root=QWidget();self.setCentralWidget(root);layout=QVBoxLayout(root);self.root_layout=layout;layout.setContentsMargins(24,18,24,16);layout.setSpacing(16)
        top=QHBoxLayout();title=ElideLabel(self.nickname);self.brand_label=title;title.compact=True;title.text_color=CYAN;title.setProperty('no_translate',True);title.setTextFormat(Qt.PlainText);title.setMinimumWidth(160);title.setMaximumWidth(500);title.setObjectName('brand');top.addWidget(title);self.version_label=text('/ DESKTOP '+APP_VERSION,True);top.addWidget(self.version_label);top.addStretch();self.clock=text('');self.clock.setObjectName('clock');self.clock.setAlignment(Qt.AlignRight|Qt.AlignVCenter);self.clock.setProperty('no_translate',True)
        self.clock_widget=QWidget();self.clock_widget.setMinimumWidth(205);self.clock_widget.setMaximumWidth(250);clock_layout=QVBoxLayout(self.clock_widget);clock_layout.setContentsMargins(0,0,0,0);clock_layout.setSpacing(0);clock_layout.addWidget(self.clock)
        self.clock_date=text('',True);self.clock_date.setObjectName('clockDate');self.clock_date.setProperty('no_translate',True);self.clock_date.setAlignment(Qt.AlignRight|Qt.AlignVCenter);clock_layout.addWidget(self.clock_date)
        self.clock_zone=text('',True);self.clock_zone.setObjectName('clockZone');self.clock_zone.setProperty('no_translate',True);self.clock_zone.setAlignment(Qt.AlignRight|Qt.AlignVCenter);self.clock_zone.setMinimumWidth(0);self.clock_zone.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred);clock_layout.addWidget(self.clock_zone);top.addWidget(self.clock_widget);layout.addLayout(top)
        toolbar=QHBoxLayout();toolbar.setSpacing(4);self.connection=text('Подключение…',True);self.connection.setWordWrap(False);self.connection.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Preferred);toolbar.addWidget(self.connection)
        self.control_menu=QMenu(self);self.control_menu.setObjectName('controlMenu')
        self.section_menu=self.control_menu.addMenu('Разделы');self.section_group=QActionGroup(self);self.section_group.setExclusive(True);self.section_actions=[]
        for index,caption in enumerate(['Обзор ресурсов','Температуры','Все датчики']):
            action=self.section_menu.addAction(caption);action.setCheckable(True);self.section_group.addAction(action);action.triggered.connect(lambda checked=False,index=index:self.tabs.setCurrentIndex(index));self.section_actions.append(action)
        self.section_actions[0].setChecked(True)
        self.pause_button=self.control_menu.addAction('Пауза');self.pause_button.triggered.connect(self.toggle_pause)
        for title,slot in [('Экспорт JSON',self.export_json),('Подключить датчики',self.sensor_help),('Панель / датчики',self.configure_dashboard),('Настройки',self.show_settings)]:
            self.control_menu.addAction(title).triggered.connect(slot)
        self.fullscreen_action=self.control_menu.addAction('Полный экран');self.fullscreen_action.setCheckable(True);self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        self.compact_button=self.control_menu.addAction('Компактно');self.compact_button.setCheckable(True);self.compact_button.setChecked(self.compact_mode);self.compact_button.triggered.connect(self.toggle_compact)
        self.gear_button=GearButton();self.gear_button.setObjectName('controlGear');self.gear_button.setIcon(gear_icon());self.gear_button.setIconSize(QSize(24,24));self.gear_button.setFixedSize(44,44);self.gear_button.setFocusPolicy(Qt.StrongFocus);self.gear_button.setAccessibleName('Меню управления мониторингом');self.gear_button.setToolTip('Управление: пауза, экспорт, датчики, настройки и вид окна');self.gear_button.setMenu(self.control_menu);self.gear_button.setPopupMode(QToolButton.InstantPopup)
        toolbar.addWidget(self.gear_button);self.theme_badge=QLabel();self.theme_badge.setObjectName('themeBadge');self.theme_badge.setProperty('no_translate',True);self.theme_badge.setFixedSize(30,30);toolbar.addWidget(self.theme_badge);toolbar.addStretch();layout.addLayout(toolbar)
        self.control_menu.aboutToShow.connect(self.sync_control_menu)
        self.demo_note=None
        if self.demo:
            note=text('ДЕМО: все значения синтетические. Реальный мониторинг запускается без --demo.');note.setWordWrap(True);style_widget(note,'background:#32170d;color:#ffc4ad;padding:10px;');self.demo_note=note;layout.addWidget(note)
        self.tabs=QTabWidget();self.tabs.tabBar().hide();layout.addWidget(self.tabs,1)
        overview=QWidget();ov=QVBoxLayout(overview);self.overview_layout=ov;ov.setSpacing(20);ov.setContentsMargins(0,16,10,16)
        self.cpu=HardwareSection('CPU', [('cpu_clock','ЧАСТОТА','MHz'),('cpu_power','МОЩНОСТЬ','W'),('cpu_usage','ЗАГРУЗКА','%'),('cpu_rpm','ВЕНТИЛЯТОР','RPM')],'cpu','ЗАГРУЗКА ПРОЦЕССОРА')
        self.gpu=HardwareSection('GPU',[('gpu_clock','ЧАСТОТА','MHz'),('gpu_power','МОЩНОСТЬ','W'),('gpu_usage','ЗАГРУЗКА','%'),('gpu_rpm','ВЕНТИЛЯТОР','RPM')],'gpu','ЗАГРУЗКА ВИДЕОКАРТЫ')
        ov.addWidget(self.cpu,1);ov.addWidget(self.gpu,1)
        self.sys_header=QFrame();style_widget(self.sys_header,'QFrame {background:#18ffe0;} QLabel {background:transparent;color:#06100b;}');self.sys_header_layout=QHBoxLayout(self.sys_header);self.sys_header_layout.setSpacing(10)
        self.syshead=ElideLabel('SYS  //////  ПАМЯТЬ И РЕСУРСЫ');self.syshead.setProperty('no_translate',True);self.syshead.setTextFormat(Qt.PlainText);self.syshead.compact=True;self.syshead.text_color='#06100b';self.syshead.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred);self.sys_header_layout.addWidget(self.syshead,1)
        self.board_caption=ElideLabel('ПЛАТА');self.board_caption.compact=True;self.board_caption.text_color='#06100b';self.board_caption.setMinimumWidth(40);self.board_caption.setMaximumWidth(220);self.board_caption.setTextFormat(Qt.PlainText);self.board_caption.setProperty('no_translate',True);self.sys_header_layout.addWidget(self.board_caption)
        self.board_temp=text('— °C');self.board_temp.setProperty('no_translate',True);self.board_temp_px=24;self.sys_header_layout.addWidget(self.board_temp)
        self.sys_section=QWidget();self.sys_section_layout=QVBoxLayout(self.sys_section);self.sys_section_layout.setContentsMargins(0,0,0,0);self.sys_section_layout.setSpacing(6);self.sys_section_layout.addWidget(self.sys_header);ov.addWidget(self.sys_section,1)
        mem=QHBoxLayout();self.memory_row=mem;self.ram_graph=Graph('ОПЕРАТИВНАЯ ПАМЯТЬ','ram');mem.addWidget(self.ram_graph,3)
        mg=QGridLayout();self.memory_grid=mg;mg.setSpacing(10);self.memory_metrics={}
        for i,(key,label) in enumerate([('ram_used','RAM ЗАНЯТО'),('ram_free','RAM ДОСТУПНО'),('vram_used','VRAM ЗАНЯТО'),('vram_free','VRAM СВОБОДНО')]):
            metric=Metric(label,'GiB');self.memory_metrics[key]=metric;mg.addWidget(metric,i//2,i%2)
        mgw=QWidget();mgw.setLayout(mg);mg.setContentsMargins(0,0,0,0);mem.addWidget(mgw,2);self.sys_section_layout.addLayout(mem,1)
        net=QHBoxLayout();self.network_row=net;self.upload=Metric('↑ ОТПРАВКА','KiB/s');self.download=Metric('↓ ЗАГРУЗКА','KiB/s');self.upload.setMinimumWidth(180);self.download.setMinimumWidth(180);net.addWidget(self.upload);net.addWidget(self.download);self.disk_label=text('ДИСКИ\nОжидание данных…',True);self.disk_label.setWordWrap(True);net.addWidget(self.disk_label,2);ov.addLayout(net)
        self.fps_metric=Metric('FPS / AIDA64 + RTSS','FPS');self.fps_metric.setToolTip('FPS из SRTSSFPS AIDA64. Нужен RTSS с обнаруженным 3D-приложением. «—» — нет данных; 0 — переданный ноль.')
        self.fps_status=text('',True);self.fps_status.setWordWrap(True);self.fps_status.setAlignment(Qt.AlignRight|Qt.AlignVCenter);self.fps_status.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred);self.fps_status.setProperty('no_translate',True)
        self.fps_metric.layout().removeWidget(self.fps_metric.value);fps_row=QHBoxLayout();fps_row.setContentsMargins(0,0,0,0);fps_row.setSpacing(12);fps_row.addWidget(self.fps_metric.value);self.fps_application=ElideLabel('');self.fps_application.setObjectName('fpsApplication');self.fps_application.compact=True;self.fps_application.setProperty('no_translate',True);self.fps_application.setTextFormat(Qt.PlainText);self.fps_application.setMinimumWidth(0);self.fps_application.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred);style_widget(self.fps_application,'background:transparent;font-family:Arial;font-size:12px;');fps_row.addWidget(self.fps_application,1);fps_row.addWidget(self.fps_status,1);self.fps_metric.layout().addLayout(fps_row)
        ov.insertWidget(0,self.fps_metric)
        self.custom_container=QWidget();self.custom_grid=QGridLayout(self.custom_container);self.custom_grid.setContentsMargins(0,0,0,0);self.custom_grid.setSpacing(12);ov.addWidget(self.custom_container)
        self.graphs={'cpu':self.cpu.graph,'gpu':self.gpu.graph,'ram':self.ram_graph}
        sc=QScrollArea();self.overview_scroll=sc;sc.setWidgetResizable(True);sc.setWidget(overview);self.tabs.addTab(sc,'Обзор ресурсов')
        thermal=QWidget();th=QVBoxLayout(thermal);th.setContentsMargins(0,16,10,0);th.setSpacing(16)
        intro=QHBoxLayout();intro.addWidget(text('ТЕМПЕРАТУРЫ / °C'));intro.addStretch();self.threshold_label=text('',True);intro.addWidget(self.threshold_label);th.addLayout(intro)
        cards=QGridLayout();self.thermal_grid=cards;cards.setSpacing(12);self.thermal_metrics={}
        thermal_defs=[('cpu_temp','CPU ТЕМПЕРАТУРА'),('gpu_temp','GPU CORE'),('gpu_mem_temp','GPU MEMORY'),('sys_temp','ПЛАТА'),('disk_temp','ДИСК MAX')]
        for i,(key,label) in enumerate(thermal_defs):
            card=Metric(label,'°C');self.thermal_metrics[key]=card;cards.addWidget(card,i//4,i%4)
        th.addLayout(cards)
        filter_row=QHBoxLayout();self.thermal_filter_row=filter_row;self.sensor_count=text('Ожидание датчиков…',True);filter_row.addWidget(self.sensor_count);filter_row.addStretch();filter_row.addWidget(text('Показать:',True));self.group_filter=QComboBox();[self.group_filter.addItem(group,group) for group in ['Все датчики','CPU','GPU','Плата','Накопитель','Другое']];self.group_filter.currentTextChanged.connect(self.update_thermal);filter_row.addWidget(self.group_filter);th.addLayout(filter_row)
        self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels(['Устройство / датчик','Сейчас, °C','Мин, °C','Макс, °C','Статус','Источник']);self.table.setAlternatingRowColors(True);self.table.setEditTriggers(QTableWidget.NoEditTriggers);self.table.setSelectionBehavior(QTableWidget.SelectRows);self.table.verticalHeader().hide();self.table.setWordWrap(False)
        header=self.table.horizontalHeader();header.setSectionResizeMode(0,QHeaderView.Stretch)
        for i,width in enumerate([0,90,85,85,145,160]):
            if i:header.setSectionResizeMode(i,QHeaderView.Interactive);self.table.setColumnWidth(i,width)
        self.table.setMinimumHeight(180);th.addWidget(self.table,1)
        self.empty_message=text('');self.empty_message.setWordWrap(True);self.empty_message.setMinimumHeight(76);style_widget(self.empty_message,'padding:12px;background:#11251b;color:#b2cfc1;');th.addWidget(self.empty_message)
        foot=text('«—» — датчик недоступен. Мин/макс — наблюдения с начала этой сессии. Порог — настройка, не предел производителя.',True);foot.setWordWrap(True);th.addWidget(foot);thermal_scroll=QScrollArea();thermal_scroll.setWidgetResizable(True);thermal_scroll.setWidget(thermal);self.tabs.addTab(thermal_scroll,'Температуры')
        raw_widget=QWidget();raw_layout=QVBoxLayout(raw_widget);raw_layout.setContentsMargins(0,16,0,0)
        note=text('Все датчики. Warning/Critical Temperature — постоянные пороги, не текущие температуры. Fan #1 не назначается CPU автоматически.',True);note.setWordWrap(True);raw_layout.addWidget(note)
        self.raw_table=QTableWidget(0,5);self.raw_table.setHorizontalHeaderLabels(['Датчик / устройство','Тип','Значение','Единица','Источник']);self.raw_table.verticalHeader().hide();self.raw_table.setEditTriggers(QTableWidget.NoEditTriggers);self.raw_table.setAlternatingRowColors(True);self.raw_table.setWordWrap(False)
        self.raw_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        for col,width in [(1,115),(2,100),(3,90),(4,150)]:self.raw_table.setColumnWidth(col,width)
        raw_layout.addWidget(self.raw_table);self.tabs.addTab(raw_widget,'Все датчики')
        self.character_overlay=CharacterPortrait(root)
        self.status=text('Ожидание телеметрии…',True);self.status.setProperty('no_translate',True);self.status.setWordWrap(True);layout.addWidget(self.status)
        self.header_drag=HeaderDragController(self,root,[root,self.brand_label,self.version_label,self.connection,self.clock_widget,self.clock,self.clock_date,self.clock_zone,self.theme_badge])

    def update_clock(self):
        data=clock_data();self.clock.setText(data['time']);self.clock_date.setText(data['date']+' · '+data['offset'])
        self.clock_zone.setText(self.clock_zone.fontMetrics().elidedText(data['zone'],Qt.ElideLeft,max(0,self.clock_widget.width())))
        tooltip=tr('Дата')+': '+data['date']+'\n'+tr('Часовой пояс')+': '+data['zone']+' · '+data['offset']+' · '+data['abbreviation']
        for widget in (self.clock,self.clock_date,self.clock_zone):widget.setToolTip(tooltip)
        if hasattr(self,'character_overlay'):self.update_character_placement()

    def refresh(self,presentation_only=False):
        if self.paused:return
        d=getattr(self,'base_snapshot',{}) if presentation_only else demo_snapshot() if self.demo else self.collector.snapshot()
        if not d:
            self.connection.setText(tr('Подключение / сбор данных…'));return
        t=d.get('timestamp',time.time())
        if not presentation_only and time.time()-t>5:
            d={'timestamp':time.time(),'status':'Сбор системных данных остановился. Перезапустите приложение.','temperatures':[]}
        self.base_snapshot=d;d=apply_config(d,self.dashboard_config)
        self.current=d;self.connection.setText('DEMO / СИНТЕТИЧЕСКИЕ ДАННЫЕ' if self.demo else 'LIVE / ЛОКАЛЬНЫЙ МОНИТОРИНГ')
        self.cpu.update_data(d,self.threshold);self.gpu.update_data(d,self.threshold)
        for key,m in self.memory_metrics.items():
            v=d.get(key)
            if key=='vram_free':v=d.get('vram_free')
            m.update_value(v,1)
        self.upload.update_value(d.get('upload'),1);self.download.update_value(d.get('download'),1)
        disks=d.get('disks',[]);self.disk_label.setText('ДИСКИ · СВОБОДНО / GiB\n'+'\n'.join(f'{x["mount"]}   {fmt(x["free"],1)} GiB   ·   {fmt(x["percent"])}% занято' for x in disks) if disks else 'ДИСКИ\nНет доступных разделов')
        if t!=self.last_timestamp:
            for key,g in self.graphs.items():g.push(t,d.get(key+'_usage'));self.last_timestamp=t
        for sensor in d.get('temperatures',[]):
            value=finite(sensor.get('value'))
            if value is not None:
                sid=sensor['id'];self.peaks[sid]=max(value,self.peaks.get(sid,value));self.troughs[sid]=min(value,self.troughs.get(sid,value))
        self.update_thermal();self.update_raw()
        labels=d.get("sensor_labels",{})
        for key in ["cpu_power","cpu_rpm","cpu_clock"]:self.cpu.metrics[key].setToolTip("Источник: "+labels.get(key,"не определён"))
        clock_kind=d.get('cpu_clock_kind');self.cpu.metrics['cpu_clock'].label.setText('ЭФФЕКТ. ЧАСТОТА' if clock_kind=='effective' else 'ЧАСТОТА (ОС)' if clock_kind=='os' else 'ЧАСТОТА CPU')
        self.cpu.temp.setToolTip("Датчик CPU: "+labels.get("cpu_temp","не определён"))
        self.thermal_metrics["cpu_temp"].setToolTip("Датчик CPU: "+labels.get("cpu_temp","не определён"))
        self.update_dashboard_cards();self.update_fps_reading(d)
        uptime=int(d.get('uptime') or 0);host=str(d.get('hostname','')).strip();host='' if host.casefold()==DEVELOPER_NAME.casefold() else host
        footer=[tr(d.get('status','Ожидание датчиков…'))]+([host] if host else [])+[f'UPTIME {uptime//86400}d {(uptime//3600)%24}h {(uptime//60)%60}m'];self.status.setText('   |   '.join(footer));localize_tree(self)

    def update_thermal(self,*_):
        if not hasattr(self,'table'):return
        d=self.current
        for key,card in self.thermal_metrics.items():
            v=d.get(key);card.update_value(v,1,finite(v) is not None and v>=self.threshold)
        self.threshold_label.setText(f'Порог выделения: {self.threshold} °C')
        self.thermal_metrics['disk_temp'].setToolTip('Максимум текущих датчиков накопителей; Warning/Critical Temperature — лимиты, в максимум не входят.')
        sensors=d.get('temperatures',[]);selected=self.group_filter.currentData();filtered=[s for s in sensors if selected=='Все датчики' or s['group']==selected]
        high=sum(1 for s in sensors if finite(s.get('value')) is not None and s['value']>=self.threshold)
        self.sensor_count.setText(f'Датчиков: {len(sensors)}   /   Выше порога: {high}')
        self.table.setRowCount(len(filtered))
        for row,s in enumerate(filtered):
            v=s.get('value');above=finite(v) is not None and v>=self.threshold;sid=s['id']
            values=[f'{s["name"]} · {s["device"]}',fmt(v,1),fmt(self.troughs.get(sid),1),fmt(self.peaks.get(sid),1),'ВЫШЕ ПОРОГА' if above else 'Ниже порога',s['source']]
            for col,value in enumerate(values):
                item=QTableWidgetItem(value);item.setToolTip(value+'\n'+sid)
                item.setForeground(QColor(theme_color(WARNING if above else CYAN if col in [1,4] else MUTED)))
                if col in [1,2,3]:item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
                self.table.setItem(row,col,item)
            self.table.setRowHeight(row,40)
        self.empty_message.setVisible(not filtered)
        self.empty_message.setText('Нет датчиков в выбранной группе.' if sensors else 'Температуры пока недоступны. Выберите AIDA64 Shared Memory или LHM в «Подключить датчики» и оставьте выбранную программу открытой. Нажмите «Подключить датчики» для инструкции. NVIDIA может отдавать температуру GPU без LHM.')

    def apply_span(self):
        for g in self.graphs.values():g.span=self.history_span;g.update()

    def sync_control_menu(self):
        self.pause_button.setText('Продолжить' if self.paused else 'Пауза');self.fullscreen_action.setChecked(self.isFullScreen());self.compact_button.setChecked(self.compact_mode)
        for i,action in enumerate(self.section_actions):action.setChecked(self.tabs.currentIndex()==i)
        localize_tree(self.control_menu);self.sync_tray_menu()

    def toggle_pause(self):
        self.paused=not self.paused;self.pause_button.setText('Продолжить' if self.paused else 'Пауза')
        if self.paused:
            for g in self.graphs.values():g.points.append((time.time(),None))
            self.connection.setText('ПАУЗА / ПОКАЗАНИЯ ЗАМОРОЖЕНЫ')
        else:self.refresh()
        localize_tree(self);self.sync_tray_menu()

    def apply_window_mode(self,fullscreen=None,on_top=None):
        """Reapply both flags together: Qt flag changes otherwise recreate a titled window."""
        self.header_drag.cancel();self.save_window_placement();self._mode_changing=True
        was_full=self._fullscreen_requested or self.isFullScreen()
        full=was_full if fullscreen is None else bool(fullscreen)
        geometry=self.saveGeometry();maximized=self.isMaximized()
        if full and not was_full:
            self._normal_window_geometry=geometry;self._normal_was_maximized=maximized
        flags=self.windowFlags()
        flags=flags|Qt.FramelessWindowHint if full else flags&~Qt.FramelessWindowHint
        if on_top is not None:
            flags=flags|Qt.WindowStaysOnTopHint if on_top else flags&~Qt.WindowStaysOnTopHint
            self.settings.setValue('always_on_top',bool(on_top))
        self._fullscreen_requested=full
        if flags!=self.windowFlags():self.setWindowFlags(flags)
        if full:self.showFullScreen()
        elif was_full:
            self.showNormal()
            if self._normal_window_geometry:self.restoreGeometry(self._normal_window_geometry)
            if self._normal_was_maximized:self.showMaximized()
        else:
            self.restoreGeometry(geometry)
            self.showMaximized() if maximized else self.showNormal()
        self.apply_shell_style();self.sync_control_menu();self.update_character_placement();self.header_drag.update_cursors();self._mode_changing=False;self.track_window_placement()

    def toggle_fullscreen(self):
        self.apply_window_mode(fullscreen=not (self._fullscreen_requested or self.isFullScreen()))

    def escape(self):
        if self._fullscreen_requested or self.isFullScreen():self.apply_window_mode(fullscreen=False)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'thermal_grid'):self.adapt_layout()
        self.track_window_placement()

    def adapt_layout(self):
        width=self.width();compact=self.compact_mode
        if self.demo_note:self.demo_note.setVisible(not compact)
        tight=self.height()<900 or len(self.custom_widgets)>6;stack=width<(780 if compact else 1000)
        self.root_layout.setContentsMargins(16 if compact else 24,10 if compact else 18,16 if compact else 24,10 if compact else 16);self.root_layout.setSpacing(6 if compact else 16)
        self.overview_layout.setContentsMargins(0,6 if compact else 16,6 if compact else 10,6 if compact else 16);self.overview_layout.setSpacing(6 if compact else 20)
        for metric in self.findChildren(Metric):metric.set_density(compact,tight)
        self.cpu.set_density(compact,tight);self.gpu.set_density(compact,tight)
        for section in (self.cpu,self.gpu):section.title_label.setMaximumWidth(max(90,min(650,int(width*.4))))
        self.sys_section_layout.setSpacing(6 if compact else 20);self.memory_grid.setSpacing(4 if compact else 10);self.ram_graph.compact=compact;self.ram_graph.setMinimumHeight((88 if tight else 110) if compact else 150);self.ram_graph.setMinimumWidth(200 if compact else 280)
        self.network_row.setSpacing(10 if compact else 16);self.custom_grid.setSpacing(6 if compact else 12)
        self.sys_header_layout.setContentsMargins(12 if compact else 16,3 if compact else 7,12 if compact else 16,3 if compact else 7)
        style_widget(self.syshead,strip_font(18 if compact else 24))
        self.board_caption.setMaximumWidth(max(60,min(220,width//4)));style_widget(self.board_caption,strip_font(18 if compact else 24))
        self.board_temp_px=18 if compact else 24;self.update_board_temperature()
        self.thermal_filter_row.setDirection(QBoxLayout.TopToBottom if width<720 else QBoxLayout.LeftToRight)
        self.version_label.setVisible(width>=900)
        brand=self.brand_label;brand.setMaximumWidth(max(160,min(500,width//2)));style_widget(brand,'font-size:'+('26' if width<720 or compact else '34')+'px;font-weight:900;letter-spacing:3px;')
        for row in [self.cpu.responsive_row,self.gpu.responsive_row,self.memory_row,self.network_row]:row.setDirection(QBoxLayout.TopToBottom if stack else QBoxLayout.LeftToRight)
        columns=4 if width>=1100 else 2
        for i,card in enumerate(self.thermal_metrics.values()):self.thermal_grid.removeWidget(card);self.thermal_grid.addWidget(card,i//columns,i%columns)
        for i,(_,card) in enumerate(self.custom_widgets):
            ncols=6 if compact and width>=1500 else columns
            self.custom_grid.removeWidget(card);self.custom_grid.addWidget(card,i//ncols,i%ncols)
        self.cpu.detail.setVisible(width>=640);self.gpu.detail.setVisible(width>=640)
        for table in [self.table,self.raw_table]:
            table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch if width>=1000 else QHeaderView.Interactive)
            if width<1000:table.setColumnWidth(0,300)
        if hasattr(self,'character_overlay'):QTimer.singleShot(0,self.update_character_placement)

    def toggle_compact(self):
        self.compact_mode=self.compact_button.isChecked();self.settings.setValue('compact_original',self.compact_mode);self.adapt_layout();self.refresh()

    def rebuild_custom_cards(self):
        for _,card in self.custom_widgets:self.custom_grid.removeWidget(card);card.hide();card.deleteLater()
        self.custom_widgets=[]
        for item in self.dashboard_config.get('custom',[]):
            card=Metric(item.get('label') or 'Датчик',item.get('unit',''));card.label.setProperty('no_translate',True);self.custom_widgets.append((item,card))
        self.custom_container.setVisible(bool(self.custom_widgets));self.adapt_layout()

    def update_dashboard_cards(self):
        config=self.dashboard_config;slots=config.get('slots',{})
        cards={**self.cpu.metrics,**self.gpu.metrics,**self.memory_metrics,**self.thermal_metrics,'fps':self.fps_metric,'upload':self.upload,'download':self.download}
        for key,card in cards.items():
            setting=slots.get(key,{});card.setVisible(not setting.get('hidden',False))
            if not hasattr(card,'default_label'):card.default_label=card.label.text()
            label=setting.get('label','').strip();card.label.setProperty('no_translate',bool(label))
            if label:card.label.setText(label)
            elif key!='cpu_clock':card.label.setText(card.default_label)
            sid=setting.get('sensor','')
            if sid:card.setToolTip('Источник: '+self.current.get('sensor_labels',{}).get(key,'Недоступно'))
        self.update_board_temperature()
        self.cpu.temp.setVisible(not slots.get('cpu_temp',{}).get('hidden',False));self.gpu.temp.setVisible(not slots.get('gpu_temp',{}).get('hidden',False))
        self.cpu.graph.setVisible(not slots.get('cpu_usage',{}).get('hidden',False));self.gpu.graph.setVisible(not slots.get('gpu_usage',{}).get('hidden',False));self.ram_graph.setVisible(not slots.get('ram_usage',{}).get('hidden',False))
        lookup={r['id']:r for r in available_rows(getattr(self,'base_snapshot',self.current))}
        for item,card in self.custom_widgets:
            row=lookup.get(item.get('sensor'));value=row.get('value') if row else None
            card.update_value(value,0 if item.get('unit') in ['RPM','MHz','FPS'] else 1,finite(value) is not None and item.get('unit')=='°C' and value>=self.threshold)
            card.setToolTip((row.get('name','')+' · '+row.get('source','')) if row else 'Выбранный датчик недоступен')

    def update_hardware_titles(self):
        for key,section in [('cpu',self.cpu),('gpu',self.gpu)]:
            caption=self.hardware_names.get(key) or key.upper();section.title_label.setText(caption);section.title_label.setToolTip(caption)

    def hardware_name_suggestions(self,key):
        values=[key.upper()] if key in ('cpu','gpu') else []
        reported=self.current.get(key+'_name') if key!='board' else self.current.get('board_name')
        if reported:values.append(reported)
        if key in ('cpu','gpu'):
            for row in self.current.get('sensor_rows',[]):
                device=str(row.get('device','')).strip()
                if group_for(row.get('id',''))!=key.upper() or not device or device.startswith('/') or device.endswith('/ AIDA64') or device.endswith('/ DEMO'):continue
                values.append(device)
        if key in ('cpu','gpu'):
            for row in self.current.get('temperatures',[]):
                device=str(row.get('device','')).strip()
                if row.get('group')==key.upper() and device and not device.startswith('/') and not device.endswith('/ AIDA64') and not device.endswith('/ DEMO'):values.append(device)
        return list(dict.fromkeys(clean_hardware_name(value) for value in values if clean_hardware_name(value)))

    def update_board_temperature(self):
        if not hasattr(self,'board_temp'):return
        setting=self.dashboard_config.get('slots',{}).get('sys_temp',{});value=finite(self.current.get('sys_temp'))
        board_name=self.hardware_names.get('board') or 'SYS'
        header=board_name+'  //////  '+tr('ПАМЯТЬ И РЕСУРСЫ');self.syshead.setText(header);self.syshead.setToolTip(header)
        caption=setting.get('label','').strip() or tr('ПЛАТА');self.board_caption.setText(caption)
        self.board_temp.setText(fmt(value,1)+' °C');hot=value is not None and value>=self.threshold
        style_widget(self.board_temp,strip_font(self.board_temp_px,'#942014' if hot else '#06100b'))
        hidden=bool(setting.get('hidden',False));self.board_caption.setVisible(not hidden);self.board_temp.setVisible(not hidden)
        source=self.current.get('sensor_labels',{}).get('sys_temp')
        if not source:
            candidates=[x for name in ('system','motherboard') for x in self.current.get('temperatures',[]) if x.get('group')=='Плата' and name in x.get('name','').casefold()]
            source=(candidates[0]['name']+' · '+candidates[0].get('device','')) if candidates and not setting.get('sensor') else tr('Недоступно')
        tooltip=caption+' · '+fmt(value,1)+' °C\n'+tr('Источник')+': '+source
        self.board_caption.setToolTip(tooltip);self.board_temp.setToolTip(tooltip)

    def configure_dashboard(self):
        dialog=QDialog(self);dialog.setWindowTitle('Настройка панели и всех датчиков');dialog.resize(min(940,max(500,self.width()-40)),min(800,max(420,self.height()-40)))
        outer=QVBoxLayout(dialog);note=text('Выбирайте источник каждой карточки, меняйте название или скрывайте её. Список показывает только датчики подходящего устройства, типа и назначения. Свои карточки — любые числовые датчики. Недоступный выбранный источник даёт «—», без автоматической подмены.',True);note.setWordWrap(True);outer.addWidget(note)
        scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();content=QVBoxLayout(body);scroll.setWidget(body);outer.addWidget(scroll,1)
        rows=available_rows(getattr(self,'base_snapshot',self.current));controls={};custom_controls=[]
        def sensor_combo(selected='',unit=None,key=None):
            box=QComboBox();box.setMinimumWidth(160);box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);box.setMinimumContentsLength(18)
            box.addItem('Авто / стандартный источник' if unit is not None else 'Выберите числовой датчик','')
            for r in rows:
                if key is not None and not matches_slot(r,key):continue
                if key is None and unit is not None and not compatible(r,unit):continue
                if unit is None and r.get('type')=='System' and finite(r.get('value')) is None:continue
                box.addItem(r['name']+' · '+r.get('device','')+' · '+fmt(r.get('value'),1)+' '+r.get('unit',''),r['id']);box.setItemData(box.count()-1,r['id']+' · '+r.get('source',''),Qt.ToolTipRole)
            if selected and box.findData(selected)<0:
                incompatible=key is not None and any(r['id']==selected for r in rows)
                box.addItem(tr('Несовместимое назначение · ' if incompatible else 'Недоступен · ')+selected,selected)
                box.model().item(box.count()-1).setEnabled(False)
            box.setCurrentIndex(max(0,box.findData(selected)));return box
        for key,label,unit in SLOTS:
            setting=self.dashboard_config.get('slots',{}).get(key,{})
            group=QFrame();layout=QVBoxLayout(group);layout.setContentsMargins(0,4,0,6);head=QHBoxLayout();head.addWidget(text(label+' / '+unit));head.addStretch();hidden=QCheckBox('Скрыть');hidden.setChecked(setting.get('hidden',False));head.addWidget(hidden);layout.addLayout(head)
            box=sensor_combo(setting.get('sensor',''),unit,key);box.setObjectName('dashboardSensor_'+key);name=QLineEdit(setting.get('label',''));name.setMaxLength(80);name.setPlaceholderText('Название карточки (пусто — стандартное)');layout.addWidget(box);layout.addWidget(name);content.addWidget(group);controls[key]=(box,name,hidden)
        content.addWidget(text('СВОИ КАРТОЧКИ'));add=None
        def add_custom(item=None):
            if len(custom_controls)>=MAX_CUSTOM_CARDS:return
            item=item or {};frame=QFrame();row=QVBoxLayout(frame);box=sensor_combo(item.get('sensor',''));name=QLineEdit(item.get('label',''));name.setMaxLength(80);name.setPlaceholderText('Название своей карточки');remove=QPushButton('Удалить карточку');row.addWidget(box);row.addWidget(name);row.addWidget(remove);content.addWidget(frame);entry=[frame,box,name,item.get('unit','')];custom_controls.append(entry)
            def delete():
                custom_controls.remove(entry);frame.deleteLater()
                if add is not None:add.setEnabled(len(custom_controls)<MAX_CUSTOM_CARDS)
            remove.clicked.connect(delete)
            if add is not None:add.setEnabled(len(custom_controls)<MAX_CUSTOM_CARDS)
        for item in self.dashboard_config.get('custom',[]):add_custom(item)
        add=QPushButton('+ Своя карточка');add.setObjectName('dashboardAddCustom');add.setEnabled(len(custom_controls)<MAX_CUSTOM_CARDS);add.clicked.connect(lambda:add_custom());outer.addWidget(add)
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel|QDialogButtonBox.Reset);buttons.button(QDialogButtonBox.Save).setText('Сохранить');buttons.button(QDialogButtonBox.Cancel).setText('Отмена');buttons.button(QDialogButtonBox.Reset).setText('Сбросить панель');outer.addWidget(buttons)
        def save(reset=False):
            result={'slots':{},'custom':[]}
            if not reset:
                for key,(box,name,hidden) in controls.items():result['slots'][key]={'sensor':box.currentData() or '', 'label':name.text().strip(),'hidden':hidden.isChecked()}
                lookup={r['id']:r for r in rows}
                for _,box,name,old_unit in custom_controls:
                    sid=box.currentData()
                    if not sid:continue
                    r=lookup.get(sid,{});result['custom'].append({'sensor':sid,'label':name.text().strip() or r.get('name','Датчик'),'unit':r.get('unit',old_unit)})
            self.dashboard_config=result;self.settings.setValue('dashboard_config_v1',json.dumps(result,ensure_ascii=False));self.rebuild_custom_cards();self.last_timestamp=None
            for graph in self.graphs.values():graph.points=[]
            was_paused=self.paused;self.paused=False;self.refresh();self.paused=was_paused;dialog.accept()
        buttons.accepted.connect(lambda:save());buttons.rejected.connect(dialog.reject);buttons.button(QDialogButtonBox.Reset).clicked.connect(lambda:save(True));self.prepare_dialog(dialog);dialog.exec();dialog.deleteLater()

    def show_settings(self):
        dialog=QDialog(self);dialog.setWindowTitle('Настройки');dialog.setMinimumWidth(480);screen=self.screen().availableGeometry();dialog.resize(min(760,screen.width()-40),min(760,screen.height()-60));outer=QVBoxLayout(dialog);scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();layout=QVBoxLayout(body);scroll.setWidget(body);outer.addWidget(scroll,1);form=QFormLayout();form.setVerticalSpacing(16);form.setRowWrapPolicy(QFormLayout.WrapLongRows);form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        nickname=QLineEdit(self.nickname);nickname.setObjectName('displayName');nickname.setMaxLength(48)
        language=QComboBox();language.setObjectName('interfaceLanguage')
        for caption,code in [('Русский','ru'),('Українська','uk'),('English','en')]:language.addItem(caption,code)
        language.setCurrentIndex(max(0,language.findData(self.language)));form.addRow('Ник / название',nickname);form.addRow('Язык интерфейса',language)
        style_button=QPushButton(theme_name(self.theme_id,self.language));style_button.setObjectName('chooseInterfaceStyle');style_button.setProperty('no_translate',True);style_button.clicked.connect(lambda:(self.choose_theme(),style_button.setText(theme_name(self.theme_id,i18n.LANG))));form.addRow('Стиль интерфейса',style_button)
        hardware_fields={}
        for key,label in [('cpu','Название процессора'),('gpu','Название видеокарты'),('board','Название материнской платы')]:
            box=QComboBox();box.setEditable(True);box.setInsertPolicy(QComboBox.NoInsert);box.setObjectName('hardwareName_'+key);box.setProperty('no_translate',True);box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);box.setMinimumContentsLength(18);box.setMinimumWidth(200);box.addItem('');box.addItems(self.hardware_name_suggestions(key));box.lineEdit().setMaxLength(80);box.lineEdit().setPlaceholderText('Пусто — стандартное название');box.setEditText(self.hardware_names.get(key,''));form.addRow(label,box);hardware_fields[key]=box
        interval=QComboBox();interval.setObjectName('interfaceRefresh');interval.addItem('250 мс',250);interval.addItem('500 мс',500);interval.addItem('1 секунда',1000);interval.addItem('2 секунды',2000);interval.addItem('5 секунд',5000);interval.setCurrentIndex(max(0,interval.findData(self.interval)))
        sensor_poll=QComboBox();sensor_poll.setObjectName('sensorPolling')
        for ms in (250,500,1000,2000,3000,5000):sensor_poll.addItem(str(ms)+' '+tr('мс'),ms)
        sensor_poll.setCurrentIndex(max(0,sensor_poll.findData(self.collector.poll_ms)))
        span=QComboBox();span.addItem('60 секунд',60);span.addItem('120 секунд',120);span.addItem('5 минут',300);span.setCurrentIndex(max(0,span.findData(self.history_span)))
        threshold=QSpinBox();threshold.setRange(30,120);threshold.setSuffix(' °C');threshold.setValue(self.threshold)
        on_top=QCheckBox('Поверх других окон');on_top.setObjectName('alwaysOnTop');on_top.setChecked(bool(self.windowFlags()&Qt.WindowStaysOnTopHint))
        form.addRow('Обновление интерфейса',interval);form.addRow('Опрос датчиков',sensor_poll);form.addRow('Окно истории',span);form.addRow('Порог температуры',threshold);layout.addLayout(form);layout.addWidget(on_top)
        startup_state=autostart_status();startup=QCheckBox('Запускать вместе с Windows');startup.setObjectName('startWithWindows');startup.setChecked(startup_state['enabled']);startup.setEnabled(startup_state['supported'] and startup_state['readable'] and (startup_state['can_enable'] or startup_state['enabled']));layout.addWidget(startup)
        startup_note=text('После входа в Windows приложение откроется с видимым окном и значком в трее. Изменение применяется кнопкой «Сохранить».' if startup.isEnabled() else 'Автозапуск доступен в собранном EXE для Windows.' if not startup_state.get('error') else 'Не удалось прочитать настройки автозапуска.',True);startup_note.setObjectName('autostartNote');startup_note.setWordWrap(True);layout.addWidget(startup_note)
        note=text('Быстрый опрос читает данные источника, но не ускоряет их публикацию в AIDA64/LHM. NVIDIA опрашивается не чаще раза в секунду; WMI — не чаще раза в 2 секунды. Порог выделения не заменяет аппаратные ограничения защиты.',True);note.setWordWrap(True);layout.addWidget(note)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.button(QDialogButtonBox.Ok).setText('Сохранить');buttons.button(QDialogButtonBox.Cancel).setText('Отмена')
        def save_startup():
            if startup.isEnabled() and (startup.isChecked()!=startup_state['enabled'] or startup.isChecked() and startup_state['can_enable'] and not startup_state['matches_current']):
                try:set_autostart(startup.isChecked())
                except (OSError,ValueError,RuntimeError) as e:
                    QMessageBox.warning(dialog,tr('Автозапуск'),tr('Не удалось изменить автозапуск. Настройки не сохранены.')+'\n'+str(e));return
            dialog.accept()
        buttons.accepted.connect(save_startup);buttons.rejected.connect(dialog.reject)
        developer_row=QHBoxLayout();developer_button=QPushButton(DEVELOPER_NAME);developer_button.setObjectName('developerButton');developer_button.setProperty('no_translate',True);developer_button.setToolTip(tr('Разработчик'));developer_button.clicked.connect(self.show_developer);developer_row.addWidget(developer_button)
        developer_row.addStretch();outer.addLayout(developer_row);outer.addWidget(buttons)
        self.prepare_dialog(dialog)
        if dialog.exec()==QDialog.Accepted:
            self.hardware_names={key:clean_hardware_name(box.currentText()) for key,box in hardware_fields.items()}
            for key,value in self.hardware_names.items():self.settings.setValue('display_hardware_'+key,value)
            self.update_hardware_titles()
            self.nickname=clean_nickname(nickname.text());self.language=language.currentData();self.settings.setValue('display_name',self.nickname);self.settings.setValue('language',self.language);set_language(self.language);self.brand_label.setText(self.nickname);self.brand_label.setToolTip(self.nickname);self.setWindowTitle(self.nickname+' Desktop '+APP_VERSION+' — '+tr('Мониторинг ПК'))
            self.collector.set_poll_interval(sensor_poll.currentData());self.settings.setValue('sensor_poll_ms',self.collector.poll_ms)
            self.interval=interval.currentData();self.history_span=span.currentData();self.threshold=threshold.value()
            for key,value in [('interval',self.interval),('history',self.history_span),('threshold',self.threshold)]:self.settings.setValue(key,value)
            self.timer.setInterval(self.interval);self.apply_span();self.update_thermal();self.apply_window_mode(on_top=on_top.isChecked());was_paused=self.paused;self.paused=False;self.refresh(presentation_only=was_paused);self.paused=was_paused
            if was_paused:self.connection.setText(tr('ПАУЗА / ПОКАЗАНИЯ ЗАМОРОЖЕНЫ'))
            self.sync_control_menu();localize_tree(self);self.sync_tray_menu();self.theme_badge.setToolTip(theme_description(self.theme_id,i18n.LANG));self.apply_span()
        dialog.deleteLater()

    def apply_theme(self,key,persist=True):
        self.theme_id=valid_theme(key);set_active_theme(self.theme_id)
        set_visual_effects(self.effects_enabled)
        app=QApplication.instance();changed=app.property('_active_theme')!=self.theme_id or app.property('_active_effects')!=self.effects_enabled;style_widget(app,STYLE)
        if changed:restyle_widgets([self]+self.findChildren(QWidget))
        app.setProperty('_active_theme',self.theme_id);app.setProperty('_active_effects',self.effects_enabled)
        if persist:self.settings.setValue('interface_theme',self.theme_id)
        self.gear_button.setIcon(gear_icon())
        self.theme_badge.setPixmap(emblem(self.theme_id,30));self.theme_badge.setVisible(THEMES[self.theme_id]['motif'] is not None)
        self.theme_badge.setToolTip(theme_description(self.theme_id,i18n.LANG))
        self.character_overlay.set_theme(self.theme_id,self.character_choices.get(self.theme_id),self.effects_enabled,self.animation_enabled);self.update_character_placement()
        self.adapt_layout();self.update_thermal()
        for graph in self.graphs.values():graph.update()
        self.update();self.repaint()

    def update_character_placement(self):
        if not isValid(self) or not isValid(self.character_overlay):return
        overlay=self.character_overlay;profile=valid_character(self.theme_id,self.character_choices.get(self.theme_id));overlay.setToolTip(character_name(profile,i18n.LANG))
        if not self.characters_enabled or self.theme_id not in CHARACTERS or self.width()<900 or portrait(profile).isNull():overlay.hide();return
        root=self.centralWidget()
        def rect(w):
            point=w.mapTo(root,QPoint(0,0));return w.rect().translated(point)
        occupied=[rect(w) for w in (self.brand_label,self.version_label,self.connection,self.gear_button,self.theme_badge) if not w.isHidden()]
        left=max(r.right() for r in occupied)+16;right=rect(self.clock_widget).left()-16
        top=min(rect(self.brand_label).top(),rect(self.clock_widget).top());bottom=rect(self.gear_button).bottom()
        region=header_region(left,right,top,bottom)
        if region.isEmpty() or any(region.intersects(r) for r in occupied+[rect(self.clock_widget),rect(self.tabs)]):overlay.hide();return
        overlay.setGeometry(region);overlay.show();overlay.raise_()

    def choose_theme(self):
        dialog=QDialog(self);dialog.setObjectName('themeChooser');dialog.setWindowTitle('Стиль интерфейса');dialog.resize(min(760,self.screen().availableGeometry().width()-40),min(780,self.screen().availableGeometry().height()-60));dialog.setMinimumWidth(400);outer=QVBoxLayout(dialog)
        note=text('Цвета и персонажи меняются, расположение панелей и показания сохраняются. Портреты появляются только в свободных областях; на узком экране скрываются.',True);note.setWordWrap(True);outer.addWidget(note)
        choices=QComboBox();choices.setObjectName('interfaceTheme');choices.setProperty('no_translate',True)
        for key in THEMES:choices.addItem(QIcon(emblem(key,40)),theme_name(key,i18n.LANG),key)
        choices.setCurrentIndex(max(0,choices.findData(self.theme_id)));outer.addWidget(choices)
        profile_label=text('Персонаж');outer.addWidget(profile_label)
        profiles=QComboBox();profiles.setObjectName('themeCharacter');profiles.setProperty('no_translate',True);outer.addWidget(profiles)
        draft=dict(self.character_choices)
        preview=ThemePreview(self.theme_id);preview.show_characters=self.characters_enabled;preview.set_character(draft.get(self.theme_id));preview.configure_effects(self.theme_id,self.effects_enabled,self.animation_enabled);preview.setObjectName('themePreview');outer.addWidget(preview,1)
        show_characters=QCheckBox('Персонажи в свободных областях');show_characters.setObjectName('showCharacters');show_characters.setChecked(self.characters_enabled);show_characters.toggled.connect(lambda value:(setattr(preview,'show_characters',value),preview.sync_playback(),preview.update()));outer.addWidget(show_characters)
        effects=QCheckBox('Визуальные эффекты');effects.setObjectName('animeEffects');effects.setChecked(self.effects_enabled);outer.addWidget(effects)
        animation=QCheckBox('Анимация GIF и эффектов');animation.setObjectName('animeAnimation');animation.setChecked(self.animation_enabled);outer.addWidget(animation)
        def effect_changed(*_):
            preview.configure_effects(choices.currentData(),effects.isChecked(),animation.isChecked())
        effects.toggled.connect(effect_changed);animation.toggled.connect(effect_changed)
        description=text('');description.setObjectName('themeDescription');description.setProperty('no_translate',True);description.setWordWrap(True);outer.addWidget(description)
        def chosen_profile(*_):
            key=choices.currentData();profile=valid_character(key,profiles.currentData());preview.set_character(profile)
            if profile is not None:draft[key]=profile
            preview.update()
        profiles.currentIndexChanged.connect(chosen_profile)
        def selected(*_):
            key=choices.currentData();profiles.blockSignals(True);profiles.clear()
            for profile in THEME_PROFILES.get(key,()):profiles.addItem(character_name(profile,i18n.LANG),profile)
            profiles.setCurrentIndex(max(0,profiles.findData(draft.get(key))));profiles.blockSignals(False)
            profiles.setVisible(key in THEME_PROFILES);profile_label.setVisible(key in THEME_PROFILES)
            preview.set_theme(key);chosen_profile();description.setText(theme_description(key,i18n.LANG));effect_changed()
        choices.currentIndexChanged.connect(selected);selected()
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.button(QDialogButtonBox.Ok).setText('Применить стиль');buttons.button(QDialogButtonBox.Cancel).setText('Отмена');buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);outer.addWidget(buttons)
        self.prepare_dialog(dialog)
        if dialog.exec()==QDialog.Accepted:
            self.characters_enabled=show_characters.isChecked();self.settings.setValue('show_characters',self.characters_enabled)
            self.effects_enabled=effects.isChecked();self.animation_enabled=animation.isChecked();self.settings.setValue('anime_effects',self.effects_enabled);self.settings.setValue('anime_animation',self.animation_enabled)
            self.character_choices=draft
            for key,value in draft.items():self.settings.setValue('theme_character/'+key,value)
            self.apply_theme(choices.currentData())
        preview.effect_timer.stop();preview.player.stop();dialog.deleteLater()

    def show_developer(self):
        dialog=QDialog(self);dialog.setObjectName('developerDialog');dialog.setWindowTitle('Разработчик');dialog.setMinimumWidth(360);layout=QVBoxLayout(dialog);layout.setSpacing(16)
        title=text(DEVELOPER_NAME);title.setObjectName('developerName');title.setProperty('no_translate',True);style_widget(title,'font-size:26px;font-weight:900;');layout.addWidget(title)
        close=QPushButton('Закрыть');close.clicked.connect(dialog.accept);layout.addWidget(close);self.prepare_dialog(dialog);dialog.exec();dialog.deleteLater()

    def prepare_dialog(self,dialog):
        localize_tree(dialog)
        timer=QTimer(dialog);timer.timeout.connect(lambda:localize_tree(dialog));timer.start(200);dialog.finished.connect(timer.stop)

    def update_raw(self):
        rows=self.current.get('sensor_rows',[])
        self.raw_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,v in enumerate([r['name']+' · '+r['device'],'Порог °C' if r.get('is_limit') else r['type'],r.get('text_value','') if r['type']=='System' else fmt(r.get('value'),1 if r['type'] not in ['Fan','FPS'] else 0),r['unit'],r['source']]):
                item=QTableWidgetItem(v);item.setToolTip(r['id']+'\n'+r['name']+' · '+r['device']);self.raw_table.setItem(i,j,item)
            self.raw_table.setRowHeight(i,36)

    def update_fps_reading(self,d):
        report=inspect_fps(d,self.dashboard_config);self.current_fps_diagnostic=report;self.fps_metric.update_value(report['value'])
        app=report['application'];caption=('RTSS: '+display_application_name(app['name'])) if app['state']=='tracked' else tr('RTSS: несколько приложений') if app['state']=='multiple' else tr('Приложение FPS: не определено')
        self.fps_application.setText(caption);self.fps_application.setToolTip(caption+'\n'+(tr('Последнее подтверждённое имя: временный сбой чтения RTSS, ожидание обновления.')+'\n' if app.get('cached') else '')+tr('RTSS показывает отслеживаемое приложение; связь с общим FPS AIDA64 не подтверждена.')+'\n'+'\n'.join(display_application_name(a['name'])+' · PID '+str(a['pid']) for a in app['candidates']))
        self.fps_status.setText(tr(status_caption(report)) if report['state'] not in ('available','demo') else '')
        style_widget(self.fps_status,'background:transparent;font-family:Arial;font-size:12px;color:'+('#ffc4ad' if report['state'] in ('zero','invalid','stale') else MUTED)+';')
        self.fps_status.setToolTip(tr(FPS_GUIDE));self.fps_metric.setToolTip(tr('Источник')+': '+tr(str(report['source']))+'\n'+tr(status_caption(report))+'\n'+tr('Подробности: ⚙ → Подключить датчики → FPS.'))

    def diagnostic_payload(self):
        d=self.current if self.demo else self.collector.snapshot()
        applied=apply_config(d,self.dashboard_config);fps=inspect_fps(applied,self.dashboard_config)
        return {'app_version':APP_VERSION,'mode':'synthetic-demo' if self.demo else 'live',
                'diagnostics':{**d.get('diagnostics',{}),'windows_shell':dict(self.shell_report),'tray_enabled':self.tray_enabled,'interface_theme':self.theme_id,'theme_character':valid_character(self.theme_id,self.character_choices.get(self.theme_id)),'anime_effects':self.effects_enabled,'anime_animation':self.animation_enabled,'polling':d.get('polling',{'requested_ms':self.collector.poll_ms,'effective_hardware_ms':self.collector.effective_poll_ms()}),'fps':fps,'dashboard_mappings':applied.get('mapping_status',{})},'sensor_labels':applied.get('sensor_labels',{}),
                'sensors':d.get('sensor_rows',[])}

    def sensor_help(self):
        dialog=QDialog(self);dialog.setObjectName('sensorConnectionDialog');dialog.setWindowTitle('AIDA64 / LHM — подключение и диагностика');screen=self.screen().availableGeometry();dialog.resize(min(900,screen.width()-40),min(840,screen.height()-60))
        outer=QVBoxLayout(dialog);pages=QTabWidget();pages.setObjectName('connectionPages');outer.addWidget(pages,1)
        def scroll_page(caption):
            sc=QScrollArea();sc.setWidgetResizable(True);body=QWidget();layout=QVBoxLayout(body);layout.setSpacing(12);sc.setWidget(body);pages.addTab(sc,caption);return layout
        connection_layout=scroll_page('Подключение')
        msg=text('');msg.setWordWrap(True);style_widget(msg,'color:#bdd3c8;');connection_layout.addWidget(msg)
        form=QFormLayout();form.setVerticalSpacing(8);form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow);form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        mode=QComboBox();mode.setObjectName('sourceMode');mode.addItem('AIDA64 Extreme 8.00.8000 — Shared Memory','aida');mode.addItem('LHM: HTTP → WMI для старых версий','auto');mode.addItem('LHM: только HTTP (0.9.5+)','http');mode.addItem('LHM: только WMI (старые версии)','wmi');mode.setCurrentIndex(max(0,mode.findData(self.collector.source_mode)))
        port=QSpinBox();port.setRange(1,65535);port.setValue(self.collector.port)
        user=QLineEdit(self.collector.username or str(self.settings.value('lhm_user','')));user.setPlaceholderText('Если включена Authentication в LHM')
        password=QLineEdit(self.collector.password);password.setEchoMode(QLineEdit.Password);password.setPlaceholderText('Только для этого сеанса, не сохраняется')
        form.addRow('Источник',mode);form.addRow('Порт локального LHM',port);form.addRow('Имя пользователя LHM',user);form.addRow('Пароль LHM',password);connection_layout.addLayout(form);connection_layout.addStretch()
        sensor_layout=scroll_page('Датчики панели')
        note=text('Назначения общие с «Панель / датчики». Выбирайте источник каждого показателя, затем нажмите «Применить». В списке только датчики подходящего устройства, типа и назначения; отсутствующий выбранный датчик даёт «—», без подмены.',True);note.setWordWrap(True);sensor_layout.addWidget(note)
        live_note=text('Показания в списках обновляются автоматически. Выбор сохраняется; изменения применяются кнопкой «Применить».',True);live_note.setWordWrap(True);live_note.setObjectName('panelLiveUpdateNote');sensor_layout.addWidget(live_note)
        combos={};custom_combos=[];defs=list(SLOTS)
        sections=[('FPS',[x for x in defs if x[0]=='fps']),('CPU',[x for x in defs if x[0].startswith('cpu_')]),('GPU',[x for x in defs if x[0].startswith('gpu_')]),('SYS / Память, сеть и накопители',[x for x in defs if x[0] not in ('fps',) and not x[0].startswith(('cpu_','gpu_'))])]
        for heading,items in sections:
            h=text(heading);style_widget(h,'background:#18ffe0;color:#06100b;padding:5px 10px;font-weight:bold;');sensor_layout.addWidget(h)
            fields=QFormLayout();fields.setVerticalSpacing(8);fields.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow);fields.setRowWrapPolicy(QFormLayout.WrapLongRows)
            for key,label,unit in items:
                box=QComboBox();box.setObjectName('panelSensor_'+key);box.setMinimumWidth(200);box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);box.setMinimumContentsLength(18);fields.addRow(label+' / '+unit,box);combos[key]=box
            sensor_layout.addLayout(fields)
        custom_items=self.dashboard_config.get('custom',[])
        if custom_items:
            sensor_layout.addWidget(text('СВОИ КАРТОЧКИ'));fields=QFormLayout();fields.setRowWrapPolicy(QFormLayout.WrapLongRows);fields.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            for i,item in enumerate(custom_items):
                label=text((item.get('label') or tr('Датчик'))+' / '+item.get('unit',''));label.setProperty('no_translate',True);label.setTextFormat(Qt.PlainText)
                box=QComboBox();box.setObjectName('customSensor_'+str(i));box.setMinimumWidth(200);box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);box.setMinimumContentsLength(18);fields.addRow(label,box);custom_combos.append((item,box))
            sensor_layout.addLayout(fields)
        note=text('FPS требует RTSS и экспорта в AIDA64. RPM — не PWM (%). Warning/Critical Temperature — лимиты, не температуры. Свободное место разделов диска читается из ОС автоматически.',True);note.setWordWrap(True);sensor_layout.addWidget(note)
        def fill_box(box,selected,unit,rows,custom=False,key=None):
            entries=[(tr('Выберите числовой датчик' if custom else 'Авто / стандартный источник'),'','',True)]
            for r in rows:
                if not (matches_slot(r,key) if key else compatible(r,unit)):continue
                caption=tr(r['name']) if r['id'].startswith(('system/','driver/')) else r['name']
                entries.append((caption+' · '+(tr(r.get('device','')) if r['id'].startswith(('system/','driver/')) else r.get('device',''))+' · '+fmt(r.get('value'),1)+' '+r.get('unit',''),r['id'],r['id']+' · '+r.get('source',''),True))
            if selected and selected not in [entry[1] for entry in entries]:
                incompatible=key is not None and any(r['id']==selected for r in rows)
                entries.append((tr('Несовместимое назначение · ' if incompatible else 'Выбран ранее, сейчас недоступен · ')+selected,selected,'',False))
            previous=box.blockSignals(True)
            try:
                current_ids=[box.itemData(i) for i in range(box.count())]
                wanted_ids=[entry[1] for entry in entries]
                if current_ids==wanted_ids:
                    # Update values in place: do not close/reopen or move an active popup.
                    for i,(caption,sid,tooltip,enabled) in enumerate(entries):
                        box.setItemText(i,caption);box.setItemData(i,tooltip,Qt.ToolTipRole);box.model().item(i).setEnabled(enabled)
                elif box.view().isVisible():
                    # Defer structural changes until the popup closes; values still update.
                    latest={entry[1]:entry for entry in entries}
                    for i,sid in enumerate(current_ids):
                        if sid in latest:
                            caption,_,tooltip,enabled=latest[sid];box.setItemText(i,caption);box.setItemData(i,tooltip,Qt.ToolTipRole)
                        elif sid:
                            box.setItemText(i,tr('Выбран ранее, сейчас недоступен · ')+str(sid))
                else:
                    box.clear()
                    for caption,sid,tooltip,enabled in entries:
                        box.addItem(caption,sid);box.setItemData(box.count()-1,tooltip,Qt.ToolTipRole);box.model().item(box.count()-1).setEnabled(enabled)
                    box.setCurrentIndex(max(0,box.findData(selected)))
                if not box.view().isVisible() and box.currentData()!=selected:
                    box.setCurrentIndex(max(0,box.findData(selected)))
            finally:box.blockSignals(previous)
        def fill_mappings(reset=False):
            d=getattr(self,'base_snapshot',self.current) if self.demo else self.collector.snapshot();is_aida=mode.currentData()=='aida';prefix='aida_sensor_' if is_aida else 'sensor_'
            rows=[r for r in available_rows(d) if self.demo or r['id'].startswith(('system/','driver/')) or r['id'].startswith('/aida/')==is_aida]
            for key,label,unit in defs:
                box=combos[key];setting=self.dashboard_config.get('slots',{}).get(key,{})
                selected=(setting.get('sensor',str(self.settings.value(prefix+key,''))) if reset or not box.count() else box.currentData()) or ''
                fill_box(box,selected,unit,rows,key=key)
            for item,box in custom_combos:fill_box(box,(item.get('sensor','') if reset or not box.count() else box.currentData()) or '',item.get('unit',''),rows,True)
            localize_tree(dialog)
        fps_layout=scroll_page('FPS');fps_summary=text('');fps_summary.setObjectName('fpsPipelineSummary');fps_summary.setProperty('no_translate',True);fps_summary.setWordWrap(True);style_widget(fps_summary,'padding:12px;background:#11251b;');fps_layout.addWidget(fps_summary)
        guide=text(FPS_GUIDE,True);guide.setWordWrap(True);fps_layout.addWidget(guide);fps_layout.addStretch()
        diagnostic_layout=scroll_page('Диагностика');report=QPlainTextEdit();report.setReadOnly(True);report.setMinimumHeight(220);diagnostic_layout.addWidget(report,1)
        def refresh_report():
            d=self.diagnostic_payload();fps=d['diagnostics']['fps'];fps_summary.setText(tr(status_caption(fps))+'\n'+tr('Источник')+': '+tr(str(fps['source']))+'\n'+tr('Значение')+': '+fmt(fps['value'],1)+' FPS\nSRTSSFPS: '+str(fps['aida_export']['raw_text'] if fps['aida_export']['present'] else tr('Не опубликован'))+'\n'+self.fps_application.toolTip());report.setPlainText(json.dumps(d.get('diagnostics',{}),ensure_ascii=False,indent=2) if d.get('diagnostics') else tr('Ожидание фонового опроса. После применения подождите и обновите список.'))
        def apply_source():
            source=mode.currentData()
            # One authoritative dashboard mapping; legacy five backend overrides become auto.
            self.collector.configure(source,port.value(),user.text() if source!='aida' else '',password.text() if source!='aida' else '',{})
            for key,value in [('sensor_source_mode',source),('lhm_port',port.value()),('lhm_user',user.text())]:self.settings.setValue(key,value)
            prefix='aida_sensor_' if source=='aida' else 'sensor_'
            for key in ['cpu_temp','cpu_clock','cpu_power','cpu_rpm','gpu_rpm']:self.settings.setValue(prefix+key,'')
            import copy
            config=copy.deepcopy(self.dashboard_config);slots=config.setdefault('slots',{})
            for key,box in combos.items():slots.setdefault(key,{})['sensor']=box.currentData() or ''
            for i,(_,box) in enumerate(custom_combos):config['custom'][i]['sensor']=box.currentData() or ''
            self.dashboard_config=config;self.settings.setValue('dashboard_config_v1',json.dumps(config,ensure_ascii=False));self.rebuild_custom_cards()
            was_paused=self.paused;self.paused=False;self.refresh(presentation_only=was_paused);self.paused=was_paused
            if was_paused:self.connection.setText(tr('ПАУЗА / ПОКАЗАНИЯ ЗАМОРОЖЕНЫ'))
            feedback.setText(tr('Настройки всех датчиков сохранены. Дождитесь фонового опроса источника.'));feedback.show()
            refresh_report()
        # Main actions stay visible even when scrolling a long sensor list.
        feedback=text('',True);feedback.setWordWrap(True);feedback.hide();outer.addWidget(feedback)
        actions=QHBoxLayout();actions.setDirection(QBoxLayout.LeftToRight)
        for name,label,slot in [('applySensors','Применить',apply_source),('refreshSensors','Обновить список',lambda:(fill_mappings(),refresh_report())),('copyDiagnostics','Копировать диагностику',lambda:QApplication.clipboard().setText(json.dumps(self.diagnostic_payload(),ensure_ascii=False,indent=2)))]:
            button=QPushButton(label);button.setObjectName(name);button.clicked.connect(slot);actions.addWidget(button)
        outer.addLayout(actions)
        links=QHBoxLayout();links.setDirection(QBoxLayout.LeftToRight);launch=QPushButton('');launch.clicked.connect(lambda:self.launch_aida() if mode.currentData()=='aida' else self.launch_lhm());links.addWidget(launch)
        link=QPushButton('Официальная инструкция');link.clicked.connect(lambda:QDesktopServices.openUrl(QUrl('https://www.aida64.com/user-manual/hardware-monitoring/external-applications' if mode.currentData()=='aida' else 'https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases')));links.addWidget(link)
        close=QPushButton('Закрыть');close.clicked.connect(dialog.reject);links.addWidget(close);outer.addLayout(links)
        def source_changed(*_):
            is_aida=mode.currentData()=='aida'
            msg.setText('AIDA64 Extreme 8.00.8000: Настройки (Preferences) → Hardware Monitoring → External Applications → Enable shared memory. Отметьте нужные датчики: CPU Clock, температуры, вентиляторы и мощность. Оставьте AIDA64 открытой. Чтение локальное, порт и пароль не нужны.' if is_aida else 'В LHM включите Remote Web Server > Run, порт 8085. Чтение: http://127.0.0.1:8085/data.json. Не открывайте порт в интернет; используйте Authentication и ограничения доступа ОС. WMI — только для старых LHM.')
            for w in [port,user,password]:w.setEnabled(not is_aida)
            launch.setText('Запустить AIDA64' if is_aida else 'Запустить LHM');fill_mappings(reset=True)
        mode.currentIndexChanged.connect(source_changed);source_changed();pages.setCurrentIndex(1)
        panel_timer=QTimer(dialog);panel_timer.setObjectName('panelLiveRefreshTimer');panel_timer.timeout.connect(fill_mappings);panel_timer.start(250);dialog.finished.connect(panel_timer.stop)
        diagnostic_timer=QTimer(dialog);diagnostic_timer.timeout.connect(refresh_report);diagnostic_timer.start(1000);dialog.finished.connect(diagnostic_timer.stop);refresh_report();self.prepare_dialog(dialog);dialog.exec();dialog.deleteLater()

    def launch_aida(self):
        if os.name!='nt':QMessageBox.information(self,'AIDA64',tr('Подключение Shared Memory предназначено для Windows x64.'));return
        name,_=QFileDialog.getOpenFileName(self,tr('Выберите aida64.exe'),str(self.settings.value('aida_path','')),'Executable (*.exe)')
        if not name:return
        if Path(name).name.lower()!='aida64.exe':QMessageBox.warning(self,tr('Проверьте файл'),tr('Выберите aida64.exe из вашего официального пакета AIDA64.'));return
        ok,_=QProcess.startDetached(name,[],str(Path(name).parent))
        if ok:self.settings.setValue('aida_path',name)
        else:QMessageBox.warning(self,tr('Не удалось запустить'),tr('Запустите AIDA64 вручную под тем же пользователем.'))

    def launch_lhm(self):
        if os.name!='nt':QMessageBox.information(self,'LHM',tr('Libre Hardware Monitor предназначен для Windows.'));return
        name,_=QFileDialog.getOpenFileName(self,tr('Выберите LibreHardwareMonitor.exe'),str(self.settings.value('lhm_path','')),'Executable (*.exe)')
        if not name:return
        if Path(name).name.lower()!='librehardwaremonitor.exe':QMessageBox.warning(self,tr('Проверьте файл'),tr('Выберите именно LibreHardwareMonitor.exe из официального пакета.'));return
        ok,_=QProcess.startDetached(name,[],str(Path(name).parent))
        if ok:self.settings.setValue('lhm_path',name)
        else:QMessageBox.warning(self,tr('Не удалось запустить'),tr('Запустите LibreHardwareMonitor.exe вручную, при необходимости от имени администратора.'))

    def export_json(self):
        if not self.current:QMessageBox.information(self,tr('Экспорт'),tr('Данные ещё не получены.'));return
        name,_=QFileDialog.getSaveFileName(self,tr('Сохранить телеметрию'),f'pc-monitor-{time.strftime("%Y%m%d-%H%M%S")}.json','JSON (*.json)')
        if not name:return
        try:
            Path(name).write_text(json.dumps(self.export_payload(),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        except OSError as e:QMessageBox.warning(self,tr('Не удалось сохранить'),str(e))

    def export_payload(self):
        return dict(mode='synthetic-demo' if self.demo else 'live',exported_at=time.time(),metrics=self.current,
                    history={k:g.points for k,g in self.graphs.items()},temperature_max=self.peaks,temperature_min=self.troughs)

    def closeEvent(self,event):
        self.header_drag.cancel()
        if self.tray_icon is not None:self.tray_icon.hide()
        self.character_overlay.effect_timer.stop();self.character_overlay.player.stop()
        self.placement_timer.stop();self.save_window_placement();self._placement_ready=False;self.timer.stop();self.clock_timer.stop();self.collector.close();super().closeEvent(event)

def demo_snapshot():
    t=time.time();sensor_defs=[('CPU','AMD Ryzen 7 7800X3D','CPU Package',47),('CPU','AMD Ryzen 7 7800X3D','CPU Core #1',43),('CPU','AMD Ryzen 7 7800X3D','CPU Core #2',45),('CPU','AMD Ryzen 7 7800X3D','CPU Core #3',44),('CPU','AMD Ryzen 7 7800X3D','CPU Core #4',42),('GPU','NVIDIA GeForce RTX 4070','GPU Core',36),('GPU','NVIDIA GeForce RTX 4070','GPU Hot Spot',42),('GPU','NVIDIA GeForce RTX 4070','GPU Memory Junction',40),('Плата','Motherboard','System',29),('Накопитель','NVMe SSD','Composite',38)]
    temps=[dict(id=f'demo/{i}',group=group,device=device,name=name,value=value,source='DEMO / синтетические') for i,(group,device,name,value) in enumerate(sensor_defs)]
    raw=[dict(id=x['id'],device=x['device'],name=x['name'],type='Temperature',group=x['group'],value=x['value'],unit='°C',source='DEMO / синтетические') for x in temps]
    raw.extend([dict(id='/amdcpu/demo/clock/0',device='CPU / DEMO',name='Cores (Average)',type='Clock',value=3600,unit='MHz',source='DEMO / синтетические'),dict(id='demo/fan/0',device='Nuvoton / DEMO',name='Fan #1',type='Fan',value=1240,unit='RPM',source='DEMO / синтетические'),dict(id='demo/power/0',device='CPU / DEMO',name='CPU Package',type='Power',value=67.6,unit='W',source='DEMO / синтетические')])
    return dict(sensor_rows=raw,diagnostics={'connected':True,'source':'DEMO / СИНТЕТИЧЕСКИЕ','attempts':[{'backend':'DEMO','ok':True,'sensor_count':13}]},sensor_labels={'cpu_temp':'CPU Package','cpu_power':'CPU Package','cpu_rpm':'Fan #1 (выбор пользователя)','cpu_clock':'Cores (Average) / DEMO'},fps=144,fps_source='DEMO',timestamp=t,hostname='DESKTOP / DEMO',cores=8,threads=16,cpu_usage=23.4,cpu_clock=3600,cpu_clock_source='DEMO',cpu_clock_kind='reported',cpu_power=67.6,cpu_rpm=1240,cpu_temp=47,cpu_core_max=45,gpu_usage=8.4,gpu_clock=2587,gpu_power=27.3,gpu_rpm=0,gpu_temp=36,gpu_hotspot=42,gpu_mem_temp=40,sys_temp=29,disk_temp=38,ram_used=15.2,ram_free=48.7,ram_total=63.9,ram_usage=23.8,vram_used=1.8,vram_total=12,upload=12.4,download=284.6,uptime=149940,disks=[dict(mount='C:\\',free=65.4,percent=74),dict(mount='D:\\',free=798,percent=21)],temperatures=temps,status='DEMO / показания не являются реальными')

def main():
    install_hooks()
    args=argparse.ArgumentParser();args.add_argument('--demo',action='store_true');args.add_argument('--screenshot');args.add_argument('--tab',choices=['overview','temperatures'],default='overview');opts=args.parse_args()
    app=QApplication(sys.argv[:1]);app.setStyle('Fusion');style_widget(app,STYLE);window=MonitorWindow(demo=opts.demo,tray_mode=False if opts.screenshot else None)
    window.show()
    if opts.screenshot:window.resize(1180,1100)
    if opts.tab=='temperatures':window.tabs.setCurrentIndex(1)
    if opts.screenshot:
        def capture():
            window.grab().save(opts.screenshot);window.close();app.quit()
        QTimer.singleShot(1800,capture)
    sys.exit(app.exec())

if __name__=='__main__':main()
