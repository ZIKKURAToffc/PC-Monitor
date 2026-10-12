"""Presentation-only RU/UK/EN localization. Protocol IDs and user input stay intact."""
LANG='ru'
MESSAGES={}
def add(ru,uk,en):MESSAGES[ru]=(uk,en)
def set_language(code):
    global LANG
    LANG=code if code in ('ru','uk','en') else 'ru'
def t(value):
    if LANG=='ru' or not isinstance(value,str):return value
    idx=0 if LANG=='uk' else 1
    if value in MESSAGES:return MESSAGES[value][idx]
    # Dynamic UI sentences use known fragments; this is not applied to sensor names.
    for key in sorted(MESSAGES,key=len,reverse=True):
        if len(key)>=5 and key in value:value=value.replace(key,MESSAGES[key][idx])
    return value

_DATA='''Разделы|Розділи|Views
Обзор ресурсов|Огляд ресурсів|Resource overview
Температуры|Температури|Temperatures
Все датчики|Усі датчики|All sensors
Пауза|Пауза|Pause
Продолжить|Продовжити|Resume
Экспорт JSON|Експорт JSON|Export JSON
Подключить датчики|Підключити датчики|Connect sensors
Панель / датчики|Панель / датчики|Dashboard / sensors
Настройки|Налаштування|Settings
Полный экран|Повний екран|Full screen
Компактно|Компактно|Compact
Мониторинг ПК|Моніторинг ПК|PC monitoring
Ник / название|Нік / назва|Nickname / title
Язык интерфейса|Мова інтерфейсу|Interface language
LIVE / ЛОКАЛЬНЫЙ МОНИТОРИНГ|LIVE / ЛОКАЛЬНИЙ МОНІТОРИНГ|LIVE / LOCAL MONITORING
DEMO / СИНТЕТИЧЕСКИЕ ДАННЫЕ|DEMO / СИНТЕТИЧНІ ДАНІ|DEMO / SYNTHETIC DATA
ПАУЗА / ПОКАЗАНИЯ ЗАМОРОЖЕНЫ|ПАУЗА / ПОКАЗНИКИ ЗАМОРОЖЕНІ|PAUSED / READINGS FROZEN
DEMO / показания не являются реальными|DEMO / показники не є реальними|DEMO / readings are not real
DEMO / синтетические|DEMO / синтетичні|DEMO / synthetic
ЗАГРУЗКА ПРОЦЕССОРА|ЗАВАНТАЖЕННЯ ПРОЦЕСОРА|CPU UTILIZATION
ЗАГРУЗКА ВИДЕОКАРТЫ|ЗАВАНТАЖЕННЯ ВІДЕОКАРТИ|GPU UTILIZATION
ОПЕРАТИВНАЯ ПАМЯТЬ|ОПЕРАТИВНА ПАМ’ЯТЬ|SYSTEM MEMORY
ПАМЯТЬ И РЕСУРСЫ|ПАМ’ЯТЬ І РЕСУРСИ|MEMORY AND RESOURCES
ЧАСТОТА CPU|ЧАСТОТА CPU|CPU CLOCK
ЧАСТОТА (ОС)|ЧАСТОТА (ОС)|CLOCK (OS)
ЭФФЕКТ. ЧАСТОТА|ЕФЕКТ. ЧАСТОТА|EFFECTIVE CLOCK
ЧАСТОТА|ЧАСТОТА|CLOCK
МОЩНОСТЬ|ПОТУЖНІСТЬ|POWER
ЗАГРУЗКА|ЗАВАНТАЖЕННЯ|UTILIZATION
ВЕНТИЛЯТОР|ВЕНТИЛЯТОР|FAN
RAM ЗАНЯТО|RAM ВИКОРИСТАНО|RAM USED
RAM ДОСТУПНО|RAM ДОСТУПНО|RAM AVAILABLE
VRAM ЗАНЯТО|VRAM ВИКОРИСТАНО|VRAM USED
VRAM СВОБОДНО|VRAM ВІЛЬНО|VRAM FREE
↑ ОТПРАВКА|↑ НАДСИЛАННЯ|↑ UPLOAD
↓ ЗАГРУЗКА|↓ ЗАВАНТАЖЕННЯ|↓ DOWNLOAD
ДИСКИ · СВОБОДНО / GiB|ДИСКИ · ВІЛЬНО / GiB|DRIVES · FREE / GiB
ДИСКИ|ДИСКИ|DRIVES
занято|використано|used
Нет доступных разделов|Немає доступних розділів|No available volumes
CPU ТЕМПЕРАТУРА|CPU ТЕМПЕРАТУРА|CPU TEMPERATURE
ПЛАТА|ПЛАТА|MOTHERBOARD
ДИСК MAX|ДИСК MAX|DRIVE MAX
ТЕМПЕРАТУРЫ / °C|ТЕМПЕРАТУРИ / °C|TEMPERATURES / °C
Плата|Плата|Motherboard
Накопитель|Накопичувач|Storage
Другое|Інше|Other
Показать:|Показати:|Show:
Устройство / датчик|Пристрій / датчик|Device / sensor
Сейчас, °C|Зараз, °C|Current, °C
Мин, °C|Мін, °C|Min, °C
Макс, °C|Макс, °C|Max, °C
Статус|Стан|Status
Источник|Джерело|Source
Датчик / устройство|Датчик / пристрій|Sensor / device
Тип|Тип|Type
Значение|Значення|Value
Единица|Одиниця|Unit
ВЫШЕ ПОРОГА|ВИЩЕ ПОРОГА|ABOVE THRESHOLD
Ниже порога|Нижче порога|Below threshold
Порог выделения:|Поріг виділення:|Highlight threshold:
Датчиков:|Датчиків:|Sensors:
Выше порога:|Вище порога:|Above threshold:
Нет данных|Немає даних|No data
СЕЙЧАС|ЗАРАЗ|NOW
Сейчас:|Зараз:|Current:
История:|Історія:|History:
Шкала:|Шкала:|Scale:
секунд|секунд|seconds
ядер|ядер|cores
потоков|потоків|threads
Недоступно|Недоступно|Unavailable
Недоступен ·|Недоступний ·|Unavailable ·
не определён|не визначено|not identified
Порог °C|Поріг °C|Limit °C
Настройка панели и всех датчиков|Налаштування панелі та всіх датчиків|Dashboard and sensor configuration
СВОИ КАРТОЧКИ|ВЛАСНІ КАРТКИ|CUSTOM CARDS
Авто / стандартный источник|Авто / стандартне джерело|Auto / default source
Авто: подходящий датчик|Авто: відповідний датчик|Auto: matching sensor
Выберите числовой датчик|Виберіть числовий датчик|Select a numeric sensor
+ Своя карточка|+ Власна картка|+ Custom card
Удалить карточку|Видалити картку|Remove card
Название карточки (пусто — стандартное)|Назва картки (порожньо — стандартна)|Card title (empty — default)
Название своей карточки|Назва власної картки|Custom card title
Скрыть|Приховати|Hide
Сохранить|Зберегти|Save
Отмена|Скасувати|Cancel
Сбросить панель|Скинути панель|Reset dashboard
Датчик|Датчик|Sensor
Выбранный датчик недоступен|Вибраний датчик недоступний|Selected sensor is unavailable
Обновление интерфейса|Оновлення інтерфейсу|Interface refresh
Окно истории|Вікно історії|History window
Порог температуры|Поріг температури|Temperature threshold
Поверх других окон|Поверх інших вікон|Always on top
1 секунда|1 секунда|1 second
2 секунды|2 секунди|2 seconds
5 секунд|5 секунд|5 seconds
60 секунд|60 секунд|60 seconds
120 секунд|120 секунд|120 seconds
5 минут|5 хвилин|5 minutes
AIDA64 / LHM — подключение и диагностика|AIDA64 / LHM — підключення та діагностика|AIDA64 / LHM — connection and diagnostics
Порт локального LHM|Порт локального LHM|Local LHM port
Имя пользователя LHM|Ім’я користувача LHM|LHM username
Пароль LHM|Пароль LHM|LHM password
Температура CPU|Температура CPU|CPU temperature
Частота CPU|Частота CPU|CPU clock
Мощность CPU|Потужність CPU|CPU power
Вентилятор CPU|Вентилятор CPU|CPU fan
Вентилятор GPU|Вентилятор GPU|GPU fan
Если включена Authentication в LHM|Якщо ввімкнено Authentication у LHM|If Authentication is enabled in LHM
Только для этого сеанса, не сохраняется|Лише для цього сеансу, не зберігається|This session only, not saved
Применить|Застосувати|Apply
Обновить список|Оновити список|Refresh list
Копировать диагностику|Копіювати діагностику|Copy diagnostics
Запустить AIDA64|Запустити AIDA64|Launch AIDA64
Запустить LHM|Запустити LHM|Launch LHM
Официальная инструкция|Офіційна інструкція|Official documentation
Закрыть|Закрити|Close
LHM: HTTP → WMI для старых версий|LHM: HTTP → WMI для старих версій|LHM: HTTP → WMI for older versions
LHM: только HTTP (0.9.5+)|LHM: лише HTTP (0.9.5+)|LHM: HTTP only (0.9.5+)
LHM: только WMI (старые версии)|LHM: лише WMI (старі версії)|LHM: WMI only (older versions)
Выбран ранее, сейчас недоступен ·|Вибраний раніше, зараз недоступний ·|Previously selected, now unavailable ·
Ожидание датчиков…|Очікування датчиків…|Waiting for sensors…
Ожидание данных…|Очікування даних…|Waiting for data…
Ожидание телеметрии…|Очікування телеметрії…|Waiting for telemetry…
Подключение…|Підключення…|Connecting…
Подключение / сбор данных…|Підключення / збір даних…|Connecting / collecting data…
Сбор системных данных остановился. Перезапустите приложение.|Збір системних даних зупинився. Перезапустіть програму.|System data collection stopped. Restart the application.
Меню управления мониторингом|Меню керування моніторингом|Monitoring control menu
Управление: пауза, экспорт, датчики, настройки и вид окна|Керування: пауза, експорт, датчики, налаштування та вигляд вікна|Controls: pause, export, sensors, settings and views
Данные ещё не получены.|Дані ще не отримано.|No data received yet.
Не удалось сохранить|Не вдалося зберегти|Could not save
Не удалось запустить|Не вдалося запустити|Could not launch
Проверьте файл|Перевірте файл|Check file
Сохранить телеметрию|Зберегти телеметрію|Save telemetry
Экспорт|Експорт|Export
Нет датчиков в выбранной группе.|Немає датчиків у вибраній групі.|No sensors in the selected group.
Выберите aida64.exe|Виберіть aida64.exe|Select aida64.exe
Выберите LibreHardwareMonitor.exe|Виберіть LibreHardwareMonitor.exe|Select LibreHardwareMonitor.exe
Подключение Shared Memory предназначено для Windows x64.|Підключення Shared Memory призначене для Windows x64.|Shared Memory connection requires Windows x64.
Libre Hardware Monitor предназначен для Windows.|Libre Hardware Monitor призначений для Windows.|Libre Hardware Monitor requires Windows.
Выберите aida64.exe из вашего официального пакета AIDA64.|Виберіть aida64.exe з вашого офіційного пакета AIDA64.|Select aida64.exe from your official AIDA64 package.
Выберите именно LibreHardwareMonitor.exe из официального пакета.|Виберіть саме LibreHardwareMonitor.exe з офіційного пакета.|Select LibreHardwareMonitor.exe from the official package.
Запустите AIDA64 вручную под тем же пользователем.|Запустіть AIDA64 вручну під тим самим користувачем.|Launch AIDA64 manually as the same user.
Запустите LibreHardwareMonitor.exe вручную, при необходимости от имени администратора.|Запустіть LibreHardwareMonitor.exe вручну, за потреби від імені адміністратора.|Launch LibreHardwareMonitor.exe manually, as administrator if needed.
Температура GPU|Температура GPU|GPU temperature
Частота GPU|Частота GPU|GPU clock
Загрузка CPU|Завантаження CPU|CPU utilization
Загрузка GPU|Завантаження GPU|GPU utilization
Мощность GPU|Потужність GPU|GPU power
Плата|Плата|Motherboard
Диск Max|Диск Max|Drive Max
RAM занято|RAM використано|RAM used
RAM доступно|RAM доступно|RAM available
Загрузка RAM|Завантаження RAM|RAM utilization
VRAM занято|VRAM використано|VRAM used
VRAM свободно|VRAM вільно|VRAM free
Отправка сети|Надсилання мережі|Network upload
Загрузка сети|Завантаження мережі|Network download'''
for line in _DATA.splitlines():add(*line.split('|'))

