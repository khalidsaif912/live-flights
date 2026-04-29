#!/usr/bin/env python3
"""
Fetch Muscat Airport live departures and publish them as data/report/flights.json.

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
from datetime import datetime, timezone
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
OUTPUT_PATH = Path(os.getenv("OUTPUT_PATH", "data/report/flights.json"))
META_PATH = Path(os.getenv("META_PATH", "data/report/meta.json"))

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

# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
    soup = BeautifulSoup(html, "html.parser")
    flights: list[Flight] = []

    for table in soup.find_all("table"):
        headers = table_headers(table)
        if not headers:
            continue

        idx_airline = index_by_keywords(headers, ["airline"])
        idx_dest    = index_by_keywords(headers, ["to", "destination"])
        idx_flight  = index_by_keywords(headers, ["flight"])
        idx_sched   = index_by_keywords(headers, ["scheduled", "std"])
        idx_est     = index_by_keywords(headers, ["estimated", "etd"])
        idx_status  = index_by_keywords(headers, ["status"])
        idx_date    = index_by_keywords(headers, ["date"])

        if idx_flight is None:
            continue

        rows = table.select("tbody tr") or table.select("tr")[1:]
        for row in rows:
            cells = cell_texts(row)
            if not cells or len(cells) <= idx_flight:
                continue

            flight_code = normalize_flight_code(cells[idx_flight])
            if not re.match(r"^[A-Z0-9]{2,3}\d{1,5}[A-Z]?$", flight_code):
                continue

            dest_raw = cells[idx_dest] if idx_dest is not None and idx_dest < len(cells) else ""
            dest, source_dest = normalize_destination(dest_raw)

            scheduled = cells[idx_sched] if idx_sched is not None and idx_sched < len(cells) else ""
            estimated = cells[idx_est]   if idx_est  is not None and idx_est  < len(cells) else ""
            date_raw  = cells[idx_date]  if idx_date is not None and idx_date < len(cells) else ""
            airline   = cells[idx_airline] if idx_airline is not None and idx_airline < len(cells) else ""
            status    = cells[idx_status]  if idx_status  is not None and idx_status  < len(cells) else ""

            flights.append(Flight(
                code=flight_code,
                date=normalize_date_key(date_raw),
                destination=dest,
                stdEtd=build_std_etd(scheduled, estimated),
                status=status,
                airline=airline,
                sourceDestination=source_dest,
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
        flights.append(Flight(
            code=flight_code,
            date=normalize_date_key(str(obj.get("date") or obj.get("Date") or "")),
            destination=dest,
            stdEtd=build_std_etd(scheduled, estimated),
            status=normalize_space(obj.get("status") or obj.get("Status") or ""),
            airline=normalize_space(obj.get("airline") or obj.get("Airline") or ""),
            sourceDestination=source_dest,
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


def read_existing_flights() -> list[dict[str, Any]]:
    if not OUTPUT_PATH.exists():
        return []
    try:
        data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


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
            existing = read_existing_flights()
            write_meta(
                status="fallback_existing",
                message="Live source reachable but no flights parsed. Kept existing flights.json.",
                count=len(existing),
            )
            if not OUTPUT_PATH.exists():
                write_json(OUTPUT_PATH, [])
            logger.warning("No flights parsed. Existing flights.json kept.")
            return 0

        payload = [asdict(f) for f in flights]
        write_json(OUTPUT_PATH, payload)
        write_meta(
            status="live",
            message="Flights updated from live source.",
            count=len(payload),
        )
        logger.info("OK: wrote %d flights to %s", len(payload), OUTPUT_PATH)
        return 0

    except Exception as exc:
        existing = read_existing_flights()

        if existing:
            write_meta(
                status="fallback_existing",
                message=f"Live source failed; kept existing flights.json. Error: {exc}",
                count=len(existing),
            )
            logger.warning("Live source failed; kept existing flights.json. Error: %s", exc)
            return 0

        # First run with no existing file
        write_json(OUTPUT_PATH, [])
        write_meta(
            status="empty_due_to_error",
            message=f"Live source failed and no existing data. Error: {exc}",
            count=0,
        )
        logger.warning("Live source failed and no existing data. Wrote empty flights.json. Error: %s", exc)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
