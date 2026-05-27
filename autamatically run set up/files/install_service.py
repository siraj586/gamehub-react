"""
GameHub Client — Windows Service Installer
===========================================
يثبّت السكريبت كـ Windows Service يشتغل تلقائياً عند تشغيل الجهاز.

الاستخدام:
  python install_service.py install    ← تثبيت الـ Service
  python install_service.py remove     ← إزالة الـ Service
  python install_service.py start      ← تشغيل الـ Service
  python install_service.py stop       ← إيقاف الـ Service
  python install_service.py status     ← حالة الـ Service

متطلبات:
  pip install pywin32
"""

import sys
import os
from pathlib import Path

# ─── تحقق من Windows ─────────────────────────────────────────────────────────
if sys.platform != "win32":
    print("❌ هذا السكريبت مخصص لـ Windows فقط.")
    print("   على Linux استخدم: install_service_linux.py")
    sys.exit(1)

try:
    import win32service
    import win32serviceutil
    import win32event
    import servicemanager
    import subprocess
except ImportError:
    print("❌ مكتبة pywin32 غير مثبتة.")
    print("   ثبّتها بـ: pip install pywin32")
    sys.exit(1)


SCRIPT_DIR   = Path(__file__).parent
CLIENT_SCRIPT = SCRIPT_DIR / "gamehub_client.py"
PYTHON_EXE   = sys.executable  # نفس بيئة Python الحالية


class GameHubService(win32serviceutil.ServiceFramework):
    _svc_name_        = "GameHubClient"
    _svc_display_name_ = "GameHub Client — Auto Session"
    _svc_description_  = "يفتح جلسة GameHub تلقائياً عند تشغيل الجهاز ويغلقها عند إيقافه."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.process    = None

    def SvcStop(self):
        """يُستدعى عند إيقاف الـ Service"""
        servicemanager.LogInfoMsg("GameHub Client: جاري الإيقاف...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.process:
            self.process.terminate()
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        """يُستدعى عند تشغيل الـ Service"""
        servicemanager.LogInfoMsg("GameHub Client: بدأ التشغيل...")
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

        # شغّل السكريبت الرئيسي كـ subprocess
        self.process = subprocess.Popen(
            [PYTHON_EXE, str(CLIENT_SCRIPT)],
            cwd=str(SCRIPT_DIR),
        )

        # انتظر إشارة الإيقاف
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()

        servicemanager.LogInfoMsg("GameHub Client: تم الإيقاف.")


# ─── CLI ─────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print_help()
        return

    command = sys.argv[1].lower()

    if command == "install":
        print("📦 جاري تثبيت GameHub Client كـ Windows Service...")
        win32serviceutil.InstallService(
            pythonClassString=f"{__name__}.GameHubService",
            serviceName=GameHubService._svc_name_,
            displayName=GameHubService._svc_display_name_,
            description=GameHubService._svc_description_,
            startType=win32service.SERVICE_AUTO_START,  # يبدأ تلقائياً مع Windows
        )
        print("✅ تم تثبيت الـ Service بنجاح!")
        print("   لتشغيله الآن: python install_service.py start")

    elif command == "remove":
        print("🗑️  جاري إزالة GameHub Client Service...")
        try:
            win32serviceutil.StopService(GameHubService._svc_name_)
        except Exception:
            pass
        win32serviceutil.RemoveService(GameHubService._svc_name_)
        print("✅ تم إزالة الـ Service.")

    elif command == "start":
        print("▶️  جاري تشغيل GameHub Client Service...")
        win32serviceutil.StartService(GameHubService._svc_name_)
        print("✅ الـ Service شغّال!")

    elif command == "stop":
        print("⏹️  جاري إيقاف GameHub Client Service...")
        win32serviceutil.StopService(GameHubService._svc_name_)
        print("✅ تم الإيقاف.")

    elif command == "status":
        status = win32serviceutil.QueryServiceStatus(GameHubService._svc_name_)
        state = status[1]
        states = {
            1: "⛔ متوقف (Stopped)",
            2: "🟡 جاري البدء (Start Pending)",
            3: "🟡 جاري الإيقاف (Stop Pending)",
            4: "✅ شغّال (Running)",
        }
        print(f"📊 حالة الـ Service: {states.get(state, f'غير معروف ({state})')}")

    elif command == "debug":
        # تشغيل مباشر بدون Service (للاختبار)
        print("🐛 تشغيل في وضع Debug (بدون Service)...")
        win32serviceutil.HandleCommandLine(GameHubService)

    else:
        print(f"❌ أمر غير معروف: {command}")
        print_help()


def print_help():
    print("""
GameHub Client — Windows Service Manager
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
الاستخدام:
  python install_service.py install    ← تثبيت الـ Service
  python install_service.py remove     ← إزالة الـ Service
  python install_service.py start      ← تشغيل الـ Service
  python install_service.py stop       ← إيقاف الـ Service
  python install_service.py status     ← حالة الـ Service
  python install_service.py debug      ← تشغيل مباشر للاختبار

⚠️  يجب تشغيل هذا السكريبت كـ Administrator
""")


if __name__ == "__main__":
    main()
