# live-flights

Fetches Muscat Airport departure flight status every 30 minutes and writes:

- `data/report/flights.json`
- `data/report/flights_meta.json`

The output is designed for `flight-autocomplete.js`.

## Source

Default source:

```text
https://www.muscatairport.co.om/flightstatusframe?type=2
```

## Manual run

```bash
pip install -r requirements.txt
python scripts/fetch_flights.py
```

## Destination mapping

The script converts destination names/codes to aviation IATA-style codes where needed.
Example:

```text
LON -> LHR
London -> LHR
```

Add more mappings in `DESTINATION_IATA_MAP` inside `scripts/fetch_flights.py`.
