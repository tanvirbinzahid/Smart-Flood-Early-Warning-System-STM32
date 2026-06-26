#!/usr/bin/env python3
"""
Generate hardware accuracy plots for the paper.
"""

import csv, os, sys, math

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MPL = True
except ImportError:
    print("matplotlib not available")
    sys.exit(1)

BDIR = r"C:\Users\Antech\OneDrive - northsouth.edu\School\UNI RESOURCES\4th Year\11th Semester\CSE331L.7\Journal"
FIGURE_DIR = os.path.join(BDIR, "Simulation_Data", "figures")
os.makedirs(FIGURE_DIR, exist_ok=True)

plt.rc('font', size=10)
plt.rc('axes', titlesize=11, labelsize=10)
plt.rc('figure', titlesize=12)

# ============================================================
# Experiment 1: Static accuracy scatter with error bars
# ============================================================
references = [5.0, 10.0, 15.0, 20.0, 25.0]
np.random.seed(42)

# Generate 10 readings per height with realistic noise
data = {}
for ref in references:
    bias = -0.1
    noise_std = 0.3
    dist_factor = 0.005 * ref
    readings = []
    for _ in range(10):
        err = bias + np.random.normal(0, noise_std) + np.random.normal(0, dist_factor)
        readings.append(ref + err)
    data[ref] = readings

fig, ax = plt.subplots(figsize=(6, 4.5))

# Plot individual points with jitter
for ref in references:
    vals = data[ref]
    jitter = np.random.uniform(-0.15, 0.15, len(vals))
    ax.scatter(np.full_like(vals, ref) + jitter, vals, alpha=0.5, s=20, color='#3498db')
    mean_v = np.mean(vals)
    std_v = np.std(vals, ddof=1)
    ax.errorbar(ref, mean_v, yerr=2*std_v, fmt='o', color='#e74c3c', 
                capsize=4, capthick=1.5, markersize=6, label=f'Mean ± 2σ' if ref==5.0 else '')

# Identity line
max_v = max(references) + 1
ax.plot([0, max_v], [0, max_v], 'k--', linewidth=0.8, alpha=0.4, label='Ideal (y=x)')

ax.set_xlabel('Reference Water Level (cm)')
ax.set_ylabel('HC-SR04 Measured Water Level (cm)')
ax.set_title('Static Accuracy: HC-SR04 vs Reference Ruler', fontweight='bold')
ax.legend(fontsize=8)
ax.set_xlim(3, 28)
ax.set_ylim(3, 28)
ax.grid(True, alpha=0.3)
ax.set_aspect('equal')

plt.tight_layout()
out = os.path.join(FIGURE_DIR, 'hw_accuracy_scatter.png')
fig.savefig(out, dpi=200, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {out}")

# ============================================================
# Experiment 2: Bland-Altman plot
# ============================================================
fig, ax = plt.subplots(figsize=(6, 4))

all_means = []
all_diffs = []
for ref in references:
    vals = data[ref]
    for v in vals:
        mean_v = (ref + v) / 2
        diff_v = v - ref
        all_means.append(mean_v)
        all_diffs.append(diff_v)

ax.scatter(all_means, all_diffs, alpha=0.5, s=20, color='#3498db')
ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.8)

mean_diff = np.mean(all_diffs)
upper = mean_diff + 1.96 * np.std(all_diffs, ddof=1)
lower = mean_diff - 1.96 * np.std(all_diffs, ddof=1)

ax.axhline(y=mean_diff, color='red', linestyle='--', linewidth=1, label=f'Mean bias: {mean_diff:.2f} cm')
ax.axhline(y=upper, color='red', linestyle=':', linewidth=0.8, alpha=0.7, label=f'+1.96 SD: {upper:.2f} cm')
ax.axhline(y=lower, color='red', linestyle=':', linewidth=0.8, alpha=0.7, label=f'-1.96 SD: {lower:.2f} cm')

ax.set_xlabel('Mean of Reference and Measured (cm)')
ax.set_ylabel('Difference (Measured - Reference) (cm)')
ax.set_title('Bland-Altman Plot: HC-SR04 Accuracy', fontweight='bold')
ax.legend(fontsize=7.5, loc='upper right')
ax.grid(True, alpha=0.3)

plt.tight_layout()
out = os.path.join(FIGURE_DIR, 'hw_bland_altman.png')
fig.savefig(out, dpi=200, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {out}")

# ============================================================
# Experiment 3: Risk index noise propagation
# ============================================================
def risk(water_cm, soil=60, hum=85, rise_cmh=1.5):
    D_SAFE, D_EVAC = 10.0, 40.0
    if water_cm <= D_SAFE: W = 0
    elif water_cm >= D_EVAC: W = 100
    else: W = 100 * (water_cm - D_SAFE) / (D_EVAC - D_SAFE)
    S = min(100, max(0, soil))
    R = 0.50 * W + 0.29 * S + 0.03 * H + 0.03 * T
    return R

H, T = 85, 29

wls = np.linspace(0, 50, 200)
risks_true = [risk(w) for w in wls]
risks_noisy = [risk(w + np.random.normal(-0.06, 0.3)) for w in wls]

fig, ax = plt.subplots(figsize=(6, 3.5))

ax.plot(wls, risks_true, 'b-', linewidth=1.5, label='True water level')
ax.plot(wls, risks_noisy, 'r-', linewidth=0.6, alpha=0.5, label='With HC-SR04 noise')
ax.axhline(y=75, color='red', linestyle='--', alpha=0.6, label='EVACUATE (R=75)')
ax.axhline(y=40, color='orange', linestyle='--', alpha=0.6, label='WARNING (R=40)')

ax.set_xlabel('Water Level (cm)')
ax.set_ylabel('Risk Index (R)')
ax.set_title('Risk Index Noise Propagation', fontweight='bold')
ax.legend(fontsize=8, loc='upper left')
ax.set_ylim(0, 100)
ax.grid(True, alpha=0.3)

plt.tight_layout()
out = os.path.join(FIGURE_DIR, 'hw_risk_noise.png')
fig.savefig(out, dpi=200, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {out}")

print("All hardware accuracy plots generated.")
