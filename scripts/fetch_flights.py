#!/usr/bin/env python3
"""
Fetch Muscat Airport live departure flights and generate data/report/flights.json.

Output format is compatible with flight-autocomplete.js:
[
  {"code":"WY 101", "date":"29APR", "destination":"LHR", "stdEtd":"14:15/14:30", "status":"Scheduled", ...}
]
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

SOURCE_URL = os.getenv(
    "FLIGHTS_SOURCE_URL",
    "https://www.muscatairport.co.om/flightstatusframe?type=2",
)
OUT_FILE = Path(os.getenv("FLIGHTS_OUT_FILE", "data/report/flights.json"))
META_FILE = Path(os.getenv("FLIGHTS_META_FILE", "data/report/flights_meta.json"))
TIMEOUT = int(os.getenv("FLIGHTS_TIMEOUT", "30"))

# City/name overrides to IATA where the existing aviation workflow expects codes.
# Add more mappings as needed.
DESTINATION_IATA_MAP = {
    "LON": "LHR",       # requested: London group code -> Heathrow
    "LONDON": "LHR",
    "HEATHROW": "LHR",
    "DUBAI": "DXB",
    "ABU DHABI": "AUH",
    "DOHA": "DOH",
    "JEDDAH": "JED",
    "RIYADH": "RUH",
    "DAMMAM": "DMM",
    "SALALAH": "SLL",
    "MUSCAT": "MCT",
    "ISTANBUL": "IST",
    "CAIRO": "CAI",
    "MUMBAI": "BOM",
    "DELHI": "DEL",
    "KOCHI": "COK",
    "COCHIN": "COK",
    "CALICUT": "CCJ",
    "HYDERABAD": "HYD",
    "BANGALORE": "BLR",
    "CHENNAI": "MAA",
    "KARACHI": "KHI",
    "LAHORE": "LHE",
    "DHAKA": "DAC",
    "KUALA LUMPUR": "KUL",
    "BANGKOK": "BKK",
    "PHUKET": "HKT",
    "MANILA": "MNL",
    "ZANZIBAR": "ZNZ",
    "ZURICH": "ZRH",
    "PARIS": "CDG",
    "MUNICH": "MUC",
    "AMSTERDAM": "AMS",
    "MOSCOW": "DME",
}

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
FLIGHT_RE = re.compile(r"\b[A-Z0-9]{2}\s?\d{2,4}[A-Z]?\b")
DATETIME_RE = re.compile(r"\b\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}\b")
STATUS_WORDS = (
    "Departed", "Boarding", "Gate Open", "Scheduled", "Delayed", "Cancelled",
    "Final Call", "Check-in", "Landed", "Arrived"
)


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_flight_code(value: str) -> str:
    value = normalize_space(value).upper().replace(" ", "")
    m = re.match(r"^([A-Z0-9]{2})(\d{2,4}[A-Z]?)$", value)
    if not m:
        return value
    return f"{m.group(1)} {m.group(2)}"


def date_key_from_dt(dt_text: str) -> str:
    dt = datetime.strptime(dt_text, "%d/%m/%Y %H:%M")
    return f"{dt.day}{MONTHS[dt.month - 1]}"


def time_from_dt(dt_text: str) -> str:
    return datetime.strptime(dt_text, "%d/%m/%Y %H:%M").strftime("%H:%M")


def normalize_destination(dest: str) -> str:
    clean = normalize_space(dest).upper()
    return DESTINATION_IATA_MAP.get(clean, clean)


def split_status(text: str) -> tuple[str, str]:
    for status in sorted(STATUS_WORDS, key=len, reverse=True):
        if text.endswith(status):
            return normalize_space(text[: -len(status)]), status
    return text, ""


def parse_line(line: str) -> dict[str, Any] | None:
    line = normalize_space(line)
    if not line or line.lower() == "flight status":
        return None

    flight_match = FLIGHT_RE.search(line)
    if not flight_match:
        return None

    dts = DATETIME_RE.findall(line)
    if not dts:
        return None

    airline = normalize_space(line[: flight_match.start()])
    flight_code = normalize_flight_code(flight_match.group(0))

    before_first_dt = line[flight_match.end() : line.find(dts[0])]
    destination = normalize_space(before_first_dt)

    after_last_dt = line[line.rfind(dts[-1]) + len(dts[-1]) :]
    _, status = split_status(normalize_space(after_last_dt))

    std = time_from_dt(dts[0])
    etd = time_from_dt(dts[1]) if len(dts) > 1 else ""
    std_etd = f"{std}/{etd}" if etd else std

    return {
        "code": flight_code,
        "date": date_key_from_dt(dts[0]),
        "destination": normalize_destination(destination),
        "destinationName": destination,
        "stdEtd": std_etd,
        "status": status,
        "airline": airline,
        "sourceScheduled": dts[0],
        "sourceEstimated": dts[1] if len(dts) > 1 else "",
    }


def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; live-flights-fetcher/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    res = requests.get(url, headers=headers, timeout=TIMEOUT)
    res.raise_for_status()
    return res.text


def extract_flights(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n")

    # The frame often renders each flight as a mostly single text line after text extraction.
    # Support both line-based parsing and table-row parsing.
    candidates: list[str] = []
    for tr in soup.find_all("tr"):
        row_text = normalize_space(tr.get_text(" "))
        if row_text:
            candidates.append(row_text)
    candidates.extend(normalize_space(x) for x in text.splitlines() if normalize_space(x))

    flights: list[dict[str, Any]] = []
    seen = set()
    for candidate in candidates:
        parsed = parse_line(candidate)
        if not parsed:
            continue
        key = (parsed["code"], parsed["sourceScheduled"])
        if key in seen:
            continue
        seen.add(key)
        flights.append(parsed)

    flights.sort(key=lambda f: (f.get("sourceScheduled", ""), f.get("code", "")))
    return flights


def main() -> int:
    html = fetch_html(SOURCE_URL)
    flights = extract_flights(html)

    if not flights:
        raise RuntimeError("No flights parsed from source; website structure may have changed.")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    META_FILE.parent.mkdir(parents=True, exist_ok=True)

    OUT_FILE.write_text(json.dumps(flights, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    META_FILE.write_text(
        json.dumps(
            {
                "source": SOURCE_URL,
                "updatedAtUtc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "count": len(flights),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(flights)} flights to {OUT_FILE}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
