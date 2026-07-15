#!/usr/bin/env python3
"""
Smart Flood Early Warning System -- Simulation Data Generator
Generates realistic sensor data based on Bangladesh flood patterns.
References: SentryLeaf (Rohan 2025), Zeng et al. (2025), BWDB/FFWC historical patterns,
Tangdamrongsub (2021) soil moisture correlations, Mdegela et al. (2023).
"""

import csv
import json
import math
import random
import os
from datetime import datetime, timedelta

random.seed(42)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(OUTPUT_DIR, "datasets")
os.makedirs(DATASET_DIR, exist_ok=True)


class LeastSquaresTrend:
    """Ring-buffer least-squares slope estimator.
       Maintains a window of recent water-level readings and computes
       the smoothed slope (cm/h) via linear regression.
       Includes a deadband threshold to reject sensor noise.
       Matches the 'least-squares trend engine' described in the paper.
    """
    def __init__(self, window=40, min_slope_threshold=1.0):
        self.window = window
        self.min_slope = min_slope_threshold  # cm/h — below this treat as 0
        self.buffer = []

    def add(self, wl_cm, t_hours):
        self.buffer.append((t_hours, wl_cm))
        if len(self.buffer) > self.window:
            self.buffer.pop(0)

    def slope_cm_per_h(self):
        """Returns smoothed slope in cm/h. Only positive slopes (rising water)
           are considered flood-relevant; receding water returns 0.
           Slopes below min_slope are treated as zero (noise deadband).
           Requires minimum net water level rise over the window."""
        n = len(self.buffer)
        if n < 8:
            return 0.0
        
        # Check the net water level change over the window
        # If water hasn't risen at least 1.5cm, any trend is noise
        first_wl = self.buffer[0][1]
        last_wl = self.buffer[-1][1]
        net_rise = last_wl - first_wl
        if net_rise < 1.5:  # cm — below this, treat drift as noise
            return 0.0
        
        sum_x = sum(x for x, _ in self.buffer)
        sum_y = sum(y for _, y in self.buffer)
        sum_xx = sum(x*x for x, _ in self.buffer)
        sum_xy = sum(x*y for x, y in self.buffer)
        denom = n * sum_xx - sum_x * sum_x
        if abs(denom) < 1e-10:
            return 0.0
        slope = (n * sum_xy - sum_x * sum_y) / denom
        slope_cmh = slope * 3600
        
        # Only rising water contributes to flood risk
        if slope_cmh <= 0:
            return 0.0
        # Noise deadband
        if slope_cmh < self.min_slope:
            return 0.0
        return slope_cmh

# ===================================================================
# SCENARIO DEFINITIONS (based on real Bangladesh flood patterns)
# ===================================================================
# Sources:
# - FFWC/BWDB: typical monsoon water level patterns
# - Tangdamrongsub (2021): soil moisture correlations
# - Rohan et al. (2025): SentryLeaf water level measurements (2.5-3.5m range)
# - Zeng et al. (2025): STM32-based sensor validation methodology

