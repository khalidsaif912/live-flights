# 📋 دليل نظام إدارة رحلات مطار مسقط الدولي

## 🎯 نظرة عامة

نظام متكامل لجلب وإدارة بيانات الرحلات المغادرة من مطار مسقط الدولي (MCT) بشكل تلقائي ومحدث.

### ✨ المميزات

- ✅ **جلب تلقائي** للرحلات من موقع المطار الرسمي
- ✅ **نظام ذكي** للتعامل مع حجب Cloudflare
- ✅ **ملفين منفصلين**: رحلات حالية (24 ساعة) + أرشيف كامل
- ✅ **منع التكرار** مع تحديث البيانات المتغيرة فقط
- ✅ **تصدير متعدد**: JSON + Excel
- ✅ **جدولة تلقائية** للتحديثات
- ✅ **سجل زمني** لكل رحلة (أول ظهور + آخر تحديث)

---

## 📦 التثبيت

### المتطلبات الأساسية
- Python 3.10 أو أحدث
- نظام التشغيل: Windows / Linux / macOS

### خطوات التثبيت

#### 1. تثبيت المكتبات الأساسية

```bash
pip install requests beautifulsoup4 cloudscraper openpyxl pandas
```

#### 2. تثبيت Playwright (اختياري لكن موصى به)

```bash
pip install playwright
playwright install chromium
```

**ملاحظة:** Playwright يحسن نسبة النجاح في جلب البيانات بشكل كبير.

---

## 🚀 الاستخدام

### التشغيل اليدوي (مرة واحدة)

```bash
python flight_manager.py
```

### التشغيل التلقائي المستمر

```bash
# التحديث كل 30 دقيقة (افتراضي)
python auto_update.py

# التحديث كل 15 دقيقة
python auto_update.py --interval 15

# التحديث كل ساعة
python auto_update.py --interval 60

# تشغيل صامت (بدون رسائل كثيرة)
python auto_update.py --quiet

# تشغيل مرة واحدة فقط
python auto_update.py --once
```

---

## 📂 بنية الملفات

بعد التشغيل الأول، سيتم إنشاء المجلد `flight_data/` بالملفات التالية:

```
flight_data/
├── live_flights.json          # الرحلات الحالية (24 ساعة القادمة)
├── archive_flights.json       # الأرشيف الكامل (جميع الرحلات)
├── live_flights.xlsx          # Excel للرحلات الحالية
├── archive_flights.xlsx       # Excel للأرشيف الكامل
└── metadata.json             # معلومات التحديث الأخير
```

### 📊 تفصيل الملفات

#### 1. `live_flights.json` - الرحلات الحالية

**الوصف:** يحتوي على الرحلات التي ستقلع خلال **24 ساعة القادمة** فقط.

**التحديث:** يتم **استبداله بالكامل** في كل تحديث.

**الاستخدام:** للمراقبة الفورية والتطبيقات التي تحتاج فقط للرحلات الحالية.

**مثال:**
```json
[
  {
    "code": "WY101",
    "date": "9MAY",
    "airline": "Oman Air",
    "destination": "LHR",
    "sourceDestination": "London Heathrow",
    "stdEtd": "1415/1430",
    "status": "Scheduled",
    "scheduledAt": "2026-05-09T14:15:00+04:00",
    "estimatedAt": "2026-05-09T14:30:00+04:00",
    "gate": "",
    "terminal": "",
    "remarks": "",
    "firstSeen": "2026-05-09T10:00:00Z",
    "lastUpdated": "2026-05-09T12:00:00Z"
  }
]
```

#### 2. `archive_flights.json` - الأرشيف الكامل

**الوصف:** يحتوي على **جميع الرحلات** التي تم جلبها منذ بداية التشغيل.

**التحديث:** يتم **الدمج الذكي**:
- رحلة جديدة → إضافتها
- رحلة موجودة + بيانات متغيرة → تحديث البيانات
- رحلة موجودة + لا تغيير → البقاء كما هي

**المفتاح الفريد:** `رقم الرحلة + التاريخ + الوجهة + الوقت المجدول`

**الاحتفاظ بالتاريخ:**
- `firstSeen`: لا يتغير أبداً (أول ظهور للرحلة)
- `lastUpdated`: يتحدث في كل تحديث

**الاستخدام:** للتحليلات التاريخية، الإحصائيات، التقارير طويلة المدى.

#### 3. `live_flights.xlsx` و `archive_flights.xlsx`