# Long instructions translated as whole messages, not word-by-word.
add('ДЕМО: все значения синтетические. Реальный мониторинг запускается без --demo.', 'ДЕМО: усі значення синтетичні. Реальний моніторинг запускається без --demo.', 'DEMO: all values are synthetic. Start without --demo for real monitoring.')
add('«—» — датчик недоступен. Мин/макс — наблюдения с начала этой сессии. Порог — настройка, не предел производителя.', '«—» — датчик недоступний. Мін/макс — спостереження від початку сеансу. Поріг — налаштування, а не межа виробника.', '“—” — sensor unavailable. Min/max are observations since this session started. The threshold is a setting, not a manufacturer limit.')
add('Все датчики. Warning/Critical Temperature — постоянные пороги, не текущие температуры. Fan #1 не назначается CPU автоматически.', 'Усі датчики. Warning/Critical Temperature — сталі пороги, а не поточні температури. Fan #1 не призначається CPU автоматично.', 'All sensors. Warning/Critical Temperature are fixed limits, not current temperatures. Fan #1 is not assigned to the CPU automatically.')
add('Выбирайте источник каждой карточки, меняйте название или скрывайте её. Список показывает только датчики подходящего устройства, типа и назначения. Свои карточки — любые числовые датчики. Недоступный выбранный источник даёт «—», без автоматической подмены.', 'Вибирайте джерело кожної картки, змінюйте назву або приховуйте її. Список містить лише датчики відповідного пристрою, типу та призначення. Власні картки — будь-які числові датчики. Недоступне вибране джерело дає «—», без автоматичної заміни.', 'Choose the source of each card, rename or hide it. The list only includes sensors with the matching device, type and purpose. Custom cards support any numeric sensor. An unavailable selected source shows “—”, without automatic substitution.')
add('Датчики AIDA64 / LHM / NVIDIA обновляются примерно каждые 3 секунды. Порог выделения не заменяет аппаратные ограничения защиты.', 'Датчики AIDA64 / LHM / NVIDIA оновлюються приблизно кожні 3 секунди. Поріг виділення не замінює апаратні обмеження захисту.', 'AIDA64 / LHM / NVIDIA sensors update roughly every 3 seconds. The highlight threshold does not replace hardware protection limits.')
add('RPM и PWM (%) — разные датчики. Fan #1 не обязательно CPU-кулер. Package — мощность процессора; TDP (%) — не ватты. Неэкспортируемые значения отображаются как «—».', 'RPM і PWM (%) — різні датчики. Fan #1 не обов’язково кулер CPU. Package — потужність процесора; TDP (%) — не вати. Неекспортовані значення відображаються як «—».', 'RPM and PWM (%) are different sensors. Fan #1 is not necessarily the CPU cooler. Package is CPU power; TDP (%) is not watts. Values not exported appear as “—”.')
add('AIDA64 Extreme 8.00.8000: Настройки (Preferences) → Hardware Monitoring → External Applications → Enable shared memory. Отметьте нужные датчики: CPU Clock, температуры, вентиляторы и мощность. Оставьте AIDA64 открытой. Чтение локальное, порт и пароль не нужны.', 'AIDA64 Extreme 8.00.8000: Налаштування (Preferences) → Hardware Monitoring → External Applications → Enable shared memory. Позначте потрібні датчики: CPU Clock, температури, вентилятори та потужність. Залиште AIDA64 відкритою. Читання локальне, порт і пароль не потрібні.', 'AIDA64 Extreme 8.00.8000: Preferences → Hardware Monitoring → External Applications → Enable shared memory. Select CPU Clock, temperatures, fans and power sensors. Keep AIDA64 open. Reading is local; no port or password is needed.')
add('В LHM включите Remote Web Server > Run, порт 8085. Чтение: http://127.0.0.1:8085/data.json. Не открывайте порт в интернет; используйте Authentication и ограничения доступа ОС. WMI — только для старых LHM.', 'У LHM увімкніть Remote Web Server > Run, порт 8085. Читання: http://127.0.0.1:8085/data.json. Не відкривайте порт в інтернет; використовуйте Authentication та обмеження доступу ОС. WMI — лише для старих LHM.', 'In LHM enable Remote Web Server > Run, port 8085. Read from http://127.0.0.1:8085/data.json. Do not expose the port to the internet; use Authentication and OS access restrictions. WMI is for older LHM versions only.')
add('Температуры пока недоступны. Выберите AIDA64 Shared Memory или LHM в «Подключить датчики» и оставьте выбранную программу открытой. Нажмите «Подключить датчики» для инструкции. NVIDIA может отдавать температуру GPU без LHM.', 'Температури поки недоступні. Виберіть AIDA64 Shared Memory або LHM у «Підключити датчики» та залиште програму відкритою. Натисніть «Підключити датчики» для інструкції. NVIDIA може передавати температуру GPU без LHM.', 'Temperatures are not available yet. Select AIDA64 Shared Memory or LHM under “Connect sensors” and keep it open. Use “Connect sensors” for instructions. NVIDIA may provide GPU temperature without LHM.')
add('Максимум текущих датчиков накопителей; Warning/Critical Temperature — лимиты, в максимум не входят.', 'Максимум поточних датчиків накопичувачів; Warning/Critical Temperature — ліміти, що не входять до максимуму.', 'Maximum of current storage temperatures; Warning/Critical Temperature limits are excluded.')
add('FPS из SRTSSFPS AIDA64. Нужен RTSS с обнаруженным 3D-приложением. «—» — нет данных; 0 — переданный ноль.', 'FPS із SRTSSFPS AIDA64. Потрібен RTSS із виявленою 3D-програмою. «—» — немає даних; 0 — переданий нуль.', 'FPS from AIDA64 SRTSSFPS. Requires RTSS with a detected 3D application. “—” means no data; 0 is a reported zero.')
add('SRTSSFPS / AIDA64. Для игрового FPS нужен RTSS. Обновление ~3 с.', 'SRTSSFPS / AIDA64. Для ігрового FPS потрібен RTSS. Оновлення ~3 с.', 'SRTSSFPS / AIDA64. Game FPS requires RTSS. Updates ~3 s.')
add('Ожидание фонового опроса. После применения подождите и обновите список.', 'Очікування фонового опитування. Після застосування зачекайте та оновіть список.', 'Waiting for background polling. After applying, wait and refresh the list.')
add('Параметры применены. Подождите фоновый опрос, затем нажмите «Обновить список». Пароль не сохраняется.', 'Параметри застосовано. Зачекайте на фонове опитування, потім натисніть «Оновити список». Пароль не зберігається.', 'Settings applied. Wait for background polling, then click “Refresh list”. The password is not saved.')

