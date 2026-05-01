#!/usr/bin/env python3
"""
fetch_offload.py
================
ينزّل ملف offload_current.html من SharePoint ويحلّله ويحفظ النتيجة
في مجلد منظّم حسب التاريخ والوقت داخل المستودع.

هيكل المجلدات الناتج:
  data/offload/
    2026-05-01/
      offload_0600.json
      offload_0610.json
      offload_0620.json
      ...

كل ملف JSON يحتوي على:
  {
    "flight":      "3T263",
    "date":        "01MAY",
    "destination": "PZU",
    "items": [
      {"awb": "524-00019784", "pcs": 6,  "kgs": 160, "description": "PERSONAL EFFECTS", "reason": ""},
      ...
    ],
    "totals": {"pcs": 88, "kgs": 1316},
    "fetchedAt": "2026-05-01T06:00:00+04:00",
    "sourceUrl":  "https://..."
  }

متطلبات:
  pip install requests beautifulsoup4

متغيرات البيئة (اختيارية):
  OFFLOAD_URL      رابط SharePoint المباشر للملف
  OFFLOAD_OUT_DIR  مسار مجلد الإخراج (افتراضي: data/offload)
  TZ_OFFSET        فرق التوقيت بالساعات عن UTC (افتراضي: 4 لمسقط)
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

# رابط الملف على SharePoint — ضعه كمتغير بيئة أو عدّله مباشرة هنا
OFFLOAD_URL: str = os.getenv(
    "OFFLOAD_URL",
    "https://omanair-my.sharepoint.com/:u:/p/8715_hq/"
    "IQAhl_w3GIpTR5hhL-y1Gb9lAQsmsCwNAzKNDxjqHrlmXq4?e=1kNULO",
)

OUT_DIR = Path(os.getenv("OFFLOAD_OUT_DIR", "data/offload"))

# فرق التوقيت (مسقط = UTC+4)
TZ_OFFSET = int(os.getenv("TZ_OFFSET", "4"))
MUSCAT_TZ = timezone(timedelta(hours=TZ_OFFSET))

# ──────────────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class OffloadItem:
    awb: str
    pcs: int
    kgs: float
    description: str
    reason: str = ""


@dataclass
class OffloadReport:
    flight: str
    date: str
    destination: str
    items: list[OffloadItem] = field(default_factory=list)
    totals: dict[str, Any] = field(default_factory=dict)
    fetchedAt: str = ""
    sourceUrl: str = ""

# ──────────────────────────────────────────────────────────────────────────────
# Download
# ──────────────────────────────────────────────────────────────────────────────

def download_html(url: str) -> str:
    """
    ينزّل الملف من SharePoint.
    SharePoint يحوّل روابط المشاركة إلى redirect — نتبع الـ redirect تلقائياً.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    session = requests.Session()
    session.headers.update(headers)

    response = session.get(url, timeout=60, allow_redirects=True)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    logger.info("Downloaded %d bytes (Content-Type: %s)", len(response.content), content_type)

    # SharePoint قد يرجع الملف مباشرة أو يعرض صفحة تسجيل دخول
    if "text/html" not in content_type and len(response.content) < 500:
        raise RuntimeError(
            f"Unexpected response. Status: {response.status_code}, "
            f"Content-Type: {content_type}. "
            "تأكد أن الرابط عام (Anyone with the link) وليس محمياً بتسجيل دخول."
        )

    return response.text


# ──────────────────────────────────────────────────────────────────────────────
# Parser
# ──────────────────────────────────────────────────────────────────────────────

def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def safe_int(value: str) -> int:
    try:
        return int(re.sub(r"[^\d]", "", value))
    except (ValueError, TypeError):
        return 0


def safe_float(value: str) -> float:
    try:
        return float(re.sub(r"[^\d.]", "", value))
    except (ValueError, TypeError):
        return 0.0