**الوصف:** نفس البيانات لكن بصيغة Excel منسقة.

**المميزات:**
- عناوين ملونة ومنسقة
- أعمدة عريضة للقراءة
- جاهزة للفتح في Excel أو Google Sheets
- تواريخ منسقة بشكل قابل للقراءة

**الأعمدة:**
| العمود | الوصف |
|--------|-------|
| رقم الرحلة | مثل: WY101 |
| التاريخ | مثل: 9MAY |
| شركة الطيران | مثل: Oman Air |
| الوجهة | رمز IATA (مثل: LHR) |
| الوجهة الكاملة | مثل: London Heathrow |
| الوقت المجدول | مثل: 1415 |
| الوقت المتوقع | مثل: 1430 |
| الحالة | مثل: Scheduled, Boarding, Departed |
| البوابة | رقم البوابة (إن وجد) |
| المبنى | رقم المبنى (إن وجد) |
| ملاحظات | أي ملاحظات إضافية |
| أول ظهور | تاريخ ووقت أول ظهور للرحلة |
| آخر تحديث | تاريخ ووقت آخر تحديث |

#### 4. `metadata.json` - معلومات التحديث

**الوصف:** يحتوي على معلومات حول آخر عملية تحديث.

**مثال:**
```json
{
  "status": "success",
  "message": "تم التحديث بنجاح",
  "liveFlightsCount": 12,
  "archiveFlightsCount": 1543,
  "sourceUrl": "https://www.muscatairport.co.om/flightstatusframe?type=2",
  "updatedAt": "2026-05-09T12:00:00Z",
  "timezone": "Asia/Muscat"
}
```

---

## 🔄 آلية عمل النظام

### 1. الجلب من الموقع

يستخدم النظام **3 استراتيجيات** للتعامل مع حماية Cloudflare:

```
┌─────────────────────────────────────────┐
│  المحاولة 1: CloudScraper              │
│  (يحل تحديات JavaScript تلقائياً)      │
└─────────────────────────────────────────┘
              ↓ فشلت؟
┌─────────────────────────────────────────┐
│  المحاولة 2: Requests + Headers كاملة  │
│  (يحاكي متصفح حقيقي)                   │
└─────────────────────────────────────────┘
              ↓ فشلت؟
┌─────────────────────────────────────────┐
│  المحاولة 3: Playwright                │
│  (متصفح Chromium حقيقي)                │
└─────────────────────────────────────────┘
```

### 2. تحليل البيانات

```python
# استخراج البيانات من جدول HTML
جدول الرحلات → BeautifulSoup → قائمة Flight objects
```

**الحقول المستخرجة:**
- رقم الرحلة
- شركة الطيران
- الوجهة
- التاريخ
- الوقت المجدول
- الوقت المتوقع
- الحالة

### 3. الفلترة والتصنيف

```
جميع الرحلات
    │
    ├─→ فلتر زمني (24 ساعة) → live_flights.json
    │
    └─→ بدون فلتر → للدمج مع الأرشيف
```

### 4. الدمج الذكي مع الأرشيف

```python
# لكل رحلة جديدة:
مفتاح = رقم_الرحلة + التاريخ + الوجهة + الوقت_المجدول

if مفتاح موجود في الأرشيف:
    # تحديث البيانات المتغيرة فقط
    update(status, estimatedAt, gate, terminal)
    keep(firstSeen)  # لا يتغير
    update(lastUpdated)  # يتحدث للآن
else:
    # رحلة جديدة تماماً
    add_to_archive()
    set(firstSeen = now)
    set(lastUpdated = now)
```

**مثال عملي:**

```
الأرشيف الحالي:
├─ WY101 | 9MAY | LHR | 2026-05-09T14:15 → status: Scheduled

رحلة جديدة مجلوبة:
└─ WY101 | 9MAY | LHR | 2026-05-09T14:15 → status: Boarding

النتيجة:
└─ WY101 | 9MAY | LHR | 2026-05-09T14:15 → status: Boarding
   firstSeen: (لم يتغير)
   lastUpdated: (محدث للآن)
```

---

## ⏰ الجدولة التلقائية

### Linux / macOS (Cron)

افتح crontab:
```bash
crontab -e
```

أضف السطر التالي للتحديث كل 30 دقيقة:
```bash
*/30 * * * * cd /path/to/project && /usr/bin/python3 flight_manager.py >> logs/cron.log 2>&1
```

