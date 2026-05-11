#!/bin/bash
# سكريبت إعداد Cron للتحديث التلقائي
# ======================================
# 
# يقوم بإضافة مهمة cron لتشغيل flight_manager.py بشكل دوري
# 
# الاستخدام:
#   chmod +x setup_cron.sh
#   ./setup_cron.sh

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║         إعداد التحديث التلقائي (Cron) - Linux/Mac       ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# الحصول على المسار الكامل للمشروع
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH="$(which python3)"
SCRIPT_PATH="$PROJECT_DIR/flight_manager.py"
LOG_DIR="$PROJECT_DIR/logs"

# إنشاء مجلد السجلات إن لم يكن موجوداً
mkdir -p "$LOG_DIR"

echo "📁 معلومات المسارات:"
echo "   - مسار المشروع: $PROJECT_DIR"
echo "   - مسار Python: $PYTHON_PATH"
echo "   - مسار السكريبت: $SCRIPT_PATH"
echo "   - مسار السجلات: $LOG_DIR"
echo ""

# التحقق من وجود السكريبت
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ خطأ: flight_manager.py غير موجود في $PROJECT_DIR"
    exit 1
fi

echo "⏱️  اختر فترة التحديث:"
echo ""
echo "  1) كل 15 دقيقة"
echo "  2) كل 30 دقيقة (موصى به)"
echo "  3) كل ساعة"
echo "  4) كل 3 ساعات"
echo "  5) كل 6 ساعات"
echo "  6) يومياً عند الساعة 6 صباحاً"
echo "  7) مخصص"
echo ""
read -p "اختر (1-7): " choice

case $choice in
    1)
        CRON_SCHEDULE="*/15 * * * *"
        DESCRIPTION="كل 15 دقيقة"
        ;;
    2)
        CRON_SCHEDULE="*/30 * * * *"
        DESCRIPTION="كل 30 دقيقة"
        ;;
    3)
        CRON_SCHEDULE="0 * * * *"
        DESCRIPTION="كل ساعة"
        ;;
    4)
        CRON_SCHEDULE="0 */3 * * *"
        DESCRIPTION="كل 3 ساعات"
        ;;
    5)
        CRON_SCHEDULE="0 */6 * * *"
        DESCRIPTION="كل 6 ساعات"
        ;;
    6)
        CRON_SCHEDULE="0 6 * * *"
        DESCRIPTION="يومياً عند 6 صباحاً"
        ;;
    7)
        echo ""
        echo "أدخل جدولة cron مخصصة (مثال: */20 * * * * للتشغيل كل 20 دقيقة):"
        read -p "الجدولة: " CRON_SCHEDULE
        DESCRIPTION="مخصص: $CRON_SCHEDULE"
        ;;
    *)
        echo "❌ اختيار غير صحيح"
        exit 1
        ;;
esac

# بناء أمر cron
CRON_COMMAND="cd $PROJECT_DIR && $PYTHON_PATH $SCRIPT_PATH >> $LOG_DIR/cron.log 2>&1"
CRON_JOB="$CRON_SCHEDULE $CRON_COMMAND"

echo ""
echo "✅ الإعداد المختار:"
echo "   - التكرار: $DESCRIPTION"
echo "   - الأمر: $CRON_COMMAND"
echo ""

# التحقق من الجدولة الحالية
EXISTING_CRON=$(crontab -l 2>/dev/null | grep -F "$SCRIPT_PATH" || true)

if [ -n "$EXISTING_CRON" ]; then
    echo "⚠️  يوجد بالفعل مهمة cron لهذا السكريبت:"
    echo "   $EXISTING_CRON"
    echo ""
    read -p "هل تريد استبدالها؟ (y/n): " replace
    
    if [[ ! $replace =~ ^[Yy]$ ]]; then
        echo "❌ تم الإلغاء"
        exit 0
    fi
    
    # حذف الجدولة القديمة
    crontab -l 2>/dev/null | grep -v -F "$SCRIPT_PATH" | crontab - || true
    echo "✅ تم حذف الجدولة القديمة"
fi

# إضافة المهمة الجديدة
(crontab -l 2>/dev/null || true; echo "# Muscat Airport Flights Auto-Update - $DESCRIPTION"; echo "$CRON_JOB") | crontab -

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                 ✅ تم الإعداد بنجاح!                     ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "📋 تفاصيل المهمة:"
echo "   - التكرار: $DESCRIPTION"
echo "   - السجلات: $LOG_DIR/cron.log"
echo ""
echo "📝 أوامر مفيدة:"
echo ""
echo "   عرض جميع مهام cron:"
echo "   $ crontab -l"
echo ""
echo "   تعديل مهام cron:"
echo "   $ crontab -e"
echo ""
echo "   حذف جميع مهام cron:"
echo "   $ crontab -r"
echo ""
echo "   عرض السجلات:"
echo "   $ tail -f $LOG_DIR/cron.log"
echo ""
echo "   التحقق من تشغيل cron:"
echo "   $ sudo service cron status"
echo ""

# اختبار تشغيل يدوي
echo "💡 نصيحة: جرّب التشغيل اليدوي الآن للتأكد:"
echo "   $ python3 $SCRIPT_PATH"
echo ""
