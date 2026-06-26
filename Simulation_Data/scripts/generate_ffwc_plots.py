#!/usr/bin/env python3
"""
Generate FFWC hypothetical scenario plots showing how the risk index
would react to real historical flood conditions at Buriganga at Dhaka.
"""

import csv, json, os, sys

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("matplotlib not installed.")
    sys.exit(1)

# Paths
BDIR = r"C:\Users\Antech\OneDrive - northsouth.edu\School\UNI RESOURCES\4th Year\11th Semester\CSE331L.7\Journal"
FIGURE_DIR = os.path.join(BDIR, "Simulation_Data", "figures")
os.makedirs(FIGURE_DIR, exist_ok=True)

# Style
plt.rc('font', size=10)
plt.rc('axes', titlesize=12, labelsize=11)
plt.rc('figure', titlesize=13)

# Scenario data
scenarios = [
    ("Normal Dry Season\n(2021 baseline)", 3.0, 12, 45, 0.1, "SAFE"),
    ("Monsoon Onset\n(June)", 8.0, 35, 78, 1.5, "SAFE"),
    ("Low Monsoon 2018\n(4.64m peak)", 15.0, 45, 75, 0.8, "SAFE"),
    ("Near-Miss 2020\n(5.53m peak)", 28.0, 75, 88, 2.5, "WARNING"),
    ("Peak Monsoon 2021\n(5.15m peak)", 35.0, 85, 92, 2.0, "WARNING"),
    ("Highest Recorded\n1968 (7.58m)", 40.0, 90, 90, 4.0, "EVACUATE"),
    ("1988 Flood\n(13.71m)", 44.0, 95, 95, 6.0, "EVACUATE"),
    ("1998 Worst Flood\n(15.19m)", 48.0, 100, 98, 8.0, "EVACUATE"),
]

TIER_COLORS = {'SAFE': '#2ecc71', 'WARNING': '#f39c12', 'EVACUATE': '#e74c3c'}


def compute_risk(water_cm, rise_cmh, soil, hum, temp=28):
    D_SAFE, D_EVAC = 10.0, 40.0
    if water_cm <= D_SAFE: W = 0
    elif water_cm >= D_EVAC: W = 100
    else: W = 100 * (water_cm - D_SAFE) / (D_EVAC - D_SAFE)
    S = min(100, max(0, soil))
    rise_cms = rise_cmh / 3600
    V_MAX = 5.0
    RR = min(100, max(0, 100 * abs(rise_cms) / V_MAX))
    H = min(100, max(0, 100 * (hum - 60) / 35))
    T = 0
    if temp > 35: T = 100
    elif temp > 32: T = 50
    elif temp < 15: T = 30
    R = 0.50 * W + 0.29 * S + 0.15 * RR + 0.03 * H + 0.03 * T
    return round(R, 1)


