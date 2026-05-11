#!/usr/bin/env python3
"""
تحليل بيانات رحلات مطار مسقط
==============================

يقدم إحصائيات وتحليلات متقدمة عن الرحلات:
- أكثر الوجهات
- أكثر شركات الطيران
- أوقات الذروة
- معدلات التأخير
- الاتجاهات الزمنية

الاستخدام:
    python analyze_flights.py
    python analyze_flights.py --destination LHR
    python analyze_flights.py --airline "Oman Air"
"""

import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import List, Dict, Any

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def load_flights(archive_path: Path = Path("flight_data/archive_flights.json")) -> List[Dict[str, Any]]:
    """تحميل بيانات الرحلات"""
    if not archive_path.exists():
        print(f"❌ الملف غير موجود: {archive_path}")
        print("   قم بتشغيل flight_manager.py أولاً")
        return []
    
    with open(archive_path, encoding="utf-8") as f:
        return json.load(f)


def print_header(title: str):
    """طباعة عنوان منسق"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def analyze_destinations(flights: List[Dict[str, Any]], top_n: int = 10):
    """تحليل الوجهات"""
    print_header("🌍 أكثر الوجهات")
    
    destinations = Counter(f["destination"] for f in flights)
    
    print(f"إجمالي الوجهات المختلفة: {len(destinations)}\n")
    print(f"أكثر {top_n} وجهات:\n")
    
    for i, (dest, count) in enumerate(destinations.most_common(top_n), 1):
        # محاولة الحصول على الاسم الكامل
        dest_full = next(
            (f["sourceDestination"] for f in flights 
             if f["destination"] == dest and f["sourceDestination"]),
            dest
        )
        
        percentage = (count / len(flights)) * 100
        bar = "█" * int(percentage / 2)
        
        print(f"{i:2}. {dest:4} - {dest_full:30} | {count:4} رحلة ({percentage:5.1f}%) {bar}")


def analyze_airlines(flights: List[Dict[str, Any]], top_n: int = 10):
    """تحليل شركات الطيران"""
    print_header("✈️  شركات الطيران")
    
    airlines = Counter(f["airline"] for f in flights if f["airline"])
    
    print(f"إجمالي شركات الطيران: {len(airlines)}\n")
    print(f"أكثر {top_n} شركات:\n")
    
    for i, (airline, count) in enumerate(airlines.most_common(top_n), 1):
        percentage = (count / len(flights)) * 100
        bar = "█" * int(percentage / 2)
        
        print(f"{i:2}. {airline:30} | {count:4} رحلة ({percentage:5.1f}%) {bar}")


def analyze_flight_status(flights: List[Dict[str, Any]]):
    """تحليل حالات الرحلات"""
    print_header("📊 حالات الرحلات")
    
    statuses = Counter(f["status"] for f in flights if f["status"])
    
    print(f"إجمالي الحالات المختلفة: {len(statuses)}\n")
    
    for status, count in statuses.most_common():
        percentage = (count / len(flights)) * 100
        bar = "█" * int(percentage / 2)
        
        print(f"  {status:20} | {count:4} رحلة ({percentage:5.1f}%) {bar}")


def analyze_delays(flights: List[Dict[str, Any]]):
    """تحليل التأخيرات"""
    print_header("⏱️  تحليل التأخيرات")
    
    delays = []
    delays_by_dest = defaultdict(list)
    delays_by_airline = defaultdict(list)
    
    for f in flights:
        if f.get("scheduledAt") and f.get("estimatedAt"):
            try:
                sched = datetime.fromisoformat(f["scheduledAt"].replace("Z", "+00:00"))
                estim = datetime.fromisoformat(f["estimatedAt"].replace("Z", "+00:00"))
                
                delay_minutes = (estim - sched).total_seconds() / 60
                
                if abs(delay_minutes) < 1440:  # تجاهل الفروقات الكبيرة جداً (أخطاء)
                    delays.append(delay_minutes)
                    delays_by_dest[f["destination"]].append(delay_minutes)
                    if f.get("airline"):
                        delays_by_airline[f["airline"]].append(delay_minutes)
            except:
                continue
    
    if not delays:
        print("⚠️  لا توجد بيانات كافية لحساب التأخيرات")
        return
    
    # إحصائيات عامة
    avg_delay = sum(delays) / len(delays)
    on_time = sum(1 for d in delays if abs(d) <= 15)
    delayed = sum(1 for d in delays if d > 15)
    early = sum(1 for d in delays if d < -15)
    
    print(f"إجمالي الرحلات المحللة: {len(delays)}")
    print(f"متوسط التأخير: {avg_delay:.1f} دقيقة")
    print(f"الحد الأقصى للتأخير: {max(delays):.1f} دقيقة")
    print(f"الحد الأدنى للتأخير: {min(delays):.1f} دقيقة")
    print()
    print(f"في الوقت المحدد (±15 دقيقة): {on_time} ({on_time/len(delays)*100:.1f}%)")
    print(f"متأخرة (>15 دقيقة): {delayed} ({delayed/len(delays)*100:.1f}%)")
    print(f"مبكرة (<-15 دقيقة): {early} ({early/len(delays)*100:.1f}%)")
    
    # أكثر الوجهات تأخيراً
    print("\n🔴 أكثر 5 وجهات تأخيراً:\n")
    dest_avg = {dest: sum(delays)/len(delays) for dest, delays in delays_by_dest.items() if len(delays) >= 3}
    for i, (dest, avg) in enumerate(sorted(dest_avg.items(), key=lambda x: x[1], reverse=True)[:5], 1):
        print(f"  {i}. {dest}: {avg:.1f} دقيقة")
    
    # أكثر الشركات تأخيراً
    print("\n🔴 أكثر 5 شركات تأخيراً:\n")
    airline_avg = {airline: sum(delays)/len(delays) for airline, delays in delays_by_airline.items() if len(delays) >= 3}
    for i, (airline, avg) in enumerate(sorted(airline_avg.items(), key=lambda x: x[1], reverse=True)[:5], 1):
        print(f"  {i}. {airline}: {avg:.1f} دقيقة")


def analyze_time_patterns(flights: List[Dict[str, Any]]):
    """تحليل الأنماط الزمنية"""
    print_header("🕐 أنماط الوقت")
    
    hours = []
    
    for f in flights:
        if f.get("scheduledAt"):
            try:
                dt = datetime.fromisoformat(f["scheduledAt"].replace("Z", "+00:00"))
                hours.append(dt.hour)
            except:
                continue
    
    if not hours:
        print("⚠️  لا توجد بيانات زمنية كافية")
        return
    
    hour_counts = Counter(hours)
    
    print("توزيع الرحلات حسب الساعة:\n")
    
    max_count = max(hour_counts.values())
    
    for hour in range(24):
        count = hour_counts.get(hour, 0)
        percentage = (count / len(hours)) * 100 if hours else 0
        bar_length = int((count / max_count) * 40) if max_count > 0 else 0
        bar = "█" * bar_length
        
        time_label = f"{hour:02d}:00"
        print(f"  {time_label} | {count:3} رحلة ({percentage:4.1f}%) {bar}")
    
    # أوقات الذروة
    print("\n🔥 أوقات الذروة:\n")
    top_hours = hour_counts.most_common(5)
    for i, (hour, count) in enumerate(top_hours, 1):
        print(f"  {i}. {hour:02d}:00 - {count} رحلة")


def analyze_by_filter(flights: List[Dict[str, Any]], destination: str = None, airline: str = None):
    """تحليل مفلتر حسب وجهة أو شركة"""
    
    filtered = flights
    
    if destination:
        filtered = [f for f in filtered if f["destination"].upper() == destination.upper()]
        print_header(f"🎯 تحليل الرحلات إلى {destination}")
    
    if airline:
        filtered = [f for f in filtered if airline.lower() in f.get("airline", "").lower()]
        print_header(f"🎯 تحليل رحلات {airline}")
    
    if not filtered:
        print(f"❌ لا توجد رحلات مطابقة")
        return
    
    print(f"إجمالي الرحلات: {len(filtered)}\n")
    
    # الإحصائيات
    if destination:
        analyze_airlines(filtered, top_n=5)
    
    if airline:
        analyze_destinations(filtered, top_n=5)
    
    analyze_flight_status(filtered)
    analyze_delays(filtered)


def export_to_csv(flights: List[Dict[str, Any]], output_path: Path = Path("flight_data/analysis.csv")):
    """تصدير التحليل إلى CSV"""
    if not HAS_PANDAS:
        print("⚠️  pandas غير متوفر - لا يمكن التصدير إلى CSV")
        return
    
    df = pd.DataFrame(flights)
    
    # إضافة أعمدة محسوبة
    if "scheduledAt" in df.columns and "estimatedAt" in df.columns:
        df["scheduledAt_dt"] = pd.to_datetime(df["scheduledAt"], errors="coerce")
        df["estimatedAt_dt"] = pd.to_datetime(df["estimatedAt"], errors="coerce")
        df["delay_minutes"] = (df["estimatedAt_dt"] - df["scheduledAt_dt"]).dt.total_seconds() / 60
    
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ تم التصدير إلى: {output_path}")


def generate_summary_report(flights: List[Dict[str, Any]]):
    """إنشاء تقرير ملخص"""
    print_header("📈 تقرير ملخص شامل")
    
    print(f"إجمالي الرحلات في الأرشيف: {len(flights)}")
    
    # نطاق التواريخ
    dates = []
    for f in flights:
        if f.get("scheduledAt"):
            try:
                dt = datetime.fromisoformat(f["scheduledAt"].replace("Z", "+00:00"))
                dates.append(dt)
            except:
                continue
    
    if dates:
        earliest = min(dates)
        latest = max(dates)
        print(f"نطاق البيانات: من {earliest.strftime('%Y-%m-%d')} إلى {latest.strftime('%Y-%m-%d')}")
        print(f"المدة: {(latest - earliest).days} يوم")
    
    print(f"\nعدد الوجهات المختلفة: {len(set(f['destination'] for f in flights))}")
    print(f"عدد شركات الطيران: {len(set(f['airline'] for f in flights if f.get('airline')))}")
    
    # متوسط الرحلات يومياً
    if dates and len(dates) > 1:
        days = (latest - earliest).days + 1
        avg_per_day = len(flights) / days
        print(f"متوسط الرحلات اليومية: {avg_per_day:.1f}")


def main():
    parser = argparse.ArgumentParser(description="تحليل بيانات رحلات مطار مسقط")
    parser.add_argument("--destination", "-d", help="فلترة حسب الوجهة (مثل: LHR, DXB)")
    parser.add_argument("--airline", "-a", help="فلترة حسب شركة الطيران")
    parser.add_argument("--export-csv", action="store_true", help="تصدير إلى CSV")
    parser.add_argument("--summary-only", action="store_true", help="عرض الملخص فقط")
    
    args = parser.parse_args()
    
    # تحميل البيانات
    flights = load_flights()
    
    if not flights:
        return 1
    
    print(f"\n✅ تم تحميل {len(flights)} رحلة من الأرشيف\n")
    
    # تقرير ملخص
    generate_summary_report(flights)
    
    if args.summary_only:
        return 0
    
    # فلترة إذا طُلب ذلك
    if args.destination or args.airline:
        analyze_by_filter(flights, args.destination, args.airline)
    else:
        # تحليل شامل
        analyze_destinations(flights)
        analyze_airlines(flights)
        analyze_flight_status(flights)
        analyze_delays(flights)
        analyze_time_patterns(flights)
    
    # تصدير CSV
    if args.export_csv:
        print_header("📤 تصدير البيانات")
        export_to_csv(flights)
    
    print("\n" + "=" * 70)
    print("  ✨ اكتمل التحليل")
    print("=" * 70 + "\n")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
