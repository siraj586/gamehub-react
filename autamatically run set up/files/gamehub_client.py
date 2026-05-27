"""
GameHub Client — Python Script
================================
يشتغل بالخلفية على كل جهاز.
- عند التشغيل  → يسجّل دخول ويفتح جلسة تلقائياً
- عند الإغلاق  → يُغلق الجلسة تلقائياً
- يسجّل كل شي في ملف log للمراجعة

التثبيت: اقرأ ملف README.md
"""

import sys
import time
import signal
import logging
import configparser
import atexit
from pathlib import Path
import requests

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.ini"
LOG_FILE    = BASE_DIR / "gamehub_client.log"

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("GameHubClient")


# ─── Config ──────────────────────────────────────────────────────────────────
def load_config():
    """يقرأ config.ini ويتحقق من كل القيم المطلوبة"""
    if not CONFIG_FILE.exists():
        log.error(f"❌ ما لقيت ملف الإعداد: {CONFIG_FILE}")
        log.error("   شغّل أولاً: python setup.py")
        sys.exit(1)

    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_FILE, encoding="utf-8")

    required = {
        "server":   ["api_url"],
        "device":   ["station_id", "branch_id"],
        "account":  ["username", "password"],
    }

    for section, keys in required.items():
        if not cfg.has_section(section):
            log.error(f"❌ القسم [{section}] ناقص في config.ini")
            sys.exit(1)
        for key in keys:
            if not cfg.get(section, key, fallback="").strip():
                log.error(f"❌ القيمة [{section}] {key} فارغة في config.ini")
                sys.exit(1)

    return cfg


# ─── API Client ──────────────────────────────────────────────────────────────
class GameHubAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session  = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.token = None

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/{path.lstrip('/')}"

    def login(self, username: str, password: str) -> bool:
        """تسجيل الدخول وحفظ الـ Token"""
        try:
            res = self.session.post(
                self._url("auth/login/"),
                json={"username": username, "password": password},
                timeout=10,
            )
            res.raise_for_status()
            self.token = res.json().get("token")
            self.session.headers.update({"Authorization": f"Token {self.token}"})
            log.info(f"✅ تسجيل الدخول نجح — المستخدم: {username}")
            return True
        except requests.exceptions.ConnectionError:
            log.error(f"❌ ما قدر يتصل بـ {self.base_url} — تأكد إن السيرفر شغّال")
            return False
        except requests.exceptions.HTTPError as e:
            log.error(f"❌ فشل تسجيل الدخول: {e.response.status_code} — {e.response.text}")
            return False
        except Exception as e:
            log.error(f"❌ خطأ غير متوقع عند تسجيل الدخول: {e}")
            return False

    def open_session(self, station_id: str, branch_id: int, customer_name: str = "") -> dict | None:
        """فتح جلسة جديدة"""
        payload = {
            "stationId":   station_id,
            "branchId":    branch_id,
            "sessionType": "POST",   # مفتوح (Postpaid)
            "name":        customer_name,
        }
        try:
            res = self.session.post(self._url("sessions/"), json=payload, timeout=10)
            res.raise_for_status()
            data = res.json()
            log.info(f"✅ تم فتح الجلسة — ID: {data.get('id')} | الجهاز: {station_id}")
            return data
        except requests.exceptions.HTTPError as e:
            body = e.response.text
            # الجهاز مشغول بالفعل؟
            if "occupied" in body.lower() or "already" in body.lower():
                log.warning(f"⚠️  الجهاز {station_id} مشغول بالفعل، رح يبحث عن الجلسة النشطة...")
                return self.get_active_session(station_id, branch_id)
            log.error(f"❌ فشل فتح الجلسة: {e.response.status_code} — {body}")
            return None
        except Exception as e:
            log.error(f"❌ خطأ عند فتح الجلسة: {e}")
            return None

    def get_active_session(self, station_id: str, branch_id: int) -> dict | None:
        """يجيب الجلسة النشطة على هذا الجهاز إذا موجودة"""
        try:
            res = self.session.get(self._url("sessions/"), timeout=10)
            res.raise_for_status()
            sessions = res.json()
            for s in sessions:
                if (
                    s.get("stationId") == station_id
                    and s.get("branchId") == branch_id
                    and not s.get("endTime")
                ):
                    log.info(f"🔍 لقيت جلسة نشطة موجودة — ID: {s.get('id')}")
                    return s
            return None
        except Exception as e:
            log.error(f"❌ خطأ عند البحث عن الجلسة النشطة: {e}")
            return None

    def close_session(self, session_id: int) -> bool:
        """إغلاق الجلسة"""
        try:
            res = self.session.post(
                self._url(f"sessions/{session_id}/end/"),
                json={"discount": 0},
                timeout=10,
            )
            res.raise_for_status()
            log.info(f"✅ تم إغلاق الجلسة — ID: {session_id}")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                # ممكن الجلسة أغلقت مسبقاً
                log.warning(f"⚠️  الجلسة {session_id} كانت مغلقة بالفعل")
                return True
            log.error(f"❌ فشل إغلاق الجلسة: {e.response.status_code} — {e.response.text}")
            return False
        except Exception as e:
            log.error(f"❌ خطأ عند إغلاق الجلسة: {e}")
            return False

    def heartbeat(self) -> bool:
        """ping للسيرفر للتحقق إنه شغّال"""
        try:
            res = self.session.get(self._url("sessions/"), timeout=5)
            return res.status_code == 200
        except Exception:
            return False


