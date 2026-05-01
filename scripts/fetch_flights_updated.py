#!/usr/bin/env python3
"""
Fetch Muscat Airport live departures and publish them as JSON files.

Strategies used to bypass Cloudflare / IP blocks (in order):
  1. cloudscraper  – solves JS challenges automatically
  2. requests with full browser fingerprint + cookie warm-up
  3. requests-html with a headless Chromium render (playwright backend)
  4. Fallback: keep existing flights.json and mark status in metadata

Output format matches flight-autocomplete.js expectations:
[
  {
    "code": "WY101",
    "date": "29APR",
    "destination": "LHR",
    "stdEtd": "1415/1430",
    "status": "Scheduled",
    "airline": "Oman Air",
    "sourceDestination": "London"
  }
]

Requirements (install once):
    pip install requests beautifulsoup4 cloudscraper
    # Optional but greatly improves bypass success:
    pip install playwright && playwright install chromium
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

BASE_URL = os.getenv("BASE_URL", "https://www.muscatairport.co.om")
SOURCE_URL = os.getenv(
    "SOURCE_URL",
    "https://www.muscatairport.co.om/flightstatusframe?type=2",
)
# Daily file: overwritten on every successful run with departures from Muscat in the next 24 hours.
DAILY_OUTPUT_PATH = Path(os.getenv("DAILY_OUTPUT_PATH", os.getenv("OUTPUT_PATH", "data/report/flights.json")))

# Archive file: never deletes old flights. New fetches are merged into this file.
# Existing flights are updated when the same flight is fetched again.
ALL_OUTPUT_PATH = Path(os.getenv("ALL_OUTPUT_PATH", "data/report/flights_all.json"))

META_PATH = Path(os.getenv("META_PATH", "data/report/meta.json"))
LOCAL_TZ = ZoneInfo(os.getenv("LOCAL_TZ", "Asia/Muscat"))

# How many seconds to wait between retries
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "3"))

MONTHS = {m: m for m in ("JAN","FEB","MAR","APR","MAY","JUN",
                          "JUL","AUG","SEP","OCT","NOV","DEC")}

DESTINATION_ALIASES = {
    "LON": "LHR",
    "LONDON": "LHR",
    "LONDON HEATHROW": "LHR",
    "HEATHROW": "LHR",
}

# ──────────────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Flight:
    code: str
    date: str
    destination: str
    stdEtd: str
    status: str = ""
    airline: str = ""
    sourceDestination: str = ""
    scheduledAt: str = ""
    estimatedAt: str = ""

# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def local_now() -> datetime:
    return datetime.now(LOCAL_TZ).replace(microsecond=0)


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_flight_code(value: str) -> str:
    return re.sub(r"\s+", "", normalize_space(value).upper())


def normalize_time(value: str) -> str:
    s = normalize_space(value)
    if not s:
        return ""
    m = re.search(r"\b(\d{1,2})[:.](\d{2})\b", s)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return f"{hh:02d}{mm:02d}"
    digits = re.sub(r"\D", "", s)
    if 3 <= len(digits) <= 4:
        digits = digits.zfill(4)
        hh, mm = int(digits[:2]), int(digits[2:4])
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return f"{hh:02d}{mm:02d}"
    return ""


def date_key_from_datetime(dt: datetime | None = None) -> str:
    dt = dt or datetime.now()
    return f"{dt.day}{dt.strftime('%b').upper()}"


def normalize_date_key(value: str) -> str:
    s = normalize_space(value).upper()
    if not s:
        return date_key_from_datetime()
    m = re.search(r"\b(\d{1,2})\s*[-/]?\s*([A-Z]{3})\s*(?:[-/]?\s*\d{2,4})?\b", s)
    if m and m.group(2) in MONTHS:
        return f"{int(m.group(1))}{m.group(2)}"
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", s)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return f"{dt.day}{dt.strftime('%b').upper()}"
        except ValueError:
            pass
    return date_key_from_datetime()


def normalize_destination(value: str) -> tuple[str, str]:
    raw = normalize_space(value)
    upper = raw.upper()
    if upper in DESTINATION_ALIASES:
        return DESTINATION_ALIASES[upper], raw
    m = re.search(r"\(([A-Z]{3})\)", upper)
    if m:
        code = DESTINATION_ALIASES.get(m.group(1), m.group(1))
        return code, raw
    if re.fullmatch(r"[A-Z]{3}", upper):
        return DESTINATION_ALIASES.get(upper, upper), raw
    return DESTINATION_ALIASES.get(upper, raw), raw


def build_std_etd(scheduled: str, estimated: str) -> str:
    std = normalize_time(scheduled)
    etd = normalize_time(estimated)
    if std and etd:
        return f"{std}/{etd}"
    return std or etd or ""


def parse_airport_datetime(value: str) -> datetime | None:
    """Parse Muscat Airport date/time text and return an Asia/Muscat aware datetime."""
    s = normalize_space(value)
    if not s:
        return None

    patterns = [
        r"\b(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})\b",
        r"\b(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{2})\b",
        r"\b(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})\b",
    ]

    for pattern in patterns:
        m = re.search(pattern, s)
        if not m:
            continue
        try:
            if pattern.startswith(r"\b(\d{4})"):
                year, month, day, hour, minute = map(int, m.groups())
            else:
                day, month, year, hour, minute = map(int, m.groups())
            return datetime(year, month, day, hour, minute, tzinfo=LOCAL_TZ)
        except ValueError:
            return None

    return None


def iso_or_empty(dt: datetime | None) -> str:
    return dt.isoformat() if dt else ""


def flight_identity(flight: dict[str, Any]) -> str:
    """
    Stable key for archive merging.
    Do not include stdEtd because ETD can change and should update the existing item.
    """
    scheduled = normalize_space(flight.get("scheduledAt"))
    return "|".join([
        normalize_flight_code(str(flight.get("code", ""))),
        normalize_date_key(str(flight.get("date", ""))),
        normalize_space(flight.get("destination", "")).upper(),
        scheduled,
    ])


def filter_next_24_hours(flights: list[Flight], now: datetime | None = None) -> list[Flight]:
    """Keep only flights departing from now through the next 24 hours."""
    now = now or local_now()
    end = now + timedelta(hours=24)
    out: list[Flight] = []
    for flight in flights:
        scheduled = None
        if flight.scheduledAt:
            try:
                scheduled = datetime.fromisoformat(flight.scheduledAt)
            except ValueError:
                scheduled = None
        if scheduled is None:
            # If the source did not provide a full timestamp, keep it rather than losing data.
            out.append(flight)
        elif now <= scheduled <= end:
            out.append(flight)
    return out


def merge_archive(existing: list[dict[str, Any]], latest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Add new flights to the archive and update existing flights with refreshed timings/status.
    Flights that disappear from the latest fetch are kept unchanged.
    """
    fetched_at = now_iso()
    merged: dict[str, dict[str, Any]] = {}

    for item in existing:
        if not isinstance(item, dict):
            continue
        key = flight_identity(item)
        if not key.strip("|"):
            continue
        merged[key] = item

    for item in latest:
        key = flight_identity(item)
        if not key.strip("|"):
            continue
        if key in merged:
            first_seen = merged[key].get("firstSeenAt") or fetched_at
            merged[key].update(item)
            merged[key]["firstSeenAt"] = first_seen
            merged[key]["lastSeenAt"] = fetched_at
            merged[key]["isStillInLatestFetch"] = True
        else:
            new_item = dict(item)
            new_item["firstSeenAt"] = fetched_at
            new_item["lastSeenAt"] = fetched_at
            new_item["isStillInLatestFetch"] = True
            merged[key] = new_item

    latest_keys = {flight_identity(item) for item in latest}
    for key, item in merged.items():
        if key not in latest_keys:
            item["isStillInLatestFetch"] = False

    return sorted(
        merged.values(),
        key=lambda x: (
            normalize_space(x.get("scheduledAt")) or normalize_space(x.get("date")),
            normalize_space(x.get("stdEtd")),
            normalize_space(x.get("code")),
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Browser-like headers  (rotated slightly on each call)
# ──────────────────────────────────────────────────────────────────────────────

_UA_POOL = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
]


def _browser_headers(ua: str | None = None) -> dict[str, str]:
    ua = ua or random.choice(_UA_POOL)
    return {
        "User-Agent": ua,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.7"
        ),
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "sec-ch-ua": (
            '"Chromium";v="124", "Google Chrome";v="124", '
            '"Not-A.Brand";v="99"'
        ),
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Fetch strategies  (tried in order)
# ──────────────────────────────────────────────────────────────────────────────

def _fetch_via_cloudscraper(url: str) -> str:
    """
    cloudscraper solves Cloudflare JS / IUAM challenges automatically.
    Install: pip install cloudscraper
    """
    import cloudscraper  # noqa: PLC0415
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    # Warm up with homepage first (picks up CF cookies)
    scraper.get(BASE_URL + "/", timeout=30)
    time.sleep(random.uniform(1.5, 3.0))
    response = scraper.get(
        url,
        headers={"Referer": BASE_URL + "/en/flight-status?type=2"},
        timeout=30,
    )
    response.raise_for_status()
    logger.info("cloudscraper: HTTP %s", response.status_code)
    return response.text


def _fetch_via_requests(url: str) -> str:
    """
    Plain requests with full browser fingerprint + homepage warm-up.
    Works when there's no JS challenge, just IP-based rate limiting.
    """
    session = requests.Session()
    headers = _browser_headers()
    session.headers.update(headers)

    # Homepage warm-up to collect cookies
    try:
        session.get(BASE_URL + "/", timeout=30)
        time.sleep(random.uniform(1.0, 2.5))
    except Exception:
        pass

    response = session.get(
        url,
        headers={"Referer": BASE_URL + "/en/flight-status?type=2"},
        timeout=30,
    )
    response.raise_for_status()
    logger.info("requests: HTTP %s", response.status_code)
    return response.text


def _fetch_via_playwright(url: str) -> str:
    """
    Full headless Chromium render via Playwright.
    This is the most reliable bypass — it runs real JavaScript.
    Install: pip install playwright && playwright install chromium
    """
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        ctx = browser.new_context(
            user_agent=random.choice(_UA_POOL),
            locale="ar-OM",
            timezone_id="Asia/Muscat",
            viewport={"width": 1366, "height": 768},
        )
        # Mask navigator.webdriver
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = ctx.new_page()

        # Warm-up: load homepage first
        page.goto(BASE_URL + "/", wait_until="domcontentloaded", timeout=40_000)
        time.sleep(random.uniform(1.5, 3.0))

        # Navigate to flight status
        page.goto(url, wait_until="networkidle", timeout=60_000)
        time.sleep(random.uniform(1.0, 2.0))

        content = page.content()
        browser.close()
        logger.info("playwright: page loaded (%d bytes)", len(content))
        return content


# Ordered list of fetch strategies to try
_STRATEGIES = [
    ("cloudscraper", _fetch_via_cloudscraper),
    ("requests",     _fetch_via_requests),
    ("playwright",   _fetch_via_playwright),
]


def request_live_html(url: str) -> str:
    """
    Try each fetch strategy in sequence.
    Raises the last exception if all strategies fail.
    """
    last_exc: Exception | None = None
    for name, strategy in _STRATEGIES:
        try:
            logger.info("Trying strategy: %s …", name)
            html = strategy(url)
            if html and len(html) > 500:
                logger.info("Strategy '%s' succeeded (%d bytes).", name, len(html))
                return html
            logger.warning("Strategy '%s' returned suspiciously short content.", name)
        except ImportError as exc:
            logger.debug("Strategy '%s' skipped (not installed): %s", name, exc)
            last_exc = exc
        except Exception as exc:
            logger.warning("Strategy '%s' failed: %s", name, exc)
            last_exc = exc
            time.sleep(RETRY_DELAY)

    raise RuntimeError(
        f"All fetch strategies failed. Last error: {last_exc}"
    ) from last_exc


# ──────────────────────────────────────────────────────────────────────────────
# HTML / JSON parsers
# ──────────────────────────────────────────────────────────────────────────────

def table_headers(table) -> list[str]:
    headers = [
        normalize_space(th.get_text(" ")).lower()
        for th in table.select("thead th")
    ]
    if headers:
        return headers
    first_row = table.select_one("tr")
    if not first_row:
        return []
    return [
        normalize_space(c.get_text(" ")).lower()
        for c in first_row.find_all(["th", "td"])
    ]


def cell_texts(row) -> list[str]:
    return [normalize_space(c.get_text(" ")) for c in row.find_all(["td", "th"])]


def index_by_keywords(headers: list[str], keywords: Iterable[str]) -> int | None:
    keywords = [k.lower() for k in keywords]
    for i, h in enumerate(headers):
        if any(k in h for k in keywords):
            return i
    return None


def parse_table_flights(html: str) -> list[Flight]:
    """
    Parser مخصص لموقع مطار مسقط.
    الجدول بدون thead - الاعمدة بترتيب ثابت:
      0=airline, 1=destination, 2=flight code,
      3=scheduled datetime, 4=estimated datetime,
      5=social buttons (يتجاهل), 6=status
    """
    soup = BeautifulSoup(html, "html.parser")
    flights: list[Flight] = []

    table = soup.find("table")
    if not table:
        return []

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 7:
            continue

        airline     = normalize_space(cells[0].get_text(" "))
        dest_raw    = normalize_space(cells[1].get_text(" "))
        flight_code = normalize_flight_code(cells[2].get_text(" "))
        sched_raw   = normalize_space(cells[3].get_text(" "))
        est_raw     = normalize_space(cells[4].get_text(" "))
        status      = normalize_space(cells[6].get_text(" "))

        if not re.match(r"^[A-Z0-9]{2,3}\d{1,5}[A-Z]?$", flight_code):
            continue

        date_key = date_key_from_datetime()
        dm = re.search(r"(\d{1,2})/(\d{2})/(\d{4})", sched_raw)
        if dm:
            try:
                dt = datetime(int(dm.group(3)), int(dm.group(2)), int(dm.group(1)))
                date_key = f"{dt.day}{dt.strftime('%b').upper()}"
            except ValueError:
                pass

        def extract_time(s: str) -> str:
            t = re.search(r"\b(\d{1,2}):(\d{2})\b", s)
            if t:
                return f"{int(t.group(1)):02d}{int(t.group(2)):02d}"
            return ""

        dest, source_dest = normalize_destination(dest_raw)
        scheduled_dt = parse_airport_datetime(sched_raw)
        estimated_dt = parse_airport_datetime(est_raw)

        flights.append(Flight(
            code=flight_code,
            date=date_key,
            destination=dest,
            stdEtd=build_std_etd(extract_time(sched_raw), extract_time(est_raw)),
            status=status,
            airline=airline,
            sourceDestination=source_dest,
            scheduledAt=iso_or_empty(scheduled_dt),
            estimatedAt=iso_or_empty(estimated_dt),
        ))

    return dedupe_flights(flights)


def parse_json_like_flights(html: str) -> list[Flight]:
    """Backup: extract embedded JS arrays/objects containing flight data."""
    flights: list[Flight] = []
    for match in re.finditer(r"\{[^{}]*(?:flight|Flight|flightNo|FlightNo)[^{}]*\}", html):
        chunk = match.group(0)
        try:
            obj = json.loads(chunk)
        except Exception:
            continue
        flight_code = normalize_flight_code(
            obj.get("flight") or obj.get("flightNo") or
            obj.get("Flight") or obj.get("FlightNo") or
            obj.get("flightNumber") or ""
        )
        if not flight_code:
            continue
        dest_value = (
            obj.get("to") or obj.get("destination") or
            obj.get("Destination") or obj.get("airport") or ""
        )
        dest, source_dest = normalize_destination(dest_value)
        scheduled = str(obj.get("scheduled") or obj.get("std") or obj.get("Scheduled") or "")
        estimated = str(obj.get("estimated") or obj.get("etd") or obj.get("Estimated") or "")
        scheduled_dt = parse_airport_datetime(scheduled)
        estimated_dt = parse_airport_datetime(estimated)
        flights.append(Flight(
            code=flight_code,
            date=normalize_date_key(str(obj.get("date") or obj.get("Date") or "")),
            destination=dest,
            stdEtd=build_std_etd(scheduled, estimated),
            status=normalize_space(obj.get("status") or obj.get("Status") or ""),
            airline=normalize_space(obj.get("airline") or obj.get("Airline") or ""),
            sourceDestination=source_dest,
            scheduledAt=iso_or_empty(scheduled_dt),
            estimatedAt=iso_or_empty(estimated_dt),
        ))
    return dedupe_flights(flights)


def parse_flights(html: str) -> list[Flight]:
    flights = parse_table_flights(html)
    return flights if flights else parse_json_like_flights(html)


def dedupe_flights(flights: list[Flight]) -> list[Flight]:
    seen: set[tuple] = set()
    out: list[Flight] = []
    for f in flights:
        key = (f.code, f.date, f.destination, f.stdEtd)
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# I/O helpers
# ──────────────────────────────────────────────────────────────────────────────

def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def read_existing_flights(path: Path = DAILY_OUTPUT_PATH) -> list[dict[str, Any]]:
    return read_json_list(path)


def write_meta(status: str, message: str, count: int, source_url: str = SOURCE_URL) -> None:
    write_json(META_PATH, {
        "status": status,
        "message": message,
        "count": count,
        "sourceUrl": source_url,
        "updatedAt": now_iso(),
    })


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> int:
    try:
        html = request_live_html(SOURCE_URL)
        flights = parse_flights(html)

        if not flights:
            existing_daily = read_existing_flights(DAILY_OUTPUT_PATH)
            existing_all = read_existing_flights(ALL_OUTPUT_PATH)
            write_meta(
                status="fallback_existing",
                message="Live source reachable but no flights parsed. Kept existing JSON files.",
                count=len(existing_daily),
            )
            if not DAILY_OUTPUT_PATH.exists():
                write_json(DAILY_OUTPUT_PATH, [])
            if not ALL_OUTPUT_PATH.exists():
                write_json(ALL_OUTPUT_PATH, existing_all)
            logger.warning("No flights parsed. Existing JSON files kept.")
            return 0

        daily_flights = filter_next_24_hours(flights)
        daily_payload = [asdict(f) for f in daily_flights]
        latest_payload = [asdict(f) for f in flights]

        existing_archive = read_existing_flights(ALL_OUTPUT_PATH)
        archive_payload = merge_archive(existing_archive, latest_payload)

        # Daily file is fully refreshed every run/day.
        write_json(DAILY_OUTPUT_PATH, daily_payload)

        # Archive file is merged: add new, update existing, never delete old.
        write_json(ALL_OUTPUT_PATH, archive_payload)

        write_meta(
            status="live",
            message="Daily 24-hour flights refreshed and all-flights archive merged from live source.",
            count=len(daily_payload),
        )
        logger.info("OK: wrote %d daily flights to %s", len(daily_payload), DAILY_OUTPUT_PATH)
        logger.info("OK: archive now contains %d flights at %s", len(archive_payload), ALL_OUTPUT_PATH)
        return 0

    except Exception as exc:
        existing_daily = read_existing_flights(DAILY_OUTPUT_PATH)
        existing_all = read_existing_flights(ALL_OUTPUT_PATH)

        if existing_daily or existing_all:
            write_meta(
                status="fallback_existing",
                message=f"Live source failed; kept existing JSON files. Error: {exc}",
                count=len(existing_daily),
            )
            logger.warning("Live source failed; kept existing JSON files. Error: %s", exc)
            return 0

        # First run with no existing files
        write_json(DAILY_OUTPUT_PATH, [])
        write_json(ALL_OUTPUT_PATH, [])
        write_meta(
            status="empty_due_to_error",
            message=f"Live source failed and no existing data. Error: {exc}",
            count=0,
        )
        logger.warning("Live source failed and no existing data. Wrote empty JSON files. Error: %s", exc)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