def localize_tree(root):
    """Remember source captions so changing languages is reversible."""
    from PySide6.QtWidgets import QWidget,QLabel,QAbstractButton,QLineEdit,QComboBox,QTabWidget,QTableWidget
    from PySide6.QtGui import QAction
    from PySide6.QtCore import QObject
    def field(obj,key,get,setter):
        cache=(obj.property('_translations') if hasattr(obj,'property') else obj.data(257)) or {};current=get();original,last=cache.get(key,(current,None))
        if current!=last:original=current
        output=t(original);setter(output);cache[key]=(original,output)
        if hasattr(obj,'setProperty'):obj.setProperty('_translations',cache)
        else:obj.setData(257,cache)
    for obj in [root]+root.findChildren(QObject):
        if obj.property('no_translate'):continue
        if isinstance(obj,QWidget):
            field(obj,'tooltip',obj.toolTip,obj.setToolTip)
            field(obj,'accessible',obj.accessibleName,obj.setAccessibleName)
            if obj.windowTitle():field(obj,'title',obj.windowTitle,obj.setWindowTitle)
        if isinstance(obj,(QLabel,QAbstractButton,QAction)):field(obj,'text',obj.text,obj.setText)
        if isinstance(obj,QLineEdit):field(obj,'placeholder',obj.placeholderText,obj.setPlaceholderText)
        if isinstance(obj,QComboBox):
            previous=obj.blockSignals(True)
            for i in range(obj.count()):
                # Hardware names/IDs are never localized.
                data=obj.itemData(i)
                if isinstance(data,str) and data not in ('','ru','uk','en','aida','auto','http','wmi','Все датчики','CPU','GPU','Плата','Накопитель','Другое'):continue
                field(obj,f'item{i}',lambda i=i:obj.itemText(i),lambda v,i=i:obj.setItemText(i,v))
            obj.blockSignals(previous)
        if isinstance(obj,QTabWidget):
            for i in range(obj.count()):field(obj,f'tab{i}',lambda i=i:obj.tabText(i),lambda v,i=i:obj.setTabText(i,v))
        if isinstance(obj,QTableWidget):
            for i in range(obj.columnCount()):
                item=obj.horizontalHeaderItem(i)
                if item:field(item,'text',item.text,item.setText)
            columns=(4,5) if obj.columnCount()==6 else (1,4)
            for row in range(obj.rowCount()):
                for col in columns:
                    item=obj.item(row,col)
                    if item:field(item,'text',item.text,item.setText)
