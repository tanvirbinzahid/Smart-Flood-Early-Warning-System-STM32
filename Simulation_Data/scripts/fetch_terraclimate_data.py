#!/usr/bin/env python3
"""
Fetch TerraClimate soil moisture data for cross-country validation.
Used in Section 8.3 (Cross-country validation using USGS data).

Source: Abatzoglou et al. (2018) Scientific Data
Access: Free, no login, via THREDDS OPeNDAP
  http://thredds.northwestknowledge.net:8080/thredds/ncss/grid/
  agg_terraclimate_soil_1950_CurrentYear_GLOBE.nc

Variable: soil (total column soil moisture, mm)
Resolution: 1/24 degree (~4 km), monthly
Normalization: % of 2000-2025 maximum for each station location

Output: CSV with raw soil moisture (mm) and % saturation
"""
import urllib.request, csv, os, sys

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets", "terraclimate")
os.makedirs(OUTPUT_DIR, exist_ok=True)

THREDDS_URL = (
    "http://thredds.northwestknowledge.net:8080/thredds/ncss/grid/"
    "agg_terraclimate_soil_1950_CurrentYear_GLOBE.nc"
)

STATIONS = [
    {
        "id": "07374000",
        "name": "Mississippi_River_Baton_Rouge",
        "lat": 30.4457, "lon": -91.1916,
        "start": "2011-05-01", "end": "2011-06-30",
        "event": "Mississippi 2011 flood",
    },
    {
        "id": "08068500",
        "name": "Harvey_Houston",
        "lat": 30.05, "lon": -95.38,
        "start": "2017-08-01", "end": "2017-09-30",
        "event": "Hurricane Harvey 2017",
    },
    {
        "id": "06934500",
        "name": "Midwest_Hermann",
        "lat": 38.7, "lon": -91.44,
        "start": "2019-03-01", "end": "2019-07-31",
        "event": "Midwest floods 2019",
    },
]


def get_climatology(lat, lon):
    """Fetch 2000-2025 data to compute min/max for normalization."""
    url = (
        f"{THREDDS_URL}?var=soil&latitude={lat}&longitude={lon}"
        f"&time_start=2000-01-01&time_end=2025-12-01&accept=csv"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read().decode()

    values = []
    for line in data.strip().split("\n")[1:]:  # skip header
        if line.strip():
            parts = line.split(",")
            try:
                values.append(float(parts[-1]))
            except (ValueError, IndexError):
                pass
    return min(values), max(values), sum(values) / len(values) if values else 0


def fetch_soil_moisture(lat, lon, start, end):
    """Fetch TerraClimate soil moisture for a point and date range."""
    url = (
        f"{THREDDS_URL}?var=soil&latitude={lat}&longitude={lon}"
        f"&time_start={start}&time_end={end}&accept=csv"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read().decode()

    records = []
    for line in data.strip().split("\n")[1:]:
        if line.strip():
            parts = line.split(",")
            if len(parts) >= 4:
                records.append({
                    "date": parts[0][:10],
                    "latitude": float(parts[1]),
                    "longitude": float(parts[2]),
                    "soil_mm": float(parts[3]),
                })
    return records


def save_csv(station_name, records, min_mm, max_mm, mean_mm):
    """Save with raw values and normalized % saturation."""
    path = os.path.join(OUTPUT_DIR, f"{station_name}_soil_moisture.csv")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "latitude", "longitude",
                         "soil_mm", "pct_saturation",
                         f"climatology_min_mm={min_mm:.0f}",
                         f"climatology_max_mm={max_mm:.0f}",
                         f"climatology_mean_mm={mean_mm:.0f}"])
        for r in records:
            pct = round(r["soil_mm"] / max_mm * 100, 1) if max_mm > 0 else 0
            writer.writerow([r["date"], r["latitude"], r["longitude"],
                             r["soil_mm"], pct])
    print(f"  Saved: {path}")
    return path


if __name__ == "__main__":
    print("=" * 60)
    print("TerraClimate Soil Moisture Data Fetch")
    print("=" * 60)

    for s in STATIONS:
        print(f"\nStation: {s['name']}")
        print(f"  Event: {s['event']}")
        print(f"  Coordinates: {s['lat']}, {s['lon']}")
        print(f"  Period: {s['start']} to {s['end']}")

        # Get climatology
        print("  Fetching climatology (2000-2025)...")
        min_mm, max_mm, mean_mm = get_climatology(s["lat"], s["lon"])
        print(f"  Climate: min={min_mm:.0f}  max={max_mm:.0f}  mean={mean_mm:.0f} mm")

        # Get event data
        print("  Fetching event data...")
        records = fetch_soil_moisture(s["lat"], s["lon"], s["start"], s["end"])

        if records:
            path = save_csv(s["name"], records, min_mm, max_mm, mean_mm)
            for r in records:
                pct = r["soil_mm"] / max_mm * 100 if max_mm > 0 else 0
                print(f"    {r['date']}: {r['soil_mm']:.0f} mm = {pct:.1f}%")
        print()

    print(f"\nAll data saved to: {OUTPUT_DIR}")
