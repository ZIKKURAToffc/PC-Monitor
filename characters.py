"""Local character portraits, shown only in reserved empty regions.
See ASSET-CREDITS.md for the original images and character pages.
"""
import sys
from pathlib import Path
from functools import lru_cache
from PySide6.QtCore import Qt,QRect,QRectF,QObject
from PySide6.QtGui import QPixmap,QPainter,QPainterPath,QColor,QPen,QMovie
from themes import THEMES
from effects import AnimatedDecoration,paint_scene

CHARACTERS={
 'frieren':{'names':('Фрирен','Фрірен','Frieren'),'focus':.40},
 'one_piece':{'names':('Монки Д. Луффи','Монкі Д. Луффі','Monkey D. Luffy'),'focus':.40},
 'one_punch':{'names':('Сайтама','Сайтама','Saitama'),'focus':.45},
 'naruto':{'names':('Наруто Узумаки','Наруто Узумакі','Naruto Uzumaki'),'focus':.40},
 'death_note':{'names':('Лайт Ягами','Лайт Яґамі','Light Yagami'),'focus':.38},
 'titan':{'names':('Леви','Леві','Levi'),'focus':.47},
}

# Original six portraits remain available; additional profiles belong to one anime only.
PROFILES={key:{**value,'theme':key} for key,value in CHARACTERS.items()}
PROFILES.update({
 'fern':dict(names=('Ферн','Ферн','Fern'),theme='frieren',focus=.40),
 'nami':dict(names=('Нами','Намі','Nami'),theme='one_piece',focus=.38),
 'robin':dict(names=('Нико Робин','Ніко Робін','Nico Robin'),theme='one_piece',focus=.40),
 'tatsumaki':dict(names=('Тацумаки','Тацумакі','Tatsumaki'),theme='one_punch',focus=.36),
 'fubuki':dict(names=('Фубуки','Фубукі','Fubuki'),theme='one_punch',focus=.40),
 'hinata':dict(names=('Хината Хьюга','Хіната Хюґа','Hinata Hyuga'),theme='naruto',focus=.40),
 'sakura':dict(names=('Сакура Харуно','Сакура Харуно','Sakura Haruno'),theme='naruto',focus=.40),
 'misa':dict(names=('Миса Аманэ','Міса Амане','Misa Amane'),theme='death_note',focus=.40),
 'mikasa':dict(names=('Микаса Аккерман','Мікаса Аккерман','Mikasa Ackerman'),theme='titan',focus=.40),
 'annie':dict(names=('Энни Леонхарт','Енні Леонгарт','Annie Leonhart'),theme='titan',focus=.42),
})
THEME_PROFILES={
 'frieren':('frieren','fern'), 'one_piece':('nami','robin','one_piece'),
 'one_punch':('tatsumaki','fubuki','one_punch'), 'naruto':('hinata','sakura','naruto'),
 'death_note':('misa','death_note'), 'titan':('mikasa','annie','titan'),
}
def valid_character(theme,key=None):
    options=THEME_PROFILES.get(theme,());return key if key in options else (options[0] if options else None)

def character_name(key,language='ru'):
    entry=PROFILES.get(key)
    return entry['names'][{'ru':0,'uk':1,'en':2}.get(language,0)] if entry else ''
def resource_path(key):
    if key not in PROFILES:return None
    base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
    return base/'assets'/'characters'/(key+'.png')
def animation_path(key):
    path=resource_path(key);return path.with_suffix('.gif') if path is not None else None