add(' — история в процентах от 0 до 100',' — історія у відсотках від 0 до 100',' — history in percent from 0 to 100')
add('датчиков','датчиків','sensors')
add('температур.','температур.','temperatures.')
add('Нет связи с AIDA64. Включите Shared Memory; подробности — «Подключить датчики».','Немає зв’язку з AIDA64. Увімкніть Shared Memory; подробиці — «Підключити датчики».','No connection to AIDA64. Enable Shared Memory; see “Connect sensors” for details.')
add('Нет связи с LHM. Включите Remote Web Server > Run; подробности — «Подключить датчики». ','Немає зв’язку з LHM. Увімкніть Remote Web Server > Run; подробиці — «Підключити датчики». ','No connection to LHM. Enable Remote Web Server > Run; see “Connect sensors” for details. ')
add('Нет подходящего датчика; выберите вручную','Немає відповідного датчика; виберіть вручну','No matching sensor; select one manually')
add('Ошибка чтения датчиков:','Помилка читання датчиків:','Sensor read error:')
add('Данные датчиков устарели.','Дані датчиків застаріли.','Sensor data is stale.')
add('Ошибка системного мониторинга:','Помилка системного моніторингу:','System monitoring error:')
add('Подключение','Підключення','Connection')
add('Датчики панели','Датчики панелі','Dashboard sensors')
add('Диагностика','Діагностика','Diagnostics')
add('SYS / Память, сеть и накопители','SYS / Пам’ять, мережа та накопичувачі','SYS / Memory, network and storage')
add('Назначения общие с «Панель / датчики». Выбирайте источник каждого показателя, затем нажмите «Применить». В списке только датчики подходящего устройства, типа и назначения; отсутствующий выбранный датчик даёт «—», без подмены.', 'Призначення спільні з «Панель / датчики». Вибирайте джерело кожного показника, потім натисніть «Застосувати». У списку лише датчики відповідного пристрою, типу та призначення; відсутній вибраний датчик дає «—», без заміни.', 'Assignments are shared with “Dashboard / sensors”. Choose each metric’s source, then click “Apply”. Only sensors with the matching device, type and purpose are listed; an unavailable selected sensor shows “—”, without substitution.')
add('FPS требует RTSS и экспорта в AIDA64. RPM — не PWM (%). Warning/Critical Temperature — лимиты, не температуры. Свободное место разделов диска читается из ОС автоматически.', 'FPS потребує RTSS та експорту в AIDA64. RPM — не PWM (%). Warning/Critical Temperature — ліміти, а не температури. Вільне місце розділів диска читається з ОС автоматично.', 'FPS requires RTSS and export in AIDA64. RPM is not PWM (%). Warning/Critical Temperature are limits, not temperatures. Free space on disk volumes is read automatically from the OS.')
add('Настройки всех датчиков сохранены. Дождитесь фонового опроса источника.', 'Налаштування всіх датчиків збережено. Дочекайтеся фонового опитування джерела.', 'All sensor settings saved. Wait for background polling of the source.')
add('ОС / psutil','ОС / psutil','OS / psutil')
add('GPU / резервный источник','GPU / резервне джерело','GPU / fallback source')
add('FPS опубликован источником','FPS опублікований джерелом','FPS published by source')
add('Синтетические данные','Синтетичні дані','Synthetic data')
add('Источник игры не определён — проверьте RTSS','Джерело гри не визначено — перевірте RTSS','Game source not identified — check RTSS')
add('FPS недоступен — проверьте источник','FPS недоступний — перевірте джерело','FPS unavailable — check source')
add('Некорректный FPS от источника','Некоректний FPS від джерела','Invalid FPS from source')
add('Показание FPS устарело','Показник FPS застарів','FPS reading is stale')
add('Подробности: ⚙ → Подключить датчики → FPS.','Подробиці: ⚙ → Підключити датчики → FPS.','Details: ⚙ → Connect sensors → FPS.')
add('Не опубликован','Не опублікований','Not published')
add('Обнаружение игры: неизвестно — AIDA64 не передаёт имя игры.','Виявлення гри: невідомо — AIDA64 не передає назву гри.','Game detection: unknown — AIDA64 does not provide the game name.')
from fps_diagnostics import FPS_GUIDE
add(FPS_GUIDE,
'''Програма читає FPS, опублікований AIDA64 (SRTSSFPS), а не вимірює кадри гри напряму. 0 означає: джерело передало нуль. Це не підтверджує, що гру виявлено, і не дозволяє встановити причину за одним значенням.

1. Запустіть RTSS (RivaTuner Statistics Server) і гру. У профілі RTSS виберіть виконуваний файл самої гри, а не лаунчер; Application detection level не має бути None. Використовуйте звичайні дозволені налаштування моніторингу.
2. Перевірте, чи показує сам RTSS ненульовий FPS під час гри. Якщо RTSS не бачить кадри, наша програма через AIDA64 теж їх не отримає.
3. У AIDA64 → Preferences → Hardware Monitoring → External Applications → Enable shared memory увімкніть експорт RTSS FPS (SRTSSFPS). Залиште AIDA64 відкритою.
4. У «Датчики панелі» перевірте вибір FPS: Авто або RTSS FPS з одиницею FPS. Зачекайте на оновлення AIDA64 (приблизно 3 секунди), потім оновіть список.
5. Якщо RTSS показує FPS, а в діагностиці AIDA64 SRTSSFPS залишається 0, перевіряйте передачу RTSS → AIDA64. Якщо обидва показують 0 або відсутні, перевіряйте виявлення гри у RTSS.

Деякі ігри або античит можуть не дозволяти сторонній моніторинг. Не вимикайте захист гри й не намагайтеся обходити обмеження; використовуйте дозволений грою лічильник FPS. Програма не обчислює FPS із завантаження GPU й не замінює нуль вигаданим значенням.''',
'''The application reads FPS published by AIDA64 (SRTSSFPS); it does not capture game frames directly. 0 means the source reported zero. This does not confirm game detection or identify the cause on its own.

1. Start RTSS (RivaTuner Statistics Server) and the game. In the RTSS profile select the game executable, not its launcher; Application detection level must not be None. Use normal monitoring settings allowed by the game.
2. Check whether RTSS itself shows nonzero FPS during gameplay. If RTSS cannot see frames, this application cannot receive them through AIDA64 either.
3. In AIDA64 → Preferences → Hardware Monitoring → External Applications → Enable shared memory, enable RTSS FPS (SRTSSFPS) export. Keep AIDA64 open.
4. Under “Dashboard sensors”, check the FPS source: Auto or RTSS FPS with FPS units. Wait for AIDA64 to update (roughly 3 seconds), then refresh the list.
5. If RTSS shows FPS but the AIDA64 SRTSSFPS diagnostic remains 0, check RTSS → AIDA64 transfer. If both show 0 or are absent, check game detection in RTSS.

Some games or anti-cheat systems may not allow third-party monitoring. Do not disable game protection or bypass restrictions; use an FPS counter allowed by the game. This application does not estimate FPS from GPU utilization or replace zero with a fabricated value.''')
add('Название процессора','Назва процесора','Processor name')
add('Название видеокарты','Назва відеокарти','Graphics card name')
add('Название материнской платы','Назва материнської плати','Motherboard name')
add('Пусто — стандартное название','Порожньо — стандартна назва','Empty — default name')
add('Разработчик','Розробник','Developer')
add('Датчик не соответствует карточке','Датчик не відповідає картці','Sensor does not match this card')
add('Несовместимое назначение · ','Несумісне призначення · ','Incompatible assignment · ')

