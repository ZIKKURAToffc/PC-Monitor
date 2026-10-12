"""Offline colour themes and original vector motifs. No remote images or fonts."""
import re
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QColor,QPainter,QPen,QPainterPath,QPixmap,QFont
from effects import AnimatedDecoration,paint_scene,ANIME_KEYS

def blend(a,b,amount):
    x=QColor(a);y=QColor(b)
    return QColor(round(x.red()*(1-amount)+y.red()*amount),round(x.green()*(1-amount)+y.green()*amount),round(x.blue()*(1-amount)+y.blue()*amount)).name()

def palette(bg,accent,chart,strip_text):
    return dict(bg=bg,accent=accent,chart=chart,strip_text=strip_text,normal='#e4eaf2',muted='#b5c2cf',
                panel=blend(bg,accent,.045),input=blend(bg,accent,.10),alt=blend(bg,accent,.065),hover=blend(bg,accent,.16),
                selection=blend(bg,accent,.20),heading=blend(bg,accent,.14),border=blend(bg,accent,.35),borderstrong=blend(bg,accent,.45),
                grid=blend(bg,accent,.20),graphbg=blend(bg,'#000000',.2),chartgrid=blend(bg,chart,.30),chartfill=blend(bg,chart,.14),
                warning='#ff9baa',hotstrip='#84201f',noticebg=blend(bg,'#ff9baa',.12),noticetext='#ffd0d7')

THEMES={
 'classic':dict(name=('Классический','Класичний','Classic'),description=('Исходные мятные полосы и оранжевые графики.','Початкові м’ятні смуги й помаранчеві графіки.','Original mint strips and orange charts.'),motif=None,palette=palette('#060b09','#18ffe0','#ff442d','#06100b')),
 'arctic':dict(name=('Арктический синий','Арктичний синій','Arctic blue'),description=('Холодный синий, светлый лёд и тёмный графит.','Холодний синій, світла крига й темний графіт.','Cool blue, light ice and dark graphite.'),motif=None,palette=palette('#071322','#8ad8ff','#76b2ff','#071426')),
 'amber':dict(name=('Янтарный','Бурштиновий','Amber'),description=('Тёплый янтарь на глубоком тёмном фоне.','Теплий бурштин на глибокому темному тлі.','Warm amber on a deep dark background.'),motif=None,palette=palette('#16110a','#ffd27a','#ffad7d','#251403')),
 'violet':dict(name=('Фиолетовый неон','Фіолетовий неон','Violet neon'),description=('Светлая лаванда и мягкое фиолетовое свечение.','Світла лаванда й м’яке фіолетове сяйво.','Light lavender and soft violet accents.'),motif=None,palette=palette('#100d1b','#d1b4ff','#c2a0ff','#1c102f')),
 'frieren':dict(name=('Фрирен','Фрірен','Frieren'),description=('Фрирен: шалфей, серебро, магический аметист и посох.','Фрірен: шавлія, срібло, магічний аметист і посох.','Frieren: sage, silver, magical amethyst and a staff.'),motif='staff',palette=palette('#081819','#a8ead2','#d5b6ff','#102725')),
 'one_piece':dict(name=('Ван Пис','Ван Піс','One Piece'),description=('Луффи: морская синь, золотая соломенная шляпа и красный акцент.','Луффі: морська синь, золота солом’яна шляпа й червоний акцент.','Luffy: ocean blue, a golden straw hat and a red accent.'),motif='hat',palette=palette('#0a1524','#ffdf8b','#91d8ff','#251900')),
 'one_punch':dict(name=('Ванпанчмен','Ванпанчмен','One-Punch Man'),description=('Сайтама: жёлтый костюм, красная перчатка и белый плащ.','Сайтама: жовтий костюм, червона рукавичка й білий плащ.','Saitama: a yellow suit, a red glove and a white cape.'),motif='fist',palette=palette('#17121a','#ffe282','#ff9caa','#271708')),
 'naruto':dict(name=('Наруто','Наруто','Naruto'),description=('Наруто: тёплый оранжевый, индиго и сюрикен.','Наруто: теплий помаранчевий, індиго й сюрикен.','Naruto: warm orange, indigo and a shuriken.'),motif='shuriken',palette=palette('#171019','#ffc185','#c4b4ff','#251400')),
 'death_note':dict(name=('Тетрадь смерти','Зошит смерті','Death Note'),description=('Лайт: чёрная тетрадь, серебристый текст и алый акцент.','Лайт: чорний зошит, сріблястий текст і червоний акцент.','Light: a black notebook, silver lettering and a crimson accent.'),motif='book',palette=palette('#101115','#e5e7eb','#ffafba','#17171a')),
 'titan':dict(name=('Атака титанов','Атака титанів','Attack on Titan'),description=('Леви: оливковый плащ, кожа, сталь и парные клинки.','Леві: оливковий плащ, шкіра, сталь і парні клинки.','Levi: an olive cloak, leather, steel and paired blades.'),motif='blades',palette=palette('#111711','#cde3a7','#deb895','#172216')),
}
THEMES['classic']['palette'].update(panel='#0b1510',input='#11251b',alt='#102219',hover='#143328',selection='#174631',heading='#163529',border='#32574a',borderstrong='#426851',grid='#214130',muted='#99b5ab',normal='#bdd3c8',graphbg='#090f0b',chartgrid='#5e3021',chartfill='#33190f',warning='#ff442d',hotstrip='#942014',noticebg='#32170d',noticetext='#ffc4ad')

