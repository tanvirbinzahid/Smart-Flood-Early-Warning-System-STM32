#!/usr/bin/env python3
"""
Fetch USGS water level data for cross-country validation.
Used in Section 8.3 (Cross-country validation using USGS data).

Stations:
  07374000 - Mississippi River at Baton Rouge, LA (2011 flood)
  08068500 - Spring Creek near Spring, TX (Hurricane Harvey 2017)
  06934500 - Missouri River at Hermann, MO (Midwest 2019)

API: USGS NWIS Instantaneous Values
     https://api.waterdata.usgs.gov/nwis/iv/
     Free, anonymous, no registration required.

Output: CSV files saved to datasets/usgs/
"""
import urllib.request, csv, os, json, sys

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets", "usgs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

STATIONS = [
    {
        "id": "07374000",
        "name": "Mississippi_River_2011",
        "location": "Baton Rouge, LA",
        "start": "2011-04-01",
        "end": "2011-06-30",
    },
    {
        "id": "08068500",
        "name": "Hurricane_Harvey_2017",
        "location": "Spring Creek, Houston, TX",
        "start": "2017-08-24",
        "end": "2017-09-05",
    },
    {
        "id": "06934500",
        "name": "Midwest_Floods_2019",
        "location": "Hermann, MO",
        "start": "2019-03-01",
        "end": "2019-07-31",
    },
]

def fetch_station(site_id, start_date, end_date):
    """Fetch water level (parameter 00065) from USGS NWIS Instantaneous Values API."""
    url = (
        f"https://api.waterdata.usgs.gov/nwis/iv/"
        f"?format=json&sites={site_id}"
        f"&parameterCd=00065"
        f"&startDT={start_date}&endDT={end_date}"
    )
    print(f"  Fetching {site_id}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())

    # Parse time series
    ts = data.get("value", {}).get("timeSeries", [])
    if not ts:
        print(f"  WARNING: No time series for {site_id}")
        return []

    records = []
    for series in ts:
        values = series.get("values", [])
        for val_set in values:
            for v in val_set.get("value", []):
                records.append({
                    "date": v.get("dateTime", ""),
                    "water_level_ft": float(v.get("value", 0)),
                })

    records.sort(key=lambda r: r["date"])
    print(f"  Retrieved {len(records)} records for {site_id}")
    return records


def save_csv(station_name, records):
    """Save records to CSV file."""
    path = os.path.join(OUTPUT_DIR, f"{station_name}.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "water_level_ft"])
        writer.writeheader()
        writer.writerows(records)
    print(f"  Saved to: {path}")
    return path


if __name__ == "__main__":
    print("=" * 60)
    print("USGS Water Level Data Fetch")
    print("=" * 60)

    for station in STATIONS:
        print(f"\nStation: {station['name']} ({station['id']})")
        print(f"  Location: {station['location']}")
        print(f"  Period: {station['start']} to {station['end']}")
        records = fetch_station(station["id"], station["start"], station["end"])
        if records:
            path = save_csv(station["name"], records)
        print()

    print(f"\nAll data saved to: {OUTPUT_DIR}")