SCENARIOS = {
    "normal_dry": {
        "name": "Normal Dry Season (November-April)",
        "description": "Typical dry season in Bangladesh. Low water levels, dry soil, stable conditions. Risk index should remain SAFE.",
        "duration_hours": 72,
        "sample_interval_s": 300,  # 5 min
        "water_level_base_cm": 5.0,
        "water_level_noise_cm": 1.0,
        "soil_moisture_pct": 15,
        "soil_noise_pct": 3,
        "humidity_pct": 45,
        "temp_c": 28,
        "has_rain_event": False,
    },
    "monsoon_gradual": {
        "name": "Monsoon Gradual Rise (June-July)",
        "description": "Typical monsoon pattern: gradual water level rise over 48h followed by sustained high water. Soil saturation increases over time. Risk should transition SAFE->WARNING->EVACUATE.",
        "duration_hours": 72,
        "sample_interval_s": 300,
        "water_level_base_cm": 8.0,
        "water_level_noise_cm": 1.5,
        "soil_moisture_pct": 35,
        "soil_noise_pct": 5,
        "humidity_pct": 78,
        "temp_c": 30,
        "has_rain_event": True,
        "rain_start_hour": 6,
        "rain_duration_hours": 36,
        "water_rise_rate_cm_per_h": 1.2,  # Gradual rise
        "max_water_cm": 50,
    },
    "flash_flood": {
        "name": "Flash Flood (Sudden, Rapid Rise)",
        "description": "Flash flood scenario: rapid water level rise over 6-8 hours. Common in Dhaka canals during intense monsoon rain. Risk should spike quickly to EVACUATE.",
        "duration_hours": 24,
        "sample_interval_s": 60,  # 1 min for high resolution
        "water_level_base_cm": 5.0,
        "water_level_noise_cm": 2.0,
        "soil_moisture_pct": 60,
        "soil_noise_pct": 5,
        "humidity_pct": 92,
        "temp_c": 27,
        "has_rain_event": True,
        "rain_start_hour": 1,
        "rain_duration_hours": 6,
        "water_rise_rate_cm_per_h": 8.0,  # Very rapid rise
        "max_water_cm": 45,
    },
    "coastal_storm_surge": {
        "name": "Coastal Storm Surge (Cyclone)",
        "description": "Cyclone-induced storm surge: sharp water level spike with debris-laden turbulent water. High humidity, saturated soil. Risk hits EVACUATE fastest.",
        "duration_hours": 18,
        "sample_interval_s": 120,
        "water_level_base_cm": 10.0,
        "water_level_noise_cm": 3.0,  # Higher noise from turbulence
        "soil_moisture_pct": 85,  # Near saturated
        "soil_noise_pct": 3,
        "humidity_pct": 95,
        "temp_c": 26,
        "has_rain_event": True,
        "rain_start_hour": 0,
        "rain_duration_hours": 12,
        "water_rise_rate_cm_per_h": 6.0,
        "max_water_cm": 40,
    },
    "urban_drain_overload": {
        "name": "Urban Drain Overload (Dhaka Canal)",
        "description": "Dhaka urban drainage canal scenario: water level rises and falls with tide/rain. Multiple peaks over 48h. Soil stays wet. Intermittent warnings.",
        "duration_hours": 48,
        "sample_interval_s": 300,
        "water_level_base_cm": 6.0,
        "water_level_noise_cm": 1.5,
        "soil_moisture_pct": 50,
        "soil_noise_pct": 5,
        "humidity_pct": 82,
        "temp_c": 29,
        "has_rain_event": True,
        "rain_start_hour": 4,
        "rain_duration_hours": 8,
        "water_rise_rate_cm_per_h": 3.5,
        "max_water_cm": 35,
    },
    "post_flood_recession": {
        "name": "Post-Flood Water Recession",
        "description": "Flood waters gradually receding. Water level falls from flood stage to normal. Soil remains saturated. Risk transitions from EVACUATE to SAFE.",
        "duration_hours": 48,
        "sample_interval_s": 300,
        "water_level_base_cm": 45.0,
        "water_level_noise_cm": 1.0,
        "soil_moisture_pct": 70,
        "soil_noise_pct": 5,
        "humidity_pct": 75,
        "temp_c": 31,
        "has_rain_event": False,
    }
}


def compute_risk_index(water_cm, rise_rate_cm_per_h, soil_pct, humidity_pct, temp_c):
    """
    Composite Flood Risk Index:
    R = 0.50*W + 0.29*S + 0.15*RR + 0.03*H + 0.03*T

    Source: Derived from hazard-severity analysis.
    Water (50%): direct hazard measure
    Soil (29%): SCS-CN antecedent moisture conditions (USDA-NRCS, 2004)
    Rise rate (15%): Modified Flash Flood Index (Kim & Choi, 2014)
    Humidity (3%) + Temp (3%): supporting context
    """
    # Normalize water level: 0cm = SAFE, 40cm+ = EVACUATE
    D_SAFE = 10.0
    D_EVAC = 40.0
    if water_cm <= D_SAFE:
        W = 0
    elif water_cm >= D_EVAC:
        W = 100
    else:
        W = 100 * (water_cm - D_SAFE) / (D_EVAC - D_SAFE)

    # Soil moisture score: 0-100 directly
    S = min(100, max(0, soil_pct))

    # Rise rate score: normalized to 5 cm/h max
    V_MAX = 5.0  # cm/h
    # Rise rate only contributes when water is actively rising ABOVE safe baseline
    # Below safe threshold, any rise rate is pre-flood and not yet hazardous
    if water_cm <= D_SAFE:
        RR = 0
    else:
        RR = min(100, max(0, 100 * rise_rate_cm_per_h / V_MAX))

    # Humidity score: 60% = 0, 95%+ = 100
    H = min(100, max(0, 100 * (humidity_pct - 60) / 35))

    # Temperature score: 20°C → 0, 40°C → 100
    T = min(100, max(0, 100 * (temp_c - 20) / 20))

    R = 0.50 * W + 0.29 * S + 0.15 * RR + 0.03 * H + 0.03 * T
    return round(R, 1)