# Series palettes: strong accents over protected dark data panels.
ANIME_PALETTES={
 'frieren':('#101527','#b9f4df','#cfafff','#102225'),
 'one_piece':('#071c2c','#ffd778','#62dcf5','#241904'),
 'one_punch':('#081b19','#b4f698','#69efc3','#102719'),
 'naruto':('#191126','#ffc280','#f3a9d9','#281406'),
 'death_note':('#180f18','#f7dcec','#ff869e','#24121c'),
 'titan':('#101c20','#d0e5ab','#8ddde4','#15221b'),
}
for key,values in ANIME_PALETTES.items():THEMES[key]['palette']=palette(*values)
SERIES_DESCRIPTIONS={
 'frieren':('Магия Фрирен и Ферн: мята, аметист, руны и светлячки.','Магія Фрірен і Ферн: м’ята, аметист, руни й світлячки.','Frieren and Fern: mint, amethyst, runes and fireflies.'),
 'one_piece':('Морское приключение: бирюза, золото, волны и солнечные искры.','Морська пригода: бірюза, золото, хвилі й сонячні іскри.','Ocean adventure: turquoise, gold, waves and sunny sparks.'),
 'one_punch':('Психическая энергия Тацумаки и Фубуки: изумруд, мята и орбиты.','Психічна енергія Тацумакі й Фубукі: смарагд, м’ята й орбіти.','Tatsumaki and Fubuki: emerald, mint and psychic energy orbits.'),
 'naruto':('Мир шиноби: индиго, оранжевая чакра, розовые акценты и спирали.','Світ шінобі: індиго, помаранчева чакра, рожеві акценти й спіралі.','Shinobi world: indigo, orange chakra, pink accents and spirals.'),
 'death_note':('Готика Мисы: чёрная вишня, жемчужный розовый, алый свет и перья.','Готика Міси: чорна вишня, перлинний рожевий, червоне світло й пір’я.','Misa-inspired gothic style: black cherry, pearl pink, crimson light and feathers.'),
 'titan':('Разведкорпус: сталь, олива, ледяной голубой и парные клинки.','Розвідкорпус: сталь, олива, крижаний блакитний і парні клинки.','Scout Regiment: steel, olive, ice blue and paired blades.'),
}
for key,description in SERIES_DESCRIPTIONS.items():THEMES[key]['description']=description

# Preserve the existing style exactly when Classic is selected.
CLASSIC_COLORS={'#060b09':'bg','#18ffe0':'accent','#99b5ab':'muted','#0b1510':'panel','#0b1711':'panel','#123a2a':'hover','#174631':'selection','#254337':'border','#143328':'hover','#101e17':'panel','#3b6654':'borderstrong','#32574a':'border','#214130':'grid','#0a140f':'panel','#102219':'alt','#21523f':'selection','#163529':'heading','#11251b':'input','#426851':'borderstrong','#27503c':'selection','#15372a':'hover','#06100b':'strip_text','#ff442d':'chart','#5e3021':'chartgrid','#33190f':'chartfill','#090f0b':'graphbg','#942014':'hotstrip','#32170d':'noticebg','#ffc4ad':'noticetext','#b2cfc1':'normal','#bdd3c8':'normal','#ff7777':'warning'}
ACTIVE='classic'
ACTIVE_EFFECTS=True
def set_visual_effects(enabled):
    global ACTIVE_EFFECTS
    ACTIVE_EFFECTS=bool(enabled)