# ─── Main Logic ──────────────────────────────────────────────────────────────
class GameHubClientApp:
    def __init__(self):
        self.cfg         = load_config()
        self.api_url     = self.cfg.get("server",  "api_url")
        self.username    = self.cfg.get("account", "username")
        self.password    = self.cfg.get("account", "password")
        self.station_id  = self.cfg.get("device",  "station_id")
        self.branch_id   = int(self.cfg.get("device", "branch_id", fallback="1"))
        self.retry_delay = int(self.cfg.get("server", "retry_delay_seconds", fallback="30"))

        self.api         = GameHubAPI(self.api_url)
        self.session_id  = None
        self._running    = True

        # سجّل دالة الإغلاق عند خروج البرنامج
        atexit.register(self._on_exit)
        signal.signal(signal.SIGTERM, self._signal_handler)
        if sys.platform != "win32":
            signal.signal(signal.SIGHUP, self._signal_handler)

    def _signal_handler(self, signum, frame):
        log.info(f"📡 استقبل إشارة إيقاف ({signum})، جاري الإغلاق...")
        self._running = False
        self._on_exit()
        sys.exit(0)

    def _on_exit(self):
        """يُنفَّذ دائماً عند إغلاق السكريبت"""
        if self.session_id:
            log.info(f"🔴 الجهاز يُغلق — جاري إنهاء الجلسة {self.session_id}...")
            self.api.close_session(self.session_id)
            self.session_id = None

    def _login_with_retry(self) -> bool:
        """يحاول تسجيل الدخول مرات متعددة"""
        attempts = 0
        while self._running:
            attempts += 1
            log.info(f"🔑 محاولة تسجيل الدخول ({attempts})...")
            if self.api.login(self.username, self.password):
                return True
            log.warning(f"⏳ رح يحاول مجدداً بعد {self.retry_delay} ثانية...")
            time.sleep(self.retry_delay)
        return False

    def _open_session_with_retry(self) -> bool:
        """يحاول فتح الجلسة مرات متعددة"""
        while self._running:
            session_data = self.api.open_session(
                station_id=self.station_id,
                branch_id=self.branch_id,
            )
            if session_data:
                self.session_id = session_data.get("id")
                log.info(f"🎮 الجلسة نشطة — الجهاز: {self.station_id} | ID: {self.session_id}")
                return True
            log.warning(f"⏳ ما قدر يفتح الجلسة، يحاول بعد {self.retry_delay} ثانية...")
            time.sleep(self.retry_delay)
        return False

    def run(self):
        log.info("⏳ انتظار 15 ثانية حتى يشتغل السيرفر...")
        time.sleep(15)
        log.info("=" * 50)
        log.info(f"🎮 GameHub Client بدأ — الجهاز: {self.station_id}")
        log.info(f"🌐 السيرفر: {self.api_url}")
        log.info("=" * 50)

        # 1. تسجيل الدخول
        if not self._login_with_retry():
            return

        # 2. فتح الجلسة
        if not self._open_session_with_retry():
            return

        # 3. حلقة المراقبة — Heartbeat كل دقيقة
        log.info("💓 جاري المراقبة... (Ctrl+C للإيقاف)")
        missed_beats = 0
        while self._running:
            time.sleep(60)
            if not self._running:
                break

            if self.api.heartbeat():
                missed_beats = 0
                log.debug("💓 السيرفر متصل")
            else:
                missed_beats += 1
                log.warning(f"⚠️  السيرفر غير متاح — المحاولة {missed_beats}/5")
                if missed_beats >= 5:
                    log.error("❌ السيرفر منقطع 5 دقائق متتالية، جاري إعادة الاتصال...")
                    if self._login_with_retry():
                        missed_beats = 0
                        log.info("✅ تم إعادة الاتصال بنجاح")


# ─── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = GameHubClientApp()
    try:
        app.run()
    except KeyboardInterrupt:
        log.info("🛑 تم الإيقاف بواسطة المستخدم (Ctrl+C)")
