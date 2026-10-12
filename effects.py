"""Small, clipped anime decorations. No overlays on sensor data or network I/O."""
import math
from PySide6.QtCore import Qt,QTimer,QPointF
from PySide6.QtGui import QColor,QPen,QPainterPath,QRadialGradient,QPainter
from PySide6.QtWidgets import QWidget
ANIME_KEYS=('frieren','one_piece','one_punch','naruto','death_note','titan')

def alpha(color,value):
    c=QColor(color);c.setAlpha(value);return c

def paint_scene(p,rect,key,palette,phase=0):
    if key not in ANIME_KEYS or rect.width()<1:return
    p.save();p.setClipRect(rect);p.setRenderHint(QPainter.Antialiasing)
    cx=rect.center().x();cy=rect.center().y();r=min(rect.width(),rect.height())*.43
    glow=QRadialGradient(QPointF(cx,cy),max(rect.width(),rect.height())*.65)
    glow.setColorAt(0,alpha(palette['chart'],65));glow.setColorAt(.65,alpha(palette['accent'],15));glow.setColorAt(1,alpha(palette['accent'],0));p.fillRect(rect,glow)
    p.setBrush(Qt.NoBrush);p.setPen(QPen(alpha(palette['chart'],140),1.2))
    if key=='frieren':
        for scale in (1,.72):p.drawEllipse(QPointF(cx,cy),r*scale,r*scale)
        for i in range(8):
            a=i*math.pi/4+phase*.12;x=cx+math.cos(a)*r;y=cy+math.sin(a)*r;p.drawLine(QPointF(x-3,y),QPointF(x+3,y));p.drawLine(QPointF(x,y-3),QPointF(x,y+3))
    elif key=='one_piece':
        for j in range(3):
            path=QPainterPath();path.moveTo(rect.left(),cy+j*12)
            for i in range(1,49):
                x=rect.left()+rect.width()*i/48;path.lineTo(x,cy+j*12+math.sin(i*.22+phase)*6)
            p.drawPath(path)
        p.drawEllipse(QPointF(cx,cy-5),r*.8,r*.8)
    elif key=='one_punch':
        for i in range(3):
            a=phase*.35+i*2*math.pi/3;rx=r*(.55+i*.24);p.drawEllipse(QPointF(cx+math.cos(a)*7,cy+math.sin(a)*5),rx,rx*.55)
        for i in range(6):
            a=phase*.2+i*math.pi/3;p.drawLine(QPointF(cx+math.cos(a)*r,cy+math.sin(a)*r),QPointF(cx+math.cos(a)*r*1.45,cy+math.sin(a)*r*1.45))
    elif key=='naruto':
        path=QPainterPath()
        for i in range(150):
            a=i*.12+phase*.16;radius=r*i/150;x=cx+math.cos(a)*radius;y=cy+math.sin(a)*radius
            if i==0:path.moveTo(x,y)
            else:path.lineTo(x,y)
        p.drawPath(path)
    elif key=='death_note':
        p.setPen(QPen(alpha(palette['chart'],140),1));p.drawEllipse(QPointF(cx,cy),r,r)
        for side in (-1,1):
            feather=QPainterPath();feather.moveTo(cx+side*r*.3,cy-r*.8);feather.cubicTo(cx+side*r*1.3,cy-r*.3,cx+side*r*1.2,cy+r*.3,cx+side*r*.45,cy+r*.65);p.drawPath(feather)
    else:
        for side in (-1,1):
            for j in range(5):
                x=cx+side*(r*.35+j*5);y=cy-r*.6+j*7;p.drawLine(QPointF(x,y),QPointF(x+side*r*.45,y+r*.28))
        p.drawLine(QPointF(cx-r*.5,cy+r*.55),QPointF(cx+r*.5,cy-r*.55));p.drawLine(QPointF(cx+r*.5,cy+r*.55),QPointF(cx-r*.5,cy-r*.55))
    for i in range(12):
        x=rect.left()+((i*.173+phase*.008*(1+i%3))%1)*rect.width();y=rect.top()+((i*.291+phase*.012)%1)*rect.height()
        p.setPen(Qt.NoPen);p.setBrush(alpha(palette['accent'] if i%2 else palette['chart'],80+(i%4)*25));p.drawEllipse(QPointF(x,y),1.1+(i%2)*.6,1.1+(i%2)*.6)
    p.restore()

class AnimatedDecoration(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.effect_theme='classic';self.effects_enabled=True;self.animation_enabled=True;self.phase=0
        self.effect_timer=QTimer(self);self.effect_timer.setInterval(100);self.effect_timer.timeout.connect(self.advance_effect)
    def advance_effect(self):self.phase=(self.phase+.10)%100;self.update()
    def configure_effects(self,key,enabled=True,animated=True):
        self.effect_theme=key;self.effects_enabled=bool(enabled);self.animation_enabled=bool(animated);self.sync_animation();self.update()
    def sync_animation(self):
        run=self.isVisible() and self.effect_theme in ANIME_KEYS and self.effects_enabled and self.animation_enabled
        if run and not self.effect_timer.isActive():self.effect_timer.start()
        if not run:self.effect_timer.stop()
    def showEvent(self,e):super().showEvent(e);self.sync_animation()
    def hideEvent(self,e):self.effect_timer.stop();super().hideEvent(e)
