"""
GameHub Client — Linux Service Installer (systemd)
====================================================
يثبّت السكريبت كـ systemd service على Linux.

الاستخدام:
  sudo python install_service_linux.py install
  sudo python install_service_linux.py remove
  sudo python install_service_linux.py status
"""

import sys
import os
import subprocess
from pathlib import Path

if sys.platform == "win32":
    print("❌ هذا السكريبت مخصص لـ Linux فقط. استخدم install_service.py على Windows.")
    sys.exit(1)

SCRIPT_DIR    = Path(__file__).parent.resolve()
CLIENT_SCRIPT = SCRIPT_DIR / "gamehub_client.py"
PYTHON_EXE    = sys.executable
SERVICE_NAME  = "gamehub-client"
SERVICE_FILE  = Path(f"/etc/systemd/system/{SERVICE_NAME}.service")


def install():
    if os.geteuid() != 0:
        print("❌ يجب تشغيل هذا الأمر كـ root (sudo)")
        sys.exit(1)

    service_content = f"""[Unit]
Description=GameHub Client — Auto Session Opener
After=network.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={PYTHON_EXE} {CLIENT_SCRIPT}
WorkingDirectory={SCRIPT_DIR}
Restart=on-failure
RestartSec=30s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    SERVICE_FILE.write_text(service_content)
    print(f"✅ تم إنشاء ملف الـ Service: {SERVICE_FILE}")

    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", SERVICE_NAME], check=True)
    subprocess.run(["systemctl", "start",  SERVICE_NAME], check=True)

    print(f"✅ تم تثبيت وتشغيل {SERVICE_NAME}!")
    print(f"   لمراقبة الـ logs: journalctl -u {SERVICE_NAME} -f")


def remove():
    if os.geteuid() != 0:
        print("❌ يجب تشغيل هذا الأمر كـ root (sudo)")
        sys.exit(1)

    subprocess.run(["systemctl", "stop",    SERVICE_NAME], check=False)
    subprocess.run(["systemctl", "disable", SERVICE_NAME], check=False)
    if SERVICE_FILE.exists():
        SERVICE_FILE.unlink()
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    print(f"✅ تم إزالة {SERVICE_NAME}.")


def status():
    subprocess.run(["systemctl", "status", SERVICE_NAME])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("الاستخدام: sudo python install_service_linux.py [install|remove|status]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "install":
        install()
    elif cmd == "remove":
        remove()
    elif cmd == "status":
        status()
    else:
        print(f"❌ أمر غير معروف: {cmd}")
