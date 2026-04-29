# Live Flights

This repository fetches Muscat Airport departures every 30 minutes and publishes:

```text
data/report/flights.json
data/report/meta.json
```

It also includes a simple preview page:

```text
preview/index.html
```

## Important

If GitHub Actions gets `403 Forbidden` from the Muscat Airport website, the workflow will not fail.
It will keep the existing `flights.json` and update `meta.json` with a fallback status.

This means your app keeps working with the latest saved data instead of breaking.

## Output format

```json
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
```

## City code conversion

The script converts:

```text
LON -> LHR
London -> LHR
London Heathrow -> LHR
```

You can add more aliases in:

```text
scripts/fetch_flights.py
```

Look for:

```python
DESTINATION_ALIASES
```

## GitHub Pages preview

After pushing this repository:

1. Go to repository **Settings**
2. Go to **Pages**
3. Source: **Deploy from a branch**
4. Branch: **main**
5. Folder: **/root**
6. Save

Preview URL will be:

```text
https://khalidsaif912.github.io/live-flights/preview/
```

Raw JSON URL:

```text
https://raw.githubusercontent.com/khalidsaif912/live-flights/main/data/report/flights.json
```

Use it in your app:

```js
window.flightAutocomplete.load(
  "https://raw.githubusercontent.com/khalidsaif912/live-flights/main/data/report/flights.json"
);
```

## Run locally

```bash
pip install -r requirements.txt
python scripts/fetch_flights.py
python -m http.server 8000
```

Open:

```text
http://localhost:8000/preview/
```
