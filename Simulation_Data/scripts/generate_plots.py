#!/usr/bin/env python3
"""
Generate plots for the flood simulation datasets.
Creates time-series plots with alert tier overlays for each scenario.
"""

import csv
import os
import sys
from datetime import datetime, timedelta

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("matplotlib not installed. Try: pip install matplotlib")
    sys.exit(1)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "datasets")
FIGURE_DIR = os.path.join(BASE_DIR, "figures")
os.makedirs(FIGURE_DIR, exist_ok=True)

# Color scheme
TIER_COLORS = {
    'SAFE': '#2ecc71',      # Green
    'WARNING': '#f39c12',   # Yellow/Orange
    'EVACUATE': '#e74c3c',  # Red
}

SMALL_SIZE = 10
MEDIUM_SIZE = 12
BIGGER_SIZE = 14
plt.rc('font', size=SMALL_SIZE)
plt.rc('axes', titlesize=MEDIUM_SIZE)
plt.rc('axes', labelsize=MEDIUM_SIZE)
plt.rc('xtick', labelsize=9)
plt.rc('ytick', labelsize=9)
plt.rc('legend', fontsize=10)
plt.rc('figure', titlesize=BIGGER_SIZE)


def read_csv(filepath):
    """Read CSV data file."""
    if not os.path.exists(filepath):
        print(f"  WARNING: {filepath} not found")
        return None
    samples = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['hours'] = float(row['hours'])
            row['water_level_cm'] = float(row['water_level_cm'])
            row['risk_index'] = float(row['risk_index'])
            row['soil_moisture_pct'] = float(row['soil_moisture_pct'])
            row['humidity_pct'] = float(row['humidity_pct'])
            row['temp_c'] = float(row.get('temp_c', 0))
            row['rise_rate_cm_per_s'] = float(row.get('rise_rate_cm_per_s', 0))
            samples.append(row)
    return samples


def plot_scenario(scenario_key, samples, title):
    """Create a comprehensive 2-panel plot for a scenario."""
    if not samples:
        return

    hours = [s['hours'] for s in samples]
    wl = [s['water_level_cm'] for s in samples]
    risk = [s['risk_index'] for s in samples]
    soil = [s['soil_moisture_pct'] for s in samples]
    tiers = [s['alert_tier'] for s in samples]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    fig.suptitle(title, fontsize=14, fontweight='bold', y=0.98)

    # Panel 1: Water Level + Alert Tiers + Soil Moisture
    # Color background by alert tier
    for i in range(len(hours) - 1):
        color = TIER_COLORS.get(tiers[i], '#cccccc')
        ax1.axvspan(hours[i], hours[i+1], alpha=0.08, color=color)

    ax1.plot(hours, wl, 'b-', linewidth=1.5, label='Water Level (cm)')
    ax1.plot(hours, soil, 'g-', linewidth=1.0, alpha=0.7, label='Soil Moisture (%)')

    # Threshold lines
    ax1.axhline(y=40, color='r', linestyle='--', alpha=0.4, linewidth=0.8, label='EVACUATE threshold (40cm)')
    ax1.axhline(y=10, color='g', linestyle='--', alpha=0.4, linewidth=0.8, label='SAFE threshold (10cm)')

    ax1.set_ylabel('Water Level (cm) / Soil (%)')
    ax1.set_ylim(0, max(60, max(wl) * 1.2))
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left', ncol=2)

    # Annotate tier transitions
    prev_tier = tiers[0]
    transition_times = []
    for i, t in enumerate(tiers):
        if t != prev_tier:
            transition_times.append((hours[i], prev_tier, t))
            prev_tier = t
    for ht, fr, to in transition_times:
        ax1.axvline(x=ht, color=TIER_COLORS.get(to, 'gray'), linestyle=':', alpha=0.7)
        ax1.annotate(f'{fr}->{to}', xy=(ht, ax1.get_ylim()[1]*0.95),
                    fontsize=7, ha='right', rotation=90,
                    color=TIER_COLORS.get(to, 'gray'))

    # Panel 2: Risk Index
    for i in range(len(hours) - 1):
        color = TIER_COLORS.get(tiers[i], '#cccccc')
        ax2.axvspan(hours[i], hours[i+1], alpha=0.08, color=color)

    ax2.plot(hours, risk, 'k-', linewidth=1.5, label='Risk Index (R)')
    ax2.axhline(y=75, color='r', linestyle='--', alpha=0.6, linewidth=1.0, label='EVACUATE (R=75)')
    ax2.axhline(y=40, color='orange', linestyle='--', alpha=0.6, linewidth=1.0, label='WARNING (R=40)')
    ax2.fill_between(hours, 0, risk, alpha=0.2, color='gray')

    ax2.set_xlabel('Time (hours)')
    ax2.set_ylabel('Composite Risk Index (0-100)')
    ax2.set_ylim(0, 110)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left', ncol=3)

    plt.tight_layout()
    outpath = os.path.join(FIGURE_DIR, f'{scenario_key}.png')
    fig.savefig(outpath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved plot: {outpath}")


def plot_comparison(scenario_data):
    """Create a combined comparison plot showing all scenarios."""
    fig, ax = plt.subplots(figsize=(14, 6))

    colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']
    line_styles = ['-', '--', '-.', ':', '-', '--']

    for i, (key, samples) in enumerate(scenario_data.items()):
        if not samples:
            continue
        hours = [s['hours'] for s in samples]
        risk = [s['risk_index'] for s in samples]
        label = f"{key.replace('_',' ').title()}"
        ax.plot(hours, risk, color=colors[i % len(colors)],
                linestyle=line_styles[i % len(line_styles)],
                linewidth=1.5, alpha=0.8, label=label)

    ax.axhline(y=75, color='r', linestyle='--', alpha=0.5, label='EVACUATE (R=75)')
    ax.axhline(y=40, color='orange', linestyle='--', alpha=0.5, label='WARNING (R=40)')
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('Composite Risk Index (0-100)')
    ax.set_title('All Flood Scenarios: Risk Index Over Time')
    ax.set_ylim(0, 110)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', ncol=2, fontsize=8)

    plt.tight_layout()
    outpath = os.path.join(FIGURE_DIR, 'all_scenarios_comparison.png')
    fig.savefig(outpath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved comparison: {outpath}")


def main():
    print("Generating plots...")

    scenario_files = [
        ('normal_dry', 'Normal Dry Season (Nov-Apr) -- SAFE throughout'),
        ('monsoon_gradual', 'Monsoon Gradual Rise (Jun-Jul) -- SAFE -> WARNING -> EVACUATE'),
        ('flash_flood', 'Flash Flood (Rapid Rise) -- SAFE -> WARNING'),
        ('coastal_storm_surge', 'Coastal Storm Surge (Cyclone) -- Rapid EVACUATE'),
        ('urban_drain_overload', 'Urban Drain Overload (Dhaka Canal) -- Tidal/Rain Peaks'),
        ('post_flood_recession', 'Post-Flood Water Recession -- Gradual Decline'),
    ]

    all_data = {}
    for key, title in scenario_files:
        filepath = os.path.join(DATASET_DIR, f'{key}.csv')
        samples = read_csv(filepath)
        if samples:
            all_data[key] = samples
            plot_scenario(key, samples, title)

    # Comparison plot
    plot_comparison(all_data)

    print(f"\nAll plots saved to: {FIGURE_DIR}")


if __name__ == '__main__':
    main()
