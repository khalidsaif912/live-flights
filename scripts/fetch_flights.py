#!/usr/bin/env python3
"""
Fetch Muscat Airport live departures and publish them as data/report/flights.json.

Important:
- Some hosts, including GitHub Actions, may receive 403 Forbidden from muscatairport.co.om.
- This script does NOT crash the workflow when the live source is blocked.
- If live fetch fails, it keeps the existing flights.json and marks status in metadata.
- If no flights.json exists yet, it writes an empty but valid JSON file.

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
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = os.getenv("BASE_URL", "https://www.muscatairport.co.om")
SOURCE_URL = os.getenv(
    "SOURCE_URL",
    "https://www.muscatairport.co.om/flightstatusframe?type=2",
)
OUTPUT_PATH = Path(os.getenv("OUTPUT_PATH", "data/report/flights.json"))
META_PATH = Path(os.getenv("META_PATH", "data/report/meta.json"))

MONTHS = {
    "JAN": "JAN",
    "FEB": "FEB",
    "MAR": "MAR",
    "APR": "APR",
    "MAY": "MAY",
    "JUN": "JUN",
    "JUL": "JUL",
    "AUG": "AUG",
    "SEP": "SEP",
    "OCT": "OCT",
    "NOV": "NOV",
    "DEC": "DEC",
}

# City/metropolitan codes or display names that your system wants converted
# to airport IATA codes.
DESTINATION_ALIASES = {
    "LON": "LHR",
    "LONDON": "LHR",
    "LONDON HEATHROW": "LHR",
    "HEATHROW": "LHR",
}


@dataclass
class Flight:
    code: str
    date: str
    destination: str
    stdEtd: str
    status: str = ""
    airline: str = ""
    sourceDestination: str = ""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_flight_code(value: str) -> str:
    # "WY 101" -> "WY101"
    return re.sub(r"\s+", "", normalize_space(value).upper())


def normalize_time(value: str) -> str:
    """
    Convert common time forms to HHMM.
    Examples:
      "14:05" -> "1405"
      "1405"  -> "1405"
      "9:05"  -> "0905"
    """
    s = normalize_space(value)
    if not s:
        return ""

    m = re.search(r"\b(\d{1,2})[:.](\d{2})\b", s)
    if m:
        hh = int(m.group(1))
        mm = int(m.group(2))
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return f"{hh:02d}{mm:02d}"

    digits = re.sub(r"\D", "", s)
    if 3 <= len(digits) <= 4:
        digits = digits.zfill(4)
        hh = int(digits[:2])
        mm = int(digits[2:4])
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return f"{hh:02d}{mm:02d}"

    return ""


def date_key_from_datetime(dt: datetime | None = None) -> str:
    dt = dt or datetime.now()
    return f"{dt.day}{dt.strftime('%b').upper()}"


def normalize_date_key(value: str) -> str:
    """
    Accepts:
      29APR
      29 APR
      29-Apr-2026
      2026-04-29
    Returns:
      29APR
    """
    s = normalize_space(value).upper()
    if not s:
        return date_key_from_datetime()

    m = re.search(r"\b(\d{1,2})\s*[-/]?\s*([A-Z]{3})\s*(?:[-/]?\s*\d{2,4})?\b", s)
    if m and m.group(2) in MONTHS:
        return f"{int(m.group(1))}{m.group(2)}"

    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            dt = datetime(y, mo, d)
            return f"{dt.day}{dt.strftime('%b').upper()}"
        except ValueError:
            return date_key_from_datetime()

    return date_key_from_datetime()


def normalize_destination(value: str) -> tuple[str, str]:
    raw = normalize_space(value)
    upper = raw.upper()

    # Direct exact aliases.
    if upper in DESTINATION_ALIASES:
        return DESTINATION_ALIASES[upper], raw

    # If destination includes an IATA code in parentheses, prefer it.
    # Example: London (LON), London Heathrow (LHR)
    m = re.search(r"\(([A-Z]{3})\)", upper)
    if m:
        code = DESTINATION_ALIASES.get(m.group(1), m.group(1))
        return code, raw

    # If a three-letter all-caps code appears alone, use it.
    m = re.fullmatch(r"[A-Z]{3}", upper)
    if m:
        code = DESTINATION_ALIASES.get(upper, upper)
        return code, raw

    # Fallback: keep original display name if no code found.
    return DESTINATION_ALIASES.get(upper, raw), raw


def build_std_etd(scheduled: str, estimated: str) -> str:
    std = normalize_time(scheduled)
    etd = normalize_time(estimated)
    if std and etd:
        return f"{std}/{etd}"
    if std:
        return std
    if etd:
        return etd
    return ""


<<<<<<< HEAD
def request_live_html(url: str) -> str:
    """
    Try to look like a normal browser session.

    If the site blocks GitHub Actions IPs, this still may return 403.
    That is expected; main() handles it safely.
    """
=======
def fetch_html(url):
    import requests

>>>>>>> 53c87cecf9ea16a4aa5904cebfdda6ce51741fb3
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
<<<<<<< HEAD
            "Chrome/124.0.0.0 Safari/537.36"
=======
            "Chrome/124.0 Safari/537.36"
>>>>>>> 53c87cecf9ea16a4aa5904cebfdda6ce51741fb3
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Referer": "https://www.muscatairport.co.om/en/flight-status?type=2",
<<<<<<< HEAD
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
=======
>>>>>>> 53c87cecf9ea16a4aa5904cebfdda6ce51741fb3
        "Connection": "keep-alive",
    }

    session = requests.Session()
    session.headers.update(headers)

<<<<<<< HEAD
    # First request helps with cookies on some sites.
    session.get(BASE_URL + "/", timeout=30)

    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text
=======
    # افتح الصفحة الرئيسية أولًا للحصول على cookies
    session.get("https://www.muscatairport.co.om/", timeout=30)

    res = session.get(url, timeout=30)
    res.raise_for_status()
    return res.text
>>>>>>> 53c87cecf9ea16a4aa5904cebfdda6ce51741fb3


def table_headers(table) -> list[str]:
    headers = []
    for th in table.select("thead th"):
        headers.append(normalize_space(th.get_text(" ")).lower())

    if headers:
        return headers

    first_row = table.select_one("tr")
    if not first_row:
        return []

    cells = first_row.find_all(["th", "td"])
    return [normalize_space(c.get_text(" ")).lower() for c in cells]


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
        idx_dest = index_by_keywords(headers, ["to", "destination"])
        idx_flight = index_by_keywords(headers, ["flight"])
        idx_sched = index_by_keywords(headers, ["scheduled", "std"])
        idx_est = index_by_keywords(headers, ["estimated", "etd"])
        idx_status = index_by_keywords(headers, ["status"])
        idx_date = index_by_keywords(headers, ["date"])

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
            estimated = cells[idx_est] if idx_est is not None and idx_est < len(cells) else ""

            date_raw = cells[idx_date] if idx_date is not None and idx_date < len(cells) else ""
            date_key = normalize_date_key(date_raw)

            airline = cells[idx_airline] if idx_airline is not None and idx_airline < len(cells) else ""
            status = cells[idx_status] if idx_status is not None and idx_status < len(cells) else ""

            flights.append(
                Flight(
                    code=flight_code,
                    date=date_key,
                    destination=dest,
                    stdEtd=build_std_etd(scheduled, estimated),
                    status=status,
                    airline=airline,
                    sourceDestination=source_dest,
                )
            )

    return dedupe_flights(flights)


def parse_json_like_flights(html: str) -> list[Flight]:
    """
    Backup parser for pages that embed a JS array/object.
    This is intentionally conservative.
    """
    flights: list[Flight] = []

    # Look for JSON-ish objects containing a flight number.
    for match in re.finditer(r"\{[^{}]*(?:flight|Flight|flightNo|FlightNo)[^{}]*\}", html):
        chunk = match.group(0)
        try:
            obj = json.loads(chunk)
        except Exception:
            continue

        flight_code = normalize_flight_code(
            obj.get("flight")
            or obj.get("flightNo")
            or obj.get("Flight")
            or obj.get("FlightNo")
            or obj.get("flightNumber")
            or ""
        )
        if not flight_code:
            continue

        dest_value = (
            obj.get("to")
            or obj.get("destination")
            or obj.get("Destination")
            or obj.get("airport")
            or ""
        )
        dest, source_dest = normalize_destination(dest_value)

        scheduled = obj.get("scheduled") or obj.get("std") or obj.get("Scheduled") or ""
        estimated = obj.get("estimated") or obj.get("etd") or obj.get("Estimated") or ""

        flights.append(
            Flight(
                code=flight_code,
                date=normalize_date_key(str(obj.get("date") or obj.get("Date") or "")),
                destination=dest,
                stdEtd=build_std_etd(str(scheduled), str(estimated)),
                status=normalize_space(obj.get("status") or obj.get("Status") or ""),
                airline=normalize_space(obj.get("airline") or obj.get("Airline") or ""),
                sourceDestination=source_dest,
            )
        )

    return dedupe_flights(flights)


def parse_flights(html: str) -> list[Flight]:
    flights = parse_table_flights(html)
    if flights:
        return flights
    return parse_json_like_flights(html)


def dedupe_flights(flights: list[Flight]) -> list[Flight]:
    seen = set()
    out = []
    for f in flights:
        key = (f.code, f.date, f.destination, f.stdEtd)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


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
    write_json(
        META_PATH,
        {
            "status": status,
            "message": message,
            "count": count,
            "sourceUrl": source_url,
            "updatedAt": now_iso(),
        },
    )


def main() -> int:
    try:
        html = request_live_html(SOURCE_URL)
        flights = parse_flights(html)

        if not flights:
            existing = read_existing_flights()
            write_meta(
                status="fallback_existing",
                message="Live source was reachable, but no flights were parsed. Kept existing flights.json.",
                count=len(existing),
            )
            if not OUTPUT_PATH.exists():
                write_json(OUTPUT_PATH, [])
            print("WARNING: No flights parsed. Existing flights.json kept.")
            return 0

        payload = [asdict(f) for f in flights]
        write_json(OUTPUT_PATH, payload)
        write_meta(
            status="live",
            message="Flights updated from live source.",
            count=len(payload),
        )
        print(f"OK: wrote {len(payload)} flights to {OUTPUT_PATH}")
        return 0

    except Exception as exc:
        existing = read_existing_flights()

        if existing:
            write_meta(
                status="fallback_existing",
                message=f"Live source failed; kept existing flights.json. Error: {exc}",
                count=len(existing),
            )
            print(f"WARNING: live source failed; kept existing flights.json. Error: {exc}")
            return 0

        # First run with no existing file: write a valid empty file so preview does not break.
        write_json(OUTPUT_PATH, [])
        write_meta(
            status="empty_due_to_error",
            message=f"Live source failed and no existing flights.json was available. Error: {exc}",
            count=0,
        )
        print(f"WARNING: live source failed and no existing data exists. Wrote empty flights.json. Error: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