add('ПАМЯТЬ GPU','ПАМ’ЯТЬ GPU','GPU MEMORY')
add('Температура памяти GPU','Температура пам’яті GPU','GPU memory temperature')

add('Показания в списках обновляются автоматически. Выбор сохраняется; изменения применяются кнопкой «Применить».','Показники у списках оновлюються автоматично. Вибір зберігається; зміни застосовуються кнопкою «Застосувати».','Readings in the lists update automatically. Selections are preserved; changes are committed with Apply.')

add('RTSS: несколько приложений','RTSS: кілька програм','RTSS: multiple applications')
add('Приложение FPS: не определено','Програма FPS: не визначена','FPS application: unknown')
add('RTSS показывает отслеживаемое приложение; связь с общим FPS AIDA64 не подтверждена.','RTSS показує відстежувану програму; зв’язок із загальним FPS AIDA64 не підтверджено.','RTSS reports the tracked application; its link to the aggregate AIDA64 FPS is unconfirmed.')

add('FPS = 0 — проверьте RTSS','FPS = 0 — перевірте RTSS','FPS = 0 — check RTSS')

add('Последнее подтверждённое имя: временный сбой чтения RTSS, ожидание обновления.','Остання підтверджена назва: тимчасова помилка читання RTSS, очікування оновлення.','Last confirmed name: temporary RTSS read failure, waiting for an update.')