def get_alert_tier(risk_index, prev_tier=None):
    """Three-tier alert with hysteresis."""
    if prev_tier == "EVACUATE":
        if risk_index <= 35:
            return "WARNING" if risk_index > 20 else "SAFE"
        return "EVACUATE"
    elif prev_tier == "WARNING":
        if risk_index >= 75:
            return "EVACUATE"
        if risk_index <= 35:
            return "SAFE"
        return "WARNING"
    else:  # SAFE
        if risk_index >= 75:
            return "EVACUATE"
        if risk_index >= 40:
            return "WARNING"
        return "SAFE"


def generate_scenario(scenario_key, params):
    """Generate sensor data for a given flood scenario."""
    print(f"Generating: {params['name']}...")

    samples = []
    duration_s = params['duration_hours'] * 3600
    interval_s = params['sample_interval_s']
    n_samples = duration_s // interval_s

    current_tier = "SAFE"
    wl = params['water_level_base_cm']
    soil = params['soil_moisture_pct']
    hum = params['humidity_pct']
    temp = params['temp_c']

    # Rise rate via smoothed least-squares trend engine
    trend = LeastSquaresTrend()  # window=40, min_slope=1.0 cm/h
    rise_rate_cm_per_h = 0.0

    # Rain event timing
    rain_active = False
    rain_end_time = 0

    for i in range(n_samples):
        t_hours = i * interval_s / 3600
        timestamp = f"T+{t_hours:06.2f}h"

        # Rain event
        if params.get('has_rain_event'):
            rain_start = params.get('rain_start_hour', 0)
            rain_dur = params.get('rain_duration_hours', 0)
            if t_hours >= rain_start and t_hours <= rain_start + rain_dur:
                rain_active = True
            else:
                rain_active = False

        # Water level dynamics
        if scenario_key == "normal_dry":
            wl = params['water_level_base_cm'] + random.gauss(0, params['water_level_noise_cm'])
        elif scenario_key == "monsoon_gradual":
            if rain_active:
                rise = params.get('water_rise_rate_cm_per_h', 1.0) * interval_s / 3600
                wl += rise
            else:
                wl += random.gauss(0, params['water_level_noise_cm']) * 0.5
            wl = min(wl, params.get('max_water_cm', 50))
        elif scenario_key == "flash_flood":
            if rain_active:
                rise = params.get('water_rise_rate_cm_per_h', 8.0) * interval_s / 3600
                wl += rise
            else:
                wl -= random.gauss(0.5, 0.5)
            wl = max(5, min(wl, params.get('max_water_cm', 50)))
        elif scenario_key == "coastal_storm_surge":
            if rain_active:
                # Storm surge: monotonic rise to peak over 4h, then sustained
                surge_duration = 4.0
                if t_hours <= surge_duration:
                    # Start from base level, rise linearly to max
                    target_wl = (params['water_level_base_cm'] + 
                                (params.get('max_water_cm', 40) - params['water_level_base_cm']) * 
                                (t_hours / surge_duration))
                else:
                    target_wl = params.get('max_water_cm', 40)
                wl = target_wl + random.gauss(0, params['water_level_noise_cm'] * 0.3)
            else:
                # Recession
                wl -= 0.8 * interval_s / 3600
                wl = max(params['water_level_base_cm'], wl + random.gauss(0, params['water_level_noise_cm'] * 0.2))
            wl = max(5, min(wl, params.get('max_water_cm', 45)))
        elif scenario_key == "urban_drain_overload":
            tidal = 3.0 * math.sin(2 * math.pi * t_hours / 12.4)
            if rain_active:
                wl += params.get('water_rise_rate_cm_per_h', 3.5) * interval_s / 3600
            wl = params['water_level_base_cm'] + tidal + random.gauss(0, params['water_level_noise_cm'])
            wl = max(5, wl)
        elif scenario_key == "post_flood_recession":
            wl = params['water_level_base_cm'] - (0.8 * t_hours / 48)
            wl = max(5, wl + random.gauss(0, params['water_level_noise_cm']))

        # Soil moisture dynamics
        if rain_active:
            soil = min(100, soil + 2.0 * interval_s / 3600)
        else:
            soil = max(params['soil_moisture_pct'], soil - 0.5 * interval_s / 3600)

        # Humidity dynamics
        if rain_active:
            hum = min(98, hum + 0.5)
        else:
            hum = max(params['humidity_pct'], hum - 0.1)

        # Rise rate via smoothed least-squares trend engine
        trend.add(wl, t_hours)
        rise_rate_cm_per_h = trend.slope_cm_per_h()

        # Compute risk index
        risk = compute_risk_index(wl, rise_rate_cm_per_h, soil, hum, temp)
        current_tier = get_alert_tier(risk, current_tier)

        # Determine sensor status flags
        dht_ok = random.random() > 0.02
        ultra_valid = random.random() > 0.05

        samples.append({
            'timestamp': timestamp,
            'hours': round(t_hours, 3),
            'water_level_cm': round(wl, 2),
            'rise_rate_cm_per_h': round(rise_rate_cm_per_h, 4),
            'soil_moisture_pct': round(soil, 1),
            'humidity_pct': round(hum, 1),
            'temp_c': round(temp + random.gauss(0, 0.5), 1),
            'risk_index': risk,
            'alert_tier': current_tier,
            'rain_active': rain_active,
            'dht_ok': dht_ok,
            'ultra_valid': ultra_valid,
        })

    return samples