**أمثلة أخرى:**
```bash
# كل 15 دقيقة
*/15 * * * * cd /path/to/project && python3 flight_manager.py

# كل ساعة
0 * * * * cd /path/to/project && python3 flight_manager.py

# كل 6 ساعات
0 */6 * * * cd /path/to/project && python3 flight_manager.py

# يومياً عند الساعة 6 صباحاً
0 6 * * * cd /path/to/project && python3 flight_manager.py
```

### Windows (Task Scheduler)

1. افتح **Task Scheduler** (جدولة المهام)
2. اختر **Create Basic Task** (إنشاء مهمة أساسية)
3. سمّها: "Muscat Flights Update"
4. المحفز: **Daily** أو **Repeat every X minutes**
5. الإجراء: **Start a Program** (بدء برنامج)
   - Program: `python.exe`
   - Arguments: `C:\path\to\flight_manager.py`
   - Start in: `C:\path\to\project`

### Python Schedule (متعدد المنصات)

```python
import schedule
import time
import subprocess

def job():
    subprocess.run(["python", "flight_manager.py"])

# التحديث كل 30 دقيقة
schedule.every(30).minutes.do(job)

# أو كل ساعة
# schedule.every().hour.do(job)

# أو يومياً عند 6 صباحاً
# schedule.every().day.at("06:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
```

---

## 🔧 التخصيص

### تغيير فترة التحديث

في `auto_update.py`:
```python
# تغيير الفترة الافتراضية من 30 إلى 15 دقيقة
parser.add_argument("--interval", type=int, default=15, ...)
```

### تغيير مسارات الملفات

في `flight_manager.py`:
```python
OUTPUT_DIR = Path("my_custom_folder")
LIVE_JSON = OUTPUT_DIR / "current.json"
ARCHIVE_JSON = OUTPUT_DIR / "all_flights.json"
```

### تغيير فلتر الوقت

في `flight_manager.py`:
```python
# من 24 ساعة إلى 48 ساعة
def filter_next_24_hours(flights, now=None):
    ...
    end = now + timedelta(hours=48)  # كان 24
```

### إضافة وجهات جديدة للأسماء المستعارة

في `flight_manager.py`:
```python
DESTINATION_ALIASES = {
    "LON": "LHR",
    "LONDON": "LHR",
    "DXB": "DXB",
    "DUBAI": "DXB",
    # أضف هنا:
    "AUH": "AUH",
    "ABU DHABI": "AUH",
}
```

---

## 🔍 استخدامات متقدمة

### 1. استخراج إحصائيات

```python
import json

# قراءة الأرشيف
with open("flight_data/archive_flights.json") as f:
    flights = json.load(f)

# أكثر الوجهات
from collections import Counter
destinations = Counter(f["destination"] for f in flights)
print("أكثر 10 وجهات:")
for dest, count in destinations.most_common(10):
    print(f"  {dest}: {count}")

# الرحلات حسب شركة الطيران
airlines = Counter(f["airline"] for f in flights)
print("\nالرحلات حسب الناقل:")
for airline, count in airlines.most_common():
    print(f"  {airline}: {count}")
```

### 2. تصدير إلى CSV

```python
import pandas as pd

# قراءة JSON
df = pd.read_json("flight_data/archive_flights.json")

# حفظ CSV
df.to_csv("flight_data/archive_flights.csv", index=False, encoding="utf-8-sig")
```

### 3. تصفية حسب وجهة معينة

```python
import json

with open("flight_data/archive_flights.json") as f:
    flights = json.load(f)

# فقط الرحلات إلى لندن
london_flights = [f for f in flights if f["destination"] == "LHR"]

# حفظ في ملف منفصل
with open("flight_data/london_flights.json", "w", encoding="utf-8") as f:
    json.dump(london_flights, f, ensure_ascii=False, indent=2)
```

### 4. إنشاء تقرير يومي

```python
from datetime import datetime
import json

with open("flight_data/live_flights.json") as f:
    flights = json.load(f)

today = datetime.now().strftime("%d%b").upper()
today_flights = [f for f in flights if f["date"] == today]

print(f"📊 تقرير رحلات {today}")
print(f"عدد الرحلات: {len(today_flights)}")
print("\nالرحلات:")
for f in today_flights:
    print(f"  {f['code']:8} → {f['destination']:4} ({f['airline']}) - {f['status']}")
```

---

## 🐛 استكشاف الأخطاء

### المشكلة: لا يتم جلب أي رحلات