add('Опрос датчиков','Опитування датчиків','Sensor polling')
add('мс','мс','ms')
add('250 мс','250 мс','250 ms')
add('500 мс','500 мс','500 ms')
add('Быстрый опрос читает данные источника, но не ускоряет их публикацию в AIDA64/LHM. NVIDIA опрашивается не чаще раза в секунду; WMI — не чаще раза в 2 секунды. Порог выделения не заменяет аппаратные ограничения защиты.','Швидке опитування читає дані джерела, але не прискорює їх публікацію в AIDA64/LHM. NVIDIA опитується не частіше разу на секунду; WMI — не частіше разу на 2 секунди. Поріг виділення не замінює апаратні обмеження захисту.','Fast polling reads source data but does not speed up publication by AIDA64/LHM. NVIDIA is queried at most once per second; WMI at most once every 2 seconds. The highlight threshold does not replace hardware protection limits.')

add('Дата','Дата','Date')
add('Часовой пояс','Часовий пояс','Time zone')

add('Стиль интерфейса','Стиль інтерфейсу','Interface style')
add('Применить стиль','Застосувати стиль','Apply style')
add('Цвета меняются, расположение панелей и показания сохраняются. Аниме-темы используют оригинальные векторные эмблемы, без изображений поверх данных.','Кольори змінюються, розташування панелей і показники зберігаються. Аніме-теми використовують оригінальні векторні емблеми, без зображень поверх даних.','Colors change while panel layout and readings are preserved. Anime themes use original vector emblems, without images covering data.')

