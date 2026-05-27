"""
GameHub Client — Setup Wizard
==============================
شغّل هذا السكريبت مرة واحدة على كل جهاز عند التثبيت.
سيسألك عن المعلومات المطلوبة وينشئ config.ini تلقائياً.
"""

import configparser
import sys
from pathlib import Path
import requests

CONFIG_FILE = Path(__file__).parent / "config.ini"


def test_connection(url: str, username: str, password: str) -> bool:
    """يتحقق من الاتصال بالسيرفر وصحة بيانات الدخول"""
    try:
        print(f"\n🔌 يحاول الاتصال بـ {url} ...")
        res = requests.post(
            f"{url.rstrip('/')}/api/auth/login/",
            json={"username": username, "password": password},
            timeout=10,
        )
        if res.status_code == 200:
            print("✅ الاتصال نجح وبيانات الدخول صحيحة!")
            return True
        elif res.status_code == 400:
            print("❌ اسم المستخدم أو كلمة المرور غلط")
            return False
        else:
            print(f"❌ خطأ من السيرفر: {res.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ ما قدر يتصل بـ {url}")
        print("   تأكد إن السيرفر شغّال وعنوان الـ IP صحيح")
        return False
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return False


def fetch_resource_units(url: str, token: str, branch_id: int) -> list:
    """يجيب قائمة الأجهزة من السيرفر"""
    try:
        headers = {"Authorization": f"Token {token}"}
        res = requests.get(
            f"{url.rstrip('/')}/api/resource-units/",
            headers=headers,
            timeout=10,
        )
        if res.status_code == 200:
            units = res.json()
            return [u for u in units if u.get("branch") == branch_id or not branch_id]
        return []
    except Exception:
        return []


def get_token(url: str, username: str, password: str) -> str | None:
    try:
        res = requests.post(
            f"{url.rstrip('/')}/api/auth/login/",
            json={"username": username, "password": password},
            timeout=10,
        )
        return res.json().get("token") if res.status_code == 200 else None
    except Exception:
        return None


def ask(prompt: str, default: str = "") -> str:
    """يسأل المستخدم ويرجع الإجابة"""
    if default:
        val = input(f"{prompt} [{default}]: ").strip()
        return val if val else default
    else:
        while True:
            val = input(f"{prompt}: ").strip()
            if val:
                return val
            print("   ⚠️  هذا الحقل مطلوب")


def main():
    print("=" * 55)
    print("  🎮 GameHub Client — إعداد الجهاز")
    print("=" * 55)

    if CONFIG_FILE.exists():
        overwrite = input(
            "\n⚠️  يوجد إعداد موجود بالفعل. هل تريد إعادة الإعداد؟ (y/n): "
        ).strip().lower()
        if overwrite != "y":
            print("✅ تم الإلغاء. الإعداد الحالي محفوظ.")
            sys.exit(0)

    print("\n─── معلومات السيرفر ─────────────────────────────")
    api_url = ask("عنوان السيرفر (مثال: http://192.168.1.100:8000)", "http://127.0.0.1:8000")

    print("\n─── بيانات الدخول ───────────────────────────────")
    print("  (حساب موظف أو مدير في GameHub)")
    username = ask("اسم المستخدم")
    password = ask("كلمة المرور")

    # اختبار الاتصال
    connected = test_connection(api_url, username, password)
    if not connected:
        retry = input("\nهل تريد المتابعة على أي حال؟ (y/n): ").strip().lower()
        if retry != "y":
            print("❌ تم الإلغاء.")
            sys.exit(1)

    print("\n─── إعداد الجهاز ────────────────────────────────")

    # إذا الاتصال نجح، اجلب قائمة الأجهزة
    branch_id = int(ask("رقم الفرع (Branch ID)", "1"))
    station_id = None

    if connected:
        token = get_token(api_url, username, password)
        if token:
            units = fetch_resource_units(api_url, token, branch_id)
            if units:
                print("\n  الأجهزة المتاحة في النظام:")
                for i, u in enumerate(units, 1):
                    print(f"    {i}. {u.get('code')} — {u.get('display_name', '')}")
                choice = input(f"\n  اختر رقم الجهاز (1-{len(units)}) أو اكتب الكود مباشرة: ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(units):
                    station_id = units[int(choice) - 1].get("code")
                    print(f"  ✅ تم اختيار: {station_id}")

    if not station_id:
        station_id = ask("كود الجهاز (مثال: PS-01 أو PC-03)")

    retry_delay = ask("وقت الانتظار بين المحاولات (ثانية)", "30")

    # حفظ الإعداد
    cfg = configparser.ConfigParser()

    cfg["server"] = {
        "api_url":              api_url,
        "retry_delay_seconds":  retry_delay,
    }
    cfg["device"] = {
        "station_id": station_id,
        "branch_id":  str(branch_id),
    }
    cfg["account"] = {
        "username": username,
        "password": password,
    }

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        cfg.write(f)

    print("\n" + "=" * 55)
    print(f"✅ تم حفظ الإعداد في: {CONFIG_FILE}")
    print(f"\n   الجهاز:   {station_id}")
    print(f"   السيرفر:  {api_url}")
    print(f"   المستخدم: {username}")
    print("\n─── الخطوة التالية ──────────────────────────────")
    print("  شغّل السكريبت الرئيسي:")
    print("  > python gamehub_client.py")
    print("\n  أو ثبّته كـ Windows Service:")
    print("  > python install_service.py install")
    print("=" * 55)


if __name__ == "__main__":
    main()