def save_csv(filename, samples):
    filepath = os.path.join(DATASET_DIR, filename)
    if not samples:
        print(f"  WARNING: No samples to save for {filename}")
        return
    keys = samples[0].keys()
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(samples)
    print(f"  Saved {len(samples)} rows to {filepath}")


def save_json(filename, data):
    filepath = os.path.join(DATASET_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  Saved to {filepath}")


def generate_all():
    all_data = {}

    for key, params in SCENARIOS.items():
        samples = generate_scenario(key, params)
        analysis = analyze_scenario(samples, params)
        all_data[key] = {
            "scenario": params,
            "analysis": analysis,
            "summary_stats": compute_summary(samples)
        }
        save_csv(f"{key}.csv", samples)

    save_json("scenario_analysis.json", all_data)
    print("\nAll datasets generated successfully!")


def compute_summary(samples):
    if not samples:
        return {}
    risks = [s['risk_index'] for s in samples]
    tiers = [s['alert_tier'] for s in samples]
    wls = [s['water_level_cm'] for s in samples]
    soils = [s['soil_moisture_pct'] for s in samples]
    return {
        "samples": len(samples),
        "risk_min": min(risks),
        "risk_max": max(risks),
        "risk_avg": round(sum(risks)/len(risks), 1),
        "tier_counts": {t: tiers.count(t) for t in set(tiers)},
        "water_level_max": max(wls),
        "water_level_avg": round(sum(wls)/len(wls), 1),
        "soil_max": max(soils),
        "soil_avg": round(sum(soils)/len(soils), 1),
    }


def analyze_scenario(samples, params):
    """
    Analyze how the risk index responds to the scenario.
    Identifies transition points and response times.
    """
    if not samples:
        return {"error": "No data"}

    transitions = []
    prev_tier = samples[0]['alert_tier']
    time_to_evacuate = None
    time_to_warning = None

    for s in samples:
        if s['alert_tier'] != prev_tier:
            transitions.append({
                'time_hours': s['hours'],
                'from_tier': prev_tier,
                'to_tier': s['alert_tier'],
                'risk_at_transition': s['risk_index'],
                'water_level_at_transition': s['water_level_cm']
            })
            if s['alert_tier'] == 'EVACUATE' and time_to_evacuate is None:
                time_to_evacuate = s['hours']
            if s['alert_tier'] == 'WARNING' and time_to_warning is None:
                time_to_warning = s['hours']
            prev_tier = s['alert_tier']

    return {
        "total_transitions": len(transitions),
        "transitions": transitions,
        "time_to_warning_hours": time_to_warning,
        "time_to_evacuate_hours": time_to_evacuate,
        "max_risk": max(s['risk_index'] for s in samples),
        "avg_risk_during_rain": round(
            sum(s['risk_index'] for s in samples if s['rain_active']) /
            max(1, sum(1 for s in samples if s['rain_active'])), 1
        ),
    }


if __name__ == "__main__":
    generate_all()
    print(f"\nDataset directory: {DATASET_DIR}")

    # Print quick summary from the analysis file
    print("\n" + "="*65)
    print("SCENARIO SUMMARY")
    print("="*65)
    for key, params in SCENARIOS.items():
        summary = compute_summary(generate_scenario(key, params))
        analysis = analyze_scenario(generate_scenario(key, params), params)
        print(f"\n{params['name']}")
        print(f"  Samples: {summary['samples']}")
        print(f"  Risk range: {summary['risk_min']} -> {summary['risk_max']} (avg: {summary['risk_avg']})")
        print(f"  Alert distribution: {summary['tier_counts']}")
        if analysis['time_to_warning_hours']:
            print(f"  Time to WARNING: {analysis['time_to_warning_hours']:.1f}h")
        if analysis['time_to_evacuate_hours']:
            print(f"  Time to EVACUATE: {analysis['time_to_evacuate_hours']:.1f}h")
        if analysis['transitions']:
            for t in analysis['transitions']:
                print(f"  Transition: {t['from_tier']} -> {t['to_tier']} at t={t['time_hours']:.1f}h, R={t['risk_at_transition']}, WL={t['water_level_at_transition']:.1f}cm")