def effects_active(key=None):return ACTIVE_EFFECTS and valid_theme(key or ACTIVE) in ANIME_KEYS

def valid_theme(key):return key if key in THEMES else 'classic'
def set_active_theme(key):
    global ACTIVE
    ACTIVE=valid_theme(key)
def theme_name(key,language='ru'):
    return THEMES[valid_theme(key)]['name'][{'ru':0,'uk':1,'en':2}.get(language,0)]
def theme_description(key,language='ru'):
    return THEMES[valid_theme(key)]['description'][{'ru':0,'uk':1,'en':2}.get(language,0)]
def theme_color(value,key=None):
    if not isinstance(value,str):return value
    key=valid_theme(key or ACTIVE);canonical=value.lower()
    if key=='classic':return '#ff442d' if canonical=='#ff7777' else value
    role=CLASSIC_COLORS.get(canonical)
    return THEMES[key]['palette'][role] if role else value

def theme_css(css,key=None):
    key=valid_theme(key or ACTIVE)
    mapped=re.sub(r'#[0-9a-fA-F]{6}\b',lambda m:theme_color(m.group(),key),str(css))
    if effects_active(key):
        p=THEMES[key]['palette']
        for role in ('panel','input','selection'):
            start=blend(p[role],p['chart'],.045);end=p[role]
            mapped=re.sub(r'(background(?:-color)?\s*:)\s*'+re.escape(end)+r'(?=\s*[;}])',lambda m:m[1]+f'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {start},stop:1 {end})',mapped,flags=re.I)
        start=p['accent'];end=blend(start,'#ffffff',.10)
        mapped=re.sub(r'(background(?:-color)?\s*:)\s*'+re.escape(start)+r'(?=\s*[;}])',lambda m:m[1]+f'qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {start},stop:0.5 {end},stop:1 {start})',mapped,flags=re.I)
    return mapped
def style_widget(widget,css):
    widget.setProperty('_theme_base_css',str(css));mapped=theme_css(css)
    if widget.styleSheet()!=mapped:widget.setStyleSheet(mapped)
def restyle_widgets(widgets):
    for widget in widgets:
        base=widget.property('_theme_base_css')
        if base is not None:
            mapped=theme_css(base)
            if widget.styleSheet()!=mapped:widget.setStyleSheet(mapped)

def contrast(a,b):
    def luminance(value):
        c=QColor(value);parts=[v/255 for v in (c.red(),c.green(),c.blue())]
        parts=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in parts]
        return .2126*parts[0]+.7152*parts[1]+.0722*parts[2]
    a,b=sorted((luminance(a),luminance(b)))
    return (b+.05)/(a+.05)

def emblem(key,size=64):
    key=valid_theme(key);p=THEMES[key]['palette'];pix=QPixmap(size,size);pix.fill(Qt.transparent)
    painter=QPainter(pix);painter.setRenderHint(QPainter.Antialiasing);painter.scale(size/64,size/64)
    painter.setPen(QPen(QColor(p['accent']),3,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));painter.setBrush(Qt.NoBrush)
    motif=THEMES[key]['motif']
    if motif=='staff':
        painter.drawLine(25,55,37,18);painter.drawEllipse(QRectF(29,4,22,22));painter.setBrush(QColor(p['chart']));painter.drawEllipse(QRectF(35,10,10,10));painter.drawLine(18,26,13,31);painter.drawLine(13,26,18,31)
    elif motif=='hat':
        painter.setBrush(QColor(p['accent']));painter.drawEllipse(QRectF(6,34,52,14));painter.drawRoundedRect(QRectF(18,17,28,24),10,10);painter.setPen(QPen(QColor('#ed6b78'),5));painter.drawLine(19,34,45,34)
    elif motif=='fist':
        painter.setBrush(QColor(p['chart']));path=QPainterPath();path.moveTo(20,50);path.lineTo(14,32);path.lineTo(17,21);path.lineTo(27,17);path.lineTo(45,18);path.lineTo(51,28);path.lineTo(46,43);path.lineTo(38,52);path.closeSubpath();painter.drawPath(path);painter.drawLine(25,20,26,31);painter.drawLine(34,19,35,30);painter.drawLine(43,21,43,31)
    elif motif=='shuriken':
        path=QPainterPath();path.moveTo(32,4)
        for x,y in [(39,25),(60,32),(39,39),(32,60),(25,39),(4,32),(25,25)]:path.lineTo(x,y)
        path.closeSubpath();painter.setBrush(QColor(p['chart']));painter.drawPath(path);painter.setBrush(QColor(p['bg']));painter.drawEllipse(QRectF(26,26,12,12))
    elif motif=='book':
        painter.setBrush(QColor(p['panel']));painter.drawRoundedRect(QRectF(15,7,35,49),3,3);painter.drawLine(22,8,22,55);painter.setPen(QPen(QColor(p['chart']),2));painter.drawLine(29,22,44,22);painter.drawLine(29,28,42,28);painter.drawLine(29,40,41,40)
    elif motif=='blades':
        painter.setPen(QPen(QColor(p['chart']),5,Qt.SolidLine,Qt.RoundCap));painter.drawLine(13,10,47,50);painter.drawLine(51,10,17,50);painter.setPen(QPen(QColor(p['accent']),3));painter.drawLine(37,49,49,39);painter.drawLine(15,40,27,50);painter.drawLine(46,50,53,58);painter.drawLine(18,50,11,58)
    else:
        painter.drawEllipse(QRectF(10,10,44,44));painter.drawLine(22,34,29,41);painter.drawLine(29,41,44,24)
    painter.end();return pix