def make_bar_chart():
    """Bar chart showing risk index for each historical scenario."""
    labels = [s[0] for s in scenarios]
    risks = []
    tiers = []
    for s in scenarios:
        r = compute_risk(s[1], s[4], s[2], s[3])
        risks.append(r)
        if r >= 75: t = 'EVACUATE'
        elif r >= 40: t = 'WARNING'
        else: t = 'SAFE'
        tiers.append(t)
    
    fig, ax = plt.subplots(figsize=(10, 5.5))
    
    x = np.arange(len(labels))
    colors = [TIER_COLORS[t] for t in tiers]
    bars = ax.bar(x, risks, color=colors, edgecolor='white', linewidth=0.8, width=0.65)
    
    # Threshold lines
    ax.axhline(y=75, color='red', linestyle='--', linewidth=1.2, alpha=0.7, label='EVACUATE (R=75)')
    ax.axhline(y=40, color='orange', linestyle='--', linewidth=1.2, alpha=0.7, label='WARNING (R=40)')
    
    # Bar labels
    for i, (bar, risk, tier) in enumerate(zip(bars, risks, tiers)):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1.5,
                f'R={risk}', ha='center', va='bottom', fontsize=8, fontweight='bold')
        # Water level label
        wl = scenarios[i][1]
        ax.text(bar.get_x() + bar.get_width()/2., 3,
                f'WL={wl:.0f}cm', ha='center', va='bottom', fontsize=6.5, color='white', fontweight='bold')
    
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5, linespacing=1.2)
    ax.set_ylabel('Composite Flood Risk Index (R)')
    ax.set_ylim(0, 105)
    ax.set_title('Risk Index Reaction to FFWC Historical Flood Scenarios\nBuriganga River at Dhaka (SW-264)', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.legend(loc='upper left', fontsize=9)
    
    # Tier zone shading
    ax.axhspan(75, 100, alpha=0.05, color='red')
    ax.axhspan(40, 75, alpha=0.05, color='orange')
    ax.axhspan(0, 40, alpha=0.05, color='green')
    
    plt.tight_layout()
    out = os.path.join(FIGURE_DIR, 'ffwc_historical_risk_bars.png')
    fig.savefig(out, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out}")


def make_component_breakdown():
    """Stacked bar chart showing how each factor contributes."""
    labels = [s[0] for s in scenarios]
    
    fig, ax = plt.subplots(figsize=(10, 5))
    
    x = np.arange(len(labels))
    width = 0.55
    
    # Calculate component scores for each scenario
    w_scores = []
    s_scores = []
    rr_scores = []
    ht_scores = []  # H+T combined
    for s in scenarios:
        wl, soil, hum, rise, temp = s[1], s[2], s[3], s[4], 28
        D_SAFE, D_EVAC = 10.0, 40.0
        if wl <= D_SAFE: W = 0
        elif wl >= D_EVAC: W = 100
        else: W = 100 * (wl - D_SAFE) / (D_EVAC - D_SAFE)
        S = min(100, max(0, soil))
        rise_cms = rise / 3600
        RR = min(100, max(0, 100 * abs(rise_cms) / 5.0))
        H = min(100, max(0, 100 * (hum - 60) / 35))
        
        w_scores.append(W * 0.50)
        s_scores.append(S * 0.29)
        rr_scores.append(RR * 0.15)
        ht_scores.append(H * 0.03)
    
    ax.bar(x, w_scores, width, label='Water (50%)', color='#3498db')
    ax.bar(x, s_scores, width, bottom=w_scores, label='Soil (29%)', color='#27ae60')
    ax.bar(x, rr_scores, width, bottom=[w+s for w,s in zip(w_scores, s_scores)], label='Rise Rate (15%)', color='#e67e22')
    ax.bar(x, ht_scores, width, bottom=[w+s+r for w,s,r in zip(w_scores, s_scores, rr_scores)], label='Hum+Temp (6%)', color='#95a5a6')
    
    ax.axhline(y=75, color='red', linestyle='--', alpha=0.5)
    ax.axhline(y=40, color='orange', linestyle='--', alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7.5, linespacing=1.1)
    ax.set_ylabel('Risk Index Contribution')
    ax.set_title('Factor Breakdown: FFWC Scenario Risk Index Components', fontweight='bold')
    ax.legend(fontsize=8, loc='upper left')
    ax.set_ylim(0, 105)
    
    plt.tight_layout()
    out = os.path.join(FIGURE_DIR, 'ffwc_risk_components.png')
    fig.savefig(out, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out}")


def make_historical_timeline():
    """Timeline of Buriganga peak water levels 2012-2021 vs DL."""
    years = list(range(2012, 2022))
    peaks = [4.95, 4.92, 5.11, 5.20, 5.21, 5.22, 4.64, 4.90, 5.53, 5.15]
    dl = 6.00
    
    fig, ax = plt.subplots(figsize=(8, 4))
    
    ax.bar(years, peaks, width=0.6, color='#3498db', edgecolor='white', label='Peak WL')
    ax.axhline(y=dl, color='red', linestyle='--', linewidth=1.5, label=f'Danger Level ({dl} mPWD)')
    
    for y, p in zip(years, peaks):
        margin = (dl - p) * 100
        ax.text(y, p + 0.1, f'{p:.2f}m\n({margin:.0f}cm below)', 
                ha='center', va='bottom', fontsize=7.5)
    
    ax.set_xlabel('Year')
    ax.set_ylabel('Peak Water Level (mPWD)')
    ax.set_title('Buriganga at Dhaka: Annual Peak Water Levels (FFWC Data)', fontweight='bold')
    ax.set_ylim(3.5, 7.5)
    ax.legend(fontsize=9)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    out = os.path.join(FIGURE_DIR, 'ffwc_buriganga_timeline.png')
    fig.savefig(out, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out}")


def make_csv_table():
    """Save a CSV of the scenario data."""
    out_path = os.path.join(
        r"C:\Users\Antech\OneDrive - northsouth.edu\School\UNI RESOURCES\4th Year\11th Semester\CSE331L.7\Journal\Simulation_Data\datasets",
        "ffwc_hypothetical_scenarios.csv"
    )
    with open(out_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["Scenario", "Real Data Source", "WL(cm)", "Soil(%)", "Hum(%)", 
                     "Rise(cm/h)", "Risk Index", "Tier"])
        for s in scenarios:
            risk = compute_risk(s[1], s[4], s[2], s[3])
            tier = "EVACUATE" if risk >= 75 else ("WARNING" if risk >= 40 else "SAFE")
            w.writerow([s[0].replace('\n', ' '), s[1], s[2], s[3], s[4], risk, tier])
    print(f"Saved CSV: {out_path}")


if __name__ == '__main__':
    make_historical_timeline()
    make_bar_chart()
    make_component_breakdown()
    make_csv_table()
    print(f"\nAll figures saved to: {FIGURE_DIR}")
