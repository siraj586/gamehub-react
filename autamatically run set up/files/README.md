# 🎮 GameHub Client

سكريبت Python يشتغل على كل جهاز في صالة الألعاب.
عند تشغيل الجهاز → يفتح جلسة تلقائياً في GameHub.
عند إيقاف الجهاز  → يُغلق الجلسة تلقائياً.

---

## 📁 الملفات

| الملف | الوظيفة |
|-------|---------|
| `gamehub_client.py` | السكريبت الرئيسي |
| `setup.py` | معالج الإعداد — شغّله مرة واحدة |
| `install_service.py` | تثبيت كـ Windows Service |
| `install_service_linux.py` | تثبيت كـ Linux systemd service |
| `config.example.ini` | مثال على ملف الإعداد |
| `requirements.txt` | المكتبات المطلوبة |

---

## ⚡ التثبيت السريع

### الخطوة 1 — تثبيت Python
تأكد من تثبيت Python 3.10+ على الجهاز.
```
https://www.python.org/downloads/
```

### الخطوة 2 — تثبيت المكتبات
```bash
pip install -r requirements.txt

# Windows فقط (للـ Service):
pip install pywin32
```

### الخطوة 3 — الإعداد
```bash
python setup.py
```
سيسألك عن:
- عنوان السيرفر (IP الجهاز اللي عليه الباك-إند)
- بيانات دخول موظف
- اسم/كود الجهاز الحالي (مثال: PS-01)

### الخطوة 4 — اختبار
```bash
python gamehub_client.py
```
يجب أن ترى في الـ log:
```
✅ تسجيل الدخول نجح
✅ تم فتح الجلسة — ID: 42 | الجهاز: PS-01
💓 جاري المراقبة...
```

---

## 🔧 التثبيت كـ Windows Service (للإنتاج)

بعد ما تتأكد إن الاختبار شغّال، ثبّته كـ Service:

```bash
# شغّل Command Prompt كـ Administrator
python install_service.py install
python install_service.py start
python install_service.py status
```

الـ Service رح يبدأ تلقائياً مع كل تشغيل للـ Windows.

---

## 🐧 التثبيت كـ Linux Service

```bash
sudo python install_service_linux.py install

# مراقبة الـ logs
journalctl -u gamehub-client -f
```

---

## 🔄 كيف يشتغل

```
🖥️  الجهاز يشتغل (Windows Startup)
         ↓
🐍  gamehub_client.py يبدأ تلقائياً
         ↓
🔑  يسجّل دخول → POST /api/auth/login/
         ↓
🎮  يفتح جلسة → POST /api/sessions/
    { stationId: "PS-01", branchId: 1, sessionType: "POST" }
         ↓
✅  الجلسة تظهر في GameHub Dashboard فوراً
         ↓
💓  يراقب السيرفر كل دقيقة (Heartbeat)
         ↓
🔴  الجهاز يُوقَف (Shutdown / Ctrl+C)
         ↓
📡  POST /api/sessions/{id}/end/
         ↓
✅  الجلسة مغلقة في النظام
```

---

## ⚠️ حالات خاصة

| الحالة | ما يصير |
|--------|---------|
| الجهاز مشغول بالفعل | يبحث عن الجلسة النشطة ويتابع معها |
| السيرفر منقطع | يحاول مجدداً كل 30 ثانية |
| السيرفر انقطع بعد فتح الجلسة | يحاول إعادة الاتصال، الجلسة تبقى مفتوحة |
| إغلاق مفاجئ للجهاز | `atexit` يُغلق الجلسة قبل الخروج |

---

## 📋 ملف الـ Log

كل العمليات تُسجَّل في:
```
gamehub_client.log
```

مثال:
```
2026-05-26 10:00:01 [INFO] 🎮 GameHub Client بدأ — الجهاز: PS-01
2026-05-26 10:00:02 [INFO] ✅ تسجيل الدخول نجح — المستخدم: staff1
2026-05-26 10:00:02 [INFO] ✅ تم فتح الجلسة — ID: 42 | الجهاز: PS-01
2026-05-26 11:30:00 [INFO] 🔴 الجهاز يُغلق — جاري إنهاء الجلسة 42...
2026-05-26 11:30:01 [INFO] ✅ تم إغلاق الجلسة — ID: 42
```

---

## ❓ مشاكل شائعة

**❌ "ما لقيت ملف الإعداد"**
```bash
python setup.py
```

**❌ "ما قدر يتصل بالسيرفر"**
- تأكد إن السيرفر شغّال
- تأكد إن الـ IP صحيح في config.ini
- تأكد إن الـ Firewall مو مسدود البورت 8000

**❌ "الجهاز PS-01 مشغول"**
- الجلسة السابقة ما أُغلقت من النظام
- أغلقها يدوياً من Dashboard ثم أعد تشغيل السكريبت

---

## 👨‍💻 المطور

**Siraj Masoud** — GameHub Pro System
