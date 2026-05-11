#!/usr/bin/env python3
"""
سكريبت الإعداد السريع لنظام رحلات مطار مسقط
==============================================

يقوم بـ:
1. فحص المتطلبات
2. تثبيت المكتبات المفقودة
3. إنشاء المجلدات
4. اختبار الاتصال
5. تشغيل تجريبي

الاستخدام:
    python setup.py
"""

import sys
import subprocess
import os
from pathlib import Path


def print_header(text):
    """طباعة عنوان منسق"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def check_python_version():
    """فحص إصدار Python"""
    print_header("🔍 فحص إصدار Python")
    
    version = sys.version_info
    print(f"الإصدار الحالي: Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ خطأ: يتطلب Python 3.9 أو أحدث")
        print("   قم بتحديث Python من: https://www.python.org/downloads/")
        return False
    
    print("✅ إصدار Python مناسب")
    return True


def check_and_install_package(package, import_name=None):
    """فحص وتثبيت مكتبة"""
    import_name = import_name or package
    
    try:
        __import__(import_name)
        print(f"  ✅ {package} مثبت")
        return True
    except ImportError:
        print(f"  ⚠️  {package} غير مثبت - جاري التثبيت...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"  ✅ تم تثبيت {package}")
            return True
        except Exception as e:
            print(f"  ❌ فشل تثبيت {package}: {e}")
            return False


def install_dependencies():
    """تثبيت المتطلبات"""
    print_header("📦 فحص وتثبيت المتطلبات")
    
    packages = [
        ("requests", "requests"),
        ("beautifulsoup4", "bs4"),
        ("cloudscraper", "cloudscraper"),
        ("openpyxl", "openpyxl"),
        ("pandas", "pandas"),
    ]
    
    all_ok = True
    for package, import_name in packages:
        if not check_and_install_package(package, import_name):
            all_ok = False
    
    # Playwright (اختياري)
    print("\n  📌 Playwright (اختياري لكن موصى به):")
    try:
        __import__("playwright")
        print("  ✅ Playwright مثبت")
    except ImportError:
        print("  ⚠️  Playwright غير مثبت")
        response = input("    هل تريد تثبيته؟ (نعم/لا): ").strip().lower()
        if response in ["نعم", "yes", "y", "ن"]:
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "playwright"],
                    stdout=subprocess.DEVNULL
                )
                print("  ✅ تم تثبيت Playwright")
                print("  🔄 جاري تثبيت متصفح Chromium...")
                subprocess.check_call(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    stdout=subprocess.DEVNULL
                )
                print("  ✅ تم تثبيت Chromium")
            except Exception as e:
                print(f"  ⚠️  فشل تثبيت Playwright (يمكنك المتابعة بدونه)")
        else:
            print("  ⏭️  تم تخطي Playwright")
    
    return all_ok


def create_directories():
    """إنشاء المجلدات المطلوبة"""
    print_header("📁 إنشاء المجلدات")
    
    dirs = ["flight_data", "logs"]
    
    for dir_name in dirs:
        path = Path(dir_name)
        if path.exists():
            print(f"  ✅ {dir_name}/ موجود بالفعل")
        else:
            path.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ تم إنشاء {dir_name}/")
    
    return True


def test_connection():
    """اختبار الاتصال بموقع المطار"""
    print_header("🌐 اختبار الاتصال")
    
    try:
        import requests
        url = "https://www.muscatairport.co.om"
        print(f"  🔄 جاري الاتصال بـ {url}")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        print(f"  ✅ الاتصال ناجح (الرمز: {response.status_code})")
        return True
        
    except Exception as e:
        print(f"  ⚠️  فشل الاتصال: {e}")
        print("  ℹ️  قد تحتاج إلى:")
        print("     - التحقق من اتصال الإنترنت")
        print("     - التحقق من إعدادات الجدار الناري")
        print("     - استخدام VPN إذا كان الموقع محجوب")
        return False


def run_test():
    """تشغيل اختبار تجريبي"""
    print_header("🧪 تشغيل اختبار تجريبي")
    
    try:
        print("  🔄 جاري التشغيل...")
        result = subprocess.run(
            [sys.executable, "flight_manager.py"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("  ✅ التشغيل التجريبي نجح!")
            
            # فحص الملفات المنشأة
            files = [
                "flight_data/live_flights.json",
                "flight_data/archive_flights.json",
                "flight_data/metadata.json"
            ]
            
            print("\n  📋 الملفات المنشأة:")
            for file in files:
                if Path(file).exists():
                    size = Path(file).stat().st_size
                    print(f"     ✅ {file} ({size} بايت)")
                else:
                    print(f"     ❌ {file} (غير موجود)")
            
            return True
        else:
            print("  ❌ فشل التشغيل التجريبي")
            if result.stderr:
                print("\n  الخطأ:")
                print("  " + "\n  ".join(result.stderr.split("\n")[:10]))
            return False
            
    except subprocess.TimeoutExpired:
        print("  ⏱️  انتهت مهلة الاختبار (أكثر من 60 ثانية)")
        return False
    except Exception as e:
        print(f"  ❌ خطأ: {e}")
        return False


def show_next_steps():
    """عرض الخطوات التالية"""
    print_header("🎉 الإعداد اكتمل!")
    
    print("\n📝 الخطوات التالية:\n")
    
    print("1️⃣  تشغيل يدوي (مرة واحدة):")
    print("   python flight_manager.py\n")
    
    print("2️⃣  تشغيل تلقائي مستمر:")
    print("   python auto_update.py\n")
    
    print("3️⃣  تشغيل تلقائي مع فترة مخصصة:")
    print("   python auto_update.py --interval 15    # كل 15 دقيقة\n")
    
    print("4️⃣  جدولة تلقائية (Linux/Mac):")
    print("   crontab -e")
    print("   أضف: */30 * * * * cd $(pwd) && python3 flight_manager.py\n")
    
    print("5️⃣  جدولة تلقائية (Windows):")
    print("   افتح Task Scheduler وأنشئ مهمة جديدة\n")
    
    print("📊 الملفات المنشأة:")
    print("   - flight_data/live_flights.json       (الرحلات الحالية)")
    print("   - flight_data/archive_flights.json    (الأرشيف الكامل)")
    print("   - flight_data/live_flights.xlsx       (Excel)")
    print("   - flight_data/archive_flights.xlsx    (Excel)")
    print("   - flight_data/metadata.json           (معلومات التحديث)")
    
    print("\n📖 للمزيد من المعلومات:")
    print("   اقرأ README_AR.md\n")


def main():
    """الوظيفة الرئيسية"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║         🛫 نظام إدارة رحلات مطار مسقط الدولي 🛬         ║
    ║                   سكريبت الإعداد السريع                   ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    steps = [
        ("فحص Python", check_python_version),
        ("تثبيت المتطلبات", install_dependencies),
        ("إنشاء المجلدات", create_directories),
        ("اختبار الاتصال", test_connection),
    ]
    
    for step_name, step_func in steps:
        if not step_func():
            print(f"\n❌ فشل: {step_name}")
            print("   قم بحل المشكلة ثم أعد تشغيل setup.py")
            return 1
    
    # التشغيل التجريبي (اختياري)
    print_header("🎯 خطوة أخيرة")
    response = input("هل تريد تشغيل اختبار تجريبي الآن؟ (نعم/لا): ").strip().lower()
    
    if response in ["نعم", "yes", "y", "ن"]:
        run_test()
    else:
        print("  ⏭️  تم تخطي التشغيل التجريبي")
    
    show_next_steps()
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ تم الإلغاء بواسطة المستخدم")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ خطأ غير متوقع: {e}")
        sys.exit(1)
