#!/usr/bin/env python3
"""
سكريبت التشغيل التلقائي لنظام رحلات مطار مسقط
====================================================

يقوم بتشغيل flight_manager.py بشكل دوري
يمكن جدولته باستخدام:
- Linux/Mac: cron
- Windows: Task Scheduler
- Python: schedule library

الاستخدام:
    python auto_update.py --interval 30  # التحديث كل 30 دقيقة
    python auto_update.py --once         # تشغيل مرة واحدة فقط
"""

import sys
import time
import argparse
import logging
import subprocess
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_flight_manager():
    """تشغيل السكريبت الرئيسي"""
    script_path = Path(__file__).parent / "flight_manager.py"
    
    logger.info("=" * 60)
    logger.info("🚀 بدء التحديث...")
    logger.info("=" * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 دقائق كحد أقصى
        )
        
        if result.returncode == 0:
            logger.info("✅ التحديث نجح")
            if result.stdout:
                print(result.stdout)
        else:
            logger.error("❌ التحديث فشل")
            if result.stderr:
                print(result.stderr)
        
        return result.returncode
        
    except subprocess.TimeoutExpired:
        logger.error("⏱️  انتهت مهلة التحديث (أكثر من 5 دقائق)")
        return 1
    except Exception as e:
        logger.error(f"❌ خطأ: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="التحديث التلقائي لرحلات مطار مسقط")
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="فترة التحديث بالدقائق (افتراضي: 30)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="تشغيل مرة واحدة فقط"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="تقليل الرسائل"
    )
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    logger.info(f"⚙️  إعدادات التشغيل:")
    logger.info(f"   - الفترة: {args.interval} دقيقة")
    logger.info(f"   - التشغيل: {'مرة واحدة' if args.once else 'مستمر'}")
    
    if args.once:
        # تشغيل مرة واحدة
        return run_flight_manager()
    
    # تشغيل مستمر
    logger.info(f"🔄 سيتم التحديث كل {args.interval} دقيقة")
    logger.info("⚠️  اضغط Ctrl+C للإيقاف")
    
    try:
        while True:
            run_flight_manager()
            
            next_run = datetime.now().replace(microsecond=0)
            next_run = next_run.replace(
                minute=(next_run.minute // args.interval + 1) * args.interval % 60,
                second=0
            )
            
            wait_seconds = (next_run - datetime.now()).total_seconds()
            if wait_seconds > 0:
                logger.info(f"⏳ التحديث القادم في {next_run.strftime('%H:%M:%S')}")
                time.sleep(wait_seconds)
            
    except KeyboardInterrupt:
        logger.info("\n👋 تم الإيقاف بواسطة المستخدم")
        return 0


if __name__ == "__main__":
    sys.exit(main())