class ThemePreview(AnimatedDecoration):
    def __init__(self,key='classic',parent=None):
        super().__init__(parent)
        from characters import PortraitPlayer,valid_character
        self.key=valid_theme(key);self.character_key=valid_character(self.key);self.show_characters=True;self.player=PortraitPlayer(self);self.player.set_profile(self.character_key);self.setMinimumHeight(240);self.configure_effects(self.key)
    def set_theme(self,key):
        self.key=valid_theme(key);self.set_character(self.character_key);self.configure_effects(self.key,self.effects_enabled,self.animation_enabled)
    def set_character(self,key):
        from characters import valid_character
        self.character_key=valid_character(self.key,key);self.player.set_profile(self.character_key);self.sync_playback();self.update()
    def sync_playback(self):self.player.sync(self.isVisible() and self.show_characters,self.animation_enabled)
    def configure_effects(self,key,enabled=True,animated=True):
        super().configure_effects(key,enabled,animated)
        if hasattr(self,'player'):self.sync_playback()
    def showEvent(self,event):super().showEvent(event);self.sync_playback()
    def hideEvent(self,event):self.player.sync(False,self.animation_enabled);super().hideEvent(event)
    def paintEvent(self,event):
        data=THEMES[self.key];p=data['palette'];q=QPainter(self);q.setRenderHint(QPainter.Antialiasing);q.fillRect(self.rect(),QColor(p['bg']));w=self.width()
        q.setPen(QColor(p['accent']));q.setFont(QFont('Arial',15,QFont.Bold));q.drawText(18,30,'PC MONITOR');q.drawPixmap(w-70,5,emblem(self.key,52))
        if self.effects_enabled:paint_scene(q,QRectF(16,238,w-32,max(0,self.height()-250)),self.key,p,self.phase)
        for i,(name,temp,value) in enumerate([('CPU','47 °C','3 600 MHz'),('GPU','36 °C','67,6 W'),('SYS','29 °C','15,2 GiB')]):
            y=52+i*61;q.fillRect(QRectF(14,y,w-28,22),QColor(p['accent']));q.setPen(QColor(p['strip_text']));q.setFont(QFont('Arial',10,QFont.Bold));q.drawText(24,y+16,name+'  //////  '+temp)
            q.setPen(QPen(QColor(p['chart']),1));q.setBrush(QColor(p['panel']));q.drawRoundedRect(QRectF(14,y+27,w-28,29),4,4);q.setPen(QColor(p['accent']));q.setFont(QFont('Consolas',12,QFont.Bold));q.drawText(26,y+47,value)
        if self.show_characters and self.key in ('frieren','one_piece','one_punch','naruto','death_note','titan'):
            from characters import draw_portrait,character_name,valid_character
            available=self.height()-240
            if available>=72:
                height=min(available-8,180);width=height*2/3
                profile=valid_character(self.key,self.character_key)
                rect=QRectF(w-width-24,238,width,height);draw_portrait(q,profile,rect,image=self.player.image())
                q.setPen(QColor(p['accent']));q.setFont(QFont('Arial',12,QFont.Bold));q.drawText(24,270,character_name(profile,__import__('i18n').LANG))
        q.end()
