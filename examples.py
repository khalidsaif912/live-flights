#!/usr/bin/env python3
"""
أمثلة متقدمة لاستخدام بيانات رحلات مطار مسقط
==================================================

مجموعة من الأمثلة العملية لتحليل واستخدام البيانات
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict


# ═══════════════════════════════════════════════════════════════════
# تحميل البيانات
# ═══════════════════════════════════════════════════════════════════

def load_archive():
    """تحميل الأرشيف الكامل"""
    with open("flight_data/archive_flights.json", encoding="utf-8") as f:
        return json.load(f)


def load_live():
    """تحميل الرحلات الحالية"""
    with open("flight_data/live_flights.json", encoding="utf-8") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════
# أمثلة التحليل
# ═══════════════════════════════════════════════════════════════════

def example_1_top_destinations():
    """مثال 1: أكثر 10 وجهات شعبية"""
    print("\n" + "="*60)
    print("مثال 1: أكثر 10 وجهات شعبية")
    print("="*60 + "\n")
    
    flights = load_archive()
    destinations = Counter(f["destination"] for f in flights)
    
    for i, (dest, count) in enumerate(destinations.most_common(10), 1):
        # الحصول على الاسم الكامل
        full_name = next(
            (f["sourceDestination"] for f in flights 
             if f["destination"] == dest and f["sourceDestination"]),
            dest
        )
        percentage = (count / len(flights)) * 100
        print(f"{i:2}. {dest:4} - {full_name:30} | {count:4} رحلة ({percentage:5.1f}%)")


def example_2_airline_market_share():
    """مثال 2: حصة كل شركة طيران من السوق"""
    print("\n" + "="*60)
    print("مثال 2: حصة شركات الطيران من السوق")
    print("="*60 + "\n")
    
    flights = load_archive()
    airlines = Counter(f["airline"] for f in flights if f["airline"])
    total = sum(airlines.values())
    
    print(f"إجمالي الرحلات: {total}\n")
    
    for airline, count in airlines.most_common(5):
        share = (count / total) * 100
        bar = "█" * int(share / 2)
        print(f"{airline:30} | {count:4} رحلة ({share:5.1f}%) {bar}")


def example_3_delay_analysis():
    """مثال 3: تحليل التأخيرات حسب الوجهة"""
    print("\n" + "="*60)
    print("مثال 3: متوسط التأخير لكل وجهة")
    print("="*60 + "\n")
    
    flights = load_archive()
    delays_by_dest = defaultdict(list)
    
    for f in flights:
        if f.get("scheduledAt") and f.get("estimatedAt"):
            try:
                sched = datetime.fromisoformat(f["scheduledAt"].replace("Z", "+00:00"))
                estim = datetime.fromisoformat(f["estimatedAt"].replace("Z", "+00:00"))
                delay = (estim - sched).total_seconds() / 60
                
                # تجاهل الفروقات غير المنطقية
                if abs(delay) < 1440:
                    delays_by_dest[f["destination"]].append(delay)
            except:
                continue
    
    # حساب المتوسط
    avg_delays = {
        dest: sum(delays) / len(delays) 
        for dest, delays in delays_by_dest.items() 
        if len(delays) >= 5  # على الأقل 5 رحلات
    }
    
    # ترتيب حسب التأخير
    sorted_delays = sorted(avg_delays.items(), key=lambda x: x[1], reverse=True)
    
    print("أكثر 10 وجهات تأخيراً:\n")
    for i, (dest, avg) in enumerate(sorted_delays[:10], 1):
        status = "🔴" if avg > 30 else "🟡" if avg > 15 else "🟢"
        print(f"{i:2}. {status} {dest:4} - متوسط التأخير: {avg:+6.1f} دقيقة")


def example_4_peak_hours():
    """مثال 4: أوقات الذروة"""
    print("\n" + "="*60)
    print("مثال 4: توزيع الرحلات حسب الساعة")
    print("="*60 + "\n")
    
    flights = load_archive()
    hours = []
    
    for f in flights:
        if f.get("scheduledAt"):
            try:
                dt = datetime.fromisoformat(f["scheduledAt"].replace("Z", "+00:00"))
                hours.append(dt.hour)
            except:
                continue
    
    hour_counts = Counter(hours)
    max_count = max(hour_counts.values()) if hour_counts else 1
    
    print("أكثر 5 ساعات ازدحاماً:\n")
    for i, (hour, count) in enumerate(hour_counts.most_common(5), 1):
        percentage = (count / len(hours)) * 100
        print(f"{i}. الساعة {hour:02d}:00 - {count} رحلة ({percentage:.1f}%)")


def example_5_flights_to_destination():
    """مثال 5: جميع الرحلات إلى وجهة معينة"""
    print("\n" + "="*60)
    print("مثال 5: الرحلات إلى دبي (DXB)")
    print("="*60 + "\n")
    
    flights = load_archive()
    dubai_flights = [f for f in flights if f["destination"] == "DXB"]
    
    print(f"إجمالي الرحلات إلى دبي: {len(dubai_flights)}\n")
    
    # شركات الطيران المشغلة
    airlines = Counter(f["airline"] for f in dubai_flights if f["airline"])
    print("الناقلات:\n")
    for airline, count in airlines.most_common():
        print(f"  - {airline}: {count} رحلة")


def example_6_recent_updates():
    """مثال 6: الرحلات التي تم تحديثها مؤخراً"""
    print("\n" + "="*60)
    print("مثال 6: آخر 10 رحلات تم تحديثها")
    print("="*60 + "\n")
    
    flights = load_archive()
    
    # ترتيب حسب آخر تحديث
    sorted_flights = sorted(
        flights,
        key=lambda x: x.get("lastUpdated", ""),
        reverse=True
    )
    
    for i, f in enumerate(sorted_flights[:10], 1):
        last_updated = f.get("lastUpdated", "غير معروف")
        try:
            dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except:
            time_str = last_updated
        
        print(f"{i:2}. {f['code']:8} → {f['destination']:4} | "
              f"الحالة: {f.get('status', 'N/A'):15} | "
              f"آخر تحديث: {time_str}")


def example_7_status_distribution():
    """مثال 7: توزيع حالات الرحلات"""
    print("\n" + "="*60)
    print("مثال 7: توزيع الرحلات حسب الحالة")
    print("="*60 + "\n")
    
    flights = load_archive()
    statuses = Counter(f["status"] for f in flights if f["status"])
    
    for status, count in statuses.most_common():
        percentage = (count / len(flights)) * 100
        print(f"{status:20} | {count:5} رحلة ({percentage:5.1f}%)")


def example_8_export_to_csv():
    """مثال 8: تصدير بيانات مخصصة إلى CSV"""
    print("\n" + "="*60)
    print("مثال 8: تصدير الرحلات المتأخرة إلى CSV")
    print("="*60 + "\n")
    
    flights = load_archive()
    delayed_flights = []
    
    for f in flights:
        if f.get("scheduledAt") and f.get("estimatedAt"):
            try:
                sched = datetime.fromisoformat(f["scheduledAt"].replace("Z", "+00:00"))
                estim = datetime.fromisoformat(f["estimatedAt"].replace("Z", "+00:00"))
                delay = (estim - sched).total_seconds() / 60
                
                if delay > 15:  # أكثر من 15 دقيقة تأخير
                    delayed_flights.append({
                        "code": f["code"],
                        "destination": f["destination"],
                        "airline": f.get("airline", ""),
                        "scheduled": sched.strftime("%Y-%m-%d %H:%M"),
                        "estimated": estim.strftime("%Y-%m-%d %H:%M"),
                        "delay_minutes": int(delay),
                        "status": f.get("status", "")
                    })
            except:
                continue
    
    # حفظ CSV
    import csv
    output_path = Path("flight_data/delayed_flights.csv")
    
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        if delayed_flights:
            writer = csv.DictWriter(f, fieldnames=delayed_flights[0].keys())
            writer.writeheader()
            writer.writerows(delayed_flights)
    
    print(f"✅ تم تصدير {len(delayed_flights)} رحلة متأخرة إلى:")
    print(f"   {output_path}")


def example_9_daily_report():
    """مثال 9: تقرير يومي"""
    print("\n" + "="*60)
    print("مثال 9: تقرير الرحلات اليوم")
    print("="*60 + "\n")
    
    flights = load_live()
    
    if not flights:
        print("⚠️  لا توجد رحلات حالية")
        return
    
    today = datetime.now().strftime("%d%b").upper()
    today_flights = [f for f in flights if f.get("date", "").upper() == today]
    
    print(f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"📊 عدد الرحلات: {len(today_flights)}\n")
    
    if today_flights:
        # حسب الحالة
        statuses = Counter(f.get("status", "Unknown") for f in today_flights)
        print("الحالات:")
        for status, count in statuses.items():
            print(f"  - {status}: {count}")
        
        print("\nالوجهات الأكثر:")
        destinations = Counter(f["destination"] for f in today_flights)
        for dest, count in destinations.most_common(5):
            print(f"  - {dest}: {count}")


def example_10_time_series_analysis():
    """مثال 10: تحليل السلاسل الزمنية"""
    print("\n" + "="*60)
    print("مثال 10: عدد الرحلات اليومية (آخر 7 أيام)")
    print("="*60 + "\n")
    
    flights = load_archive()
    daily_counts = defaultdict(int)
    
    for f in flights:
        if f.get("scheduledAt"):
            try:
                dt = datetime.fromisoformat(f["scheduledAt"].replace("Z", "+00:00"))
                date_key = dt.strftime("%Y-%m-%d")
                daily_counts[date_key] += 1
            except:
                continue
    
    # آخر 7 أيام
    sorted_dates = sorted(daily_counts.keys(), reverse=True)[:7]
    sorted_dates.reverse()
    
    max_count = max(daily_counts[d] for d in sorted_dates) if sorted_dates else 1
    
    for date in sorted_dates:
        count = daily_counts[date]
        bar = "█" * int((count / max_count) * 40)
        print(f"{date} | {count:3} رحلة {bar}")


# ═══════════════════════════════════════════════════════════════════
# تشغيل جميع الأمثلة
# ═══════════════════════════════════════════════════════════════════

def main():
    """تشغيل جميع الأمثلة"""
    
    print("\n" + "╔" + "="*70 + "╗")
    print("║" + " "*70 + "║")
    print("║" + "  أمثلة متقدمة لتحليل بيانات رحلات مطار مسقط".center(70) + "║")
    print("║" + " "*70 + "║")
    print("╚" + "="*70 + "╝")
    
    # التحقق من وجود البيانات
    archive_path = Path("flight_data/archive_flights.json")
    if not archive_path.exists():
        print("\n❌ خطأ: ملف الأرشيف غير موجود")
        print("   قم بتشغيل flight_manager.py أولاً")
        return
    
    examples = [
        example_1_top_destinations,
        example_2_airline_market_share,
        example_3_delay_analysis,
        example_4_peak_hours,
        example_5_flights_to_destination,
        example_6_recent_updates,
        example_7_status_distribution,
        example_8_export_to_csv,
        example_9_daily_report,
        example_10_time_series_analysis,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n❌ خطأ في {example.__name__}: {e}")
    
    print("\n" + "="*70)
    print("✨ انتهت الأمثلة")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