class PortraitPlayer(QObject):
    """One stream-decoded GIF per visible portrait; never cache every frame."""
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.key=None;self.movie=None
    def set_profile(self,key):
        if key==self.key:return
        if self.movie is not None:
            self.movie.stop();self.movie.deleteLater();self.movie=None
        self.key=key;path=animation_path(key)
        if path is not None and path.is_file():
            movie=QMovie(str(path),b'gif',self);movie.setCacheMode(QMovie.CacheNone)
            if movie.isValid() and movie.frameCount()>1:
                self.movie=movie;movie.frameChanged.connect(self.owner.update);movie.jumpToFrame(0)
            else:movie.deleteLater()
    def sync(self,visible,animated):
        if self.movie is None:return
        if visible and animated:
            if self.movie.state()==QMovie.Paused:self.movie.setPaused(False)
            elif self.movie.state()!=QMovie.Running:self.movie.start()
        elif self.movie.state()==QMovie.Running:self.movie.setPaused(True)
    def image(self):
        if self.movie is not None:
            pix=self.movie.currentPixmap()
            if not pix.isNull():return pix
        return portrait(self.key)
    def stop(self):
        if self.movie is not None:self.movie.stop()

@lru_cache(maxsize=24)
def portrait(key):
    path=resource_path(key)
    return QPixmap(str(path)) if path is not None and path.is_file() else QPixmap()

def draw_portrait(painter,key,rect,square=False,image=None):
    image=portrait(key) if image is None else image
    if image.isNull() or rect.width()<1 or rect.height()<1:return False
    painter.save();painter.setRenderHint(QPainter.SmoothPixmapTransform);painter.setRenderHint(QPainter.Antialiasing)
    path=QPainterPath();path.addRoundedRect(QRectF(rect),9,9);painter.setClipPath(path)
    if square:
        side=min(image.width(),image.height());y=max(0,min(image.height()-side,image.height()*PROFILES[key]['focus']-side/2));source=QRectF((image.width()-side)/2,y,side,side)
    else:
        # Landscape GIFs must not be stretched into the tall preview portrait.
        scale=max(rect.width()/image.width(),rect.height()/image.height());width=rect.width()/scale;height=rect.height()/scale
        y=max(0,min(image.height()-height,image.height()*PROFILES[key]['focus']-height/2));source=QRectF((image.width()-width)/2,y,width,height)
    painter.drawPixmap(QRectF(rect),image,source);painter.restore()
    return True

def header_region(left,right,top,bottom):
    """Only use the empty strip between header controls and the clock."""
    room=right-left;height=bottom-top
    size=min(104,height-8)
    if room<136 or size<72:return QRect()
    width=min(300,room-16)
    return QRect(int(left+(room-width)/2),int(top+4),int(width),int(size))

class CharacterPortrait(AnimatedDecoration):
    def __init__(self,parent=None):
        super().__init__(parent);self.key='classic';self.player=PortraitPlayer(self);self.setObjectName('characterPortrait')
        self.setAttribute(Qt.WA_TransparentForMouseEvents,True);self.setAttribute(Qt.WA_NoSystemBackground,True);self.setFocusPolicy(Qt.NoFocus);self.setStyleSheet('background:transparent;border:0;');self.hide()
    def set_theme(self,key,profile=None,effects=True,animated=True):
        self.key=valid_character(key,profile);self.player.set_profile(self.key);self.configure_effects(key,effects,animated)
    def configure_effects(self,key,enabled=True,animated=True):
        super().configure_effects(key,enabled,animated)
        if hasattr(self,'player'):self.player.sync(self.isVisible(),self.animation_enabled)
    def showEvent(self,event):super().showEvent(event);self.player.sync(True,self.animation_enabled)
    def hideEvent(self,event):self.player.sync(False,self.animation_enabled);super().hideEvent(event)
    def paintEvent(self,event):
        if self.key not in PROFILES:return
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);palette=THEMES[self.effect_theme]['palette']
        if self.effects_enabled:paint_scene(p,QRectF(self.rect()),self.effect_theme,palette,self.phase)
        size=min(self.height()-8,104);rect=QRectF((self.width()-size)/2,4,size,size)
        draw_portrait(p,self.key,rect,square=True,image=self.player.image())
        if self.effects_enabled:
            p.setPen(QPen(QColor(palette['accent']),1.4));p.setBrush(Qt.NoBrush);p.drawRoundedRect(rect,9,9)
        p.end()