def parse_offload(html: str) -> OffloadReport:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")

    report = OffloadReport(flight="", date="", destination="")

    for row in rows:
        cells = [clean(td.get_text(" ")) for td in row.find_all(["td", "th"])]
        cells = [c for c in cells if c and c != "\xa0" and c.strip()]

        if not cells:
            continue

        # ── صف معلومات الرحلة ──────────────────────────────────────────────
        # ['FLIGHT #', '3T263', 'DATE', '01MAY', 'DESTINATION', 'PZU']
        if "FLIGHT #" in cells or "FLIGHT#" in cells:
            try:
                flight_idx = next(
                    i for i, c in enumerate(cells)
                    if "FLIGHT" in c.upper()
                )
                report.flight      = cells[flight_idx + 1] if flight_idx + 1 < len(cells) else ""
                date_idx           = next(i for i, c in enumerate(cells) if c.upper() == "DATE")
                report.date        = cells[date_idx + 1] if date_idx + 1 < len(cells) else ""
                dest_idx           = next(i for i, c in enumerate(cells) if "DESTINATION" in c.upper())
                report.destination = cells[dest_idx + 1] if dest_idx + 1 < len(cells) else ""
            except (StopIteration, IndexError):
                pass
            continue

        # ── صف العناوين ────────────────────────────────────────────────────
        if cells[0].upper() in ("AWB", "AWB NO", "AWB NUMBER"):
            continue

        # ── صف المجاميع ────────────────────────────────────────────────────
        if cells[0].upper() == "TOTAL":
            pcs = safe_int(cells[1]) if len(cells) > 1 else 0
            kgs = safe_float(cells[2]) if len(cells) > 2 else 0.0
            report.totals = {"pcs": pcs, "kgs": kgs}
            continue

        # ── صف بيانات AWB ──────────────────────────────────────────────────
        # ['524-00019784', '6', '160', 'PERSONAL EFFECTS', 'SPACE']
        awb_pattern = re.match(r"^\d{3}-\d+$", cells[0].strip())
        if awb_pattern:
            awb         = cells[0].strip()
            pcs         = safe_int(cells[1]) if len(cells) > 1 else 0
            kgs         = safe_float(cells[2]) if len(cells) > 2 else 0.0
            description = cells[3] if len(cells) > 3 else ""
            reason      = cells[4] if len(cells) > 4 else ""
            report.items.append(OffloadItem(
                awb=awb, pcs=pcs, kgs=kgs,
                description=description, reason=reason,
            ))
            continue

    return report


# ──────────────────────────────────────────────────────────────────────────────
# Output helpers
# ──────────────────────────────────────────────────────────────────────────────

def now_muscat() -> datetime:
    return datetime.now(MUSCAT_TZ)


def output_path(dt: datetime) -> Path:
    """
    data/offload/2026-05-01/offload_0600.json
    """
    date_folder = dt.strftime("%Y-%m-%d")
    filename    = f"offload_{dt.strftime('%H%M')}.json"
    return OUT_DIR / date_folder / filename


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info("Saved → %s", path)


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> int:
    dt = now_muscat()
    logger.info("Starting offload fetch at %s (MCT)", dt.strftime("%Y-%m-%d %H:%M"))

    try:
        html = download_html(OFFLOAD_URL)
    except Exception as exc:
        logger.error("Download failed: %s", exc)
        return 1

    report = parse_offload(html)

    if not report.flight and not report.items:
        logger.error(
            "Parsing failed — no flight info or items found. "
            "تحقق أن الملف هو نفس تنسيق offload_current.html"
        )
        return 1

    report.fetchedAt = dt.isoformat()
    report.sourceUrl = OFFLOAD_URL

    # إذا لم يُجد التاريخ من الملف نفسه، استخدم تاريخ اليوم
    if not report.date:
        report.date = dt.strftime("%-d%b").upper()  # مثال: 1MAY

    payload = asdict(report)
    path    = output_path(dt)
    write_json(path, payload)

    logger.info(
        "OK: Flight=%s  Date=%s  Dest=%s  Items=%d  Total PCS=%s  Total KGS=%s",
        report.flight,
        report.date,
        report.destination,
        len(report.items),
        report.totals.get("pcs", "?"),
        report.totals.get("kgs", "?"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