add('Персонажи в свободных областях','Персонажі у вільних областях','Characters in empty areas')
add('Цвета и персонажи меняются, расположение панелей и показания сохраняются. Портреты появляются только в свободных областях; на узком экране скрываются.','Кольори й персонажі змінюються, розташування панелей і показники зберігаються. Портрети з’являються лише у вільних областях; на вузькому екрані приховуються.','Colors and characters change while panel layout and readings are preserved. Portraits appear only in empty areas and are hidden on narrow windows.')

add('Показать окно','Показати вікно','Show window')
add('Выход','Вихід','Exit')

add('Персонаж','Персонаж','Character')
add('Визуальные эффекты','Візуальні ефекти','Visual effects')
add('Анимация эффектов','Анімація ефектів','Animated effects')

add('Анимация GIF и эффектов','Анімація GIF та ефектів','Animate GIFs and effects')

add('Запускать вместе с Windows','Запускати разом із Windows','Start with Windows')
add('Автозапуск','Автозапуск','Startup')
add('Автозапуск доступен в собранном EXE для Windows.','Автозапуск доступний у зібраному EXE для Windows.','Startup is available in the compiled Windows EXE.')
add('После входа в Windows приложение откроется с видимым окном и значком в трее. Изменение применяется кнопкой «Сохранить».','Після входу у Windows програма відкриється з видимим вікном і значком у треї. Зміна застосовується кнопкою «Зберегти».','After Windows sign-in, the app opens with a visible window and a tray icon. The change is committed with Save.')
add('Не удалось прочитать настройки автозапуска.','Не вдалося прочитати налаштування автозапуску.','Could not read startup settings.')
add('Не удалось изменить автозапуск. Настройки не сохранены.','Не вдалося змінити автозапуск. Налаштування не збережено.','Could not change startup. Settings were not saved.')