**الحلول:**
1. تأكد من تثبيت Playwright:
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. جرب التشغيل اليدوي لرؤية الأخطاء:
   ```bash
   python flight_manager.py
   ```

3. تحقق من الاتصال بالإنترنت والوصول للموقع:
   ```bash
   curl https://www.muscatairport.co.om/flightstatusframe?type=2
   ```

### المشكلة: Excel لا يتم إنشاؤه

**الحل:** تثبيت openpyxl:
```bash
pip install openpyxl
```

### المشكلة: خطأ في التواريخ/الأوقات

**الحل:** تأكد من تثبيت zoneinfo (Python 3.9+):
```bash
# للإصدارات الأقدم:
pip install backports.zoneinfo
```

### المشكلة: البيانات لا تتحدث تلقائياً

**الحل:** تحقق من إعدادات Cron/Task Scheduler:
```bash
# تأكد من تشغيل cron (Linux)
sudo service cron status

# أو systemctl (Linux الحديث)
sudo systemctl status cron
```

---

## 📊 مثال على البيانات الكاملة

```json
{
  "code": "WY101",
  "date": "9MAY",
  "destination": "LHR",
  "stdEtd": "1415/1430",
  "status": "Boarding",
  "airline": "Oman Air",
  "sourceDestination": "London Heathrow (LHR)",
  "scheduledAt": "2026-05-09T14:15:00+04:00",
  "estimatedAt": "2026-05-09T14:30:00+04:00",
  "gate": "B12",
  "terminal": "1",
  "remarks": "",
  "lastUpdated": "2026-05-09T12:30:00Z",
  "firstSeen": "2026-05-01T08:00:00Z"
}
```

**شرح الحقول:**
- `code`: رقم الرحلة (WY = Oman Air, 101 = رقم الرحلة)
- `date`: التاريخ بصيغة مختصرة (9MAY = 9 مايو)
- `destination`: رمز IATA للوجهة (LHR = London Heathrow)
- `stdEtd`: الوقت المجدول/المتوقع (1415 = 2:15 PM, 1430 = 2:30 PM)
- `status`: حالة الرحلة (Scheduled, Boarding, Departed, Delayed, Cancelled)
- `scheduledAt`: الوقت المجدول بصيغة ISO مع المنطقة الزمنية
- `estimatedAt`: الوقت المتوقع بصيغة ISO
- `firstSeen`: أول مرة ظهرت فيها الرحلة (لا يتغير)
- `lastUpdated`: آخر تحديث للبيانات (يتحدث في كل مرة)

---

## 📈 الإحصائيات والتحليلات

### احتساب المتوسطات

```python
import json
from datetime import datetime
from collections import defaultdict

with open("flight_data/archive_flights.json") as f:
    flights = json.load(f)

# متوسط التأخير لكل وجهة
delays_by_dest = defaultdict(list)

for f in flights:
    if f["scheduledAt"] and f["estimatedAt"]:
        sched = datetime.fromisoformat(f["scheduledAt"])
        estim = datetime.fromisoformat(f["estimatedAt"])
        delay = (estim - sched).total_seconds() / 60  # بالدقائق
        delays_by_dest[f["destination"]].append(delay)

print("متوسط التأخير (بالدقائق) حسب الوجهة:")
for dest, delays in sorted(delays_by_dest.items()):
    avg = sum(delays) / len(delays)
    print(f"  {dest}: {avg:.1f} دقيقة")
```

---

## 🔐 الأمان والخصوصية

- ✅ لا يتم تخزين أي بيانات شخصية
- ✅ جميع البيانات عامة من موقع المطار الرسمي
- ✅ لا توجد عمليات تسجيل دخول أو API keys مطلوبة
- ✅ البيانات محلية فقط (لا يتم إرسالها لأي خادم)

---

## 📝 الترخيص

هذا المشروع للاستخدام الشخصي والتعليمي.

---

## 🆘 الدعم

للأسئلة أو المشاكل:
1. راجع قسم **استكشاف الأخطاء** أعلاه
2. تحقق من ملفات السجل (logs)
3. تأكد من تثبيت جميع المتطلبات

---

## 🎉 ملاحظات ختامية

- النظام يعمل بشكل كامل ومستقل
- يحفظ سجل دائم لجميع الرحلات
- يمنع التكرار بذكاء
- يحدّث البيانات المتغيرة فقط
- يصدر لصيغ متعددة (JSON + Excel)
- قابل للتخصيص بالكامل

**بالتوفيق! ✈️**
