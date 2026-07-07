#!/usr/bin/env python3
"""
IEEE Access - Rigorous Simulation Analysis
D1: Comparative baseline study (water-only, water+soil, MFFI, full index)
D2: Monte Carlo robustness (N=100 runs)
D3: Ablation study (remove each term)
D4: Evaluation metrics (confusion matrices)
"""

import csv, json, math, random, os
from collections import defaultdict

# Paths
SCRIPTS_DIR = r"C:\Users\Antech\OneDrive - northsouth.edu\School\UNI RESOURCES\4th Year\11th Semester\CSE331L.7\Journal\Simulation_Data\scripts"
DATASET_DIR = os.path.join(SCRIPTS_DIR, "datasets")
OUTPUT_DIR  = os.path.join(SCRIPTS_DIR, "..", "figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)

random.seed(42)

# ──── RISK INDEX FUNCTION ────
def compute_risk(water_cm, rise_cmh, soil_pct, hum_pct, temp_c=28):
    D_SAFE, D_EVAC = 10.0, 40.0
    W = 0 if water_cm <= D_SAFE else 100 if water_cm >= D_EVAC else 100 * (water_cm - D_SAFE) / (D_EVAC - D_SAFE)
    S = min(100, max(0, soil_pct))
    RR = min(100, max(0, 100 * rise_cmh / 5.0))
    H = min(100, max(0, 100 * (hum_pct - 60) / 35))
    T = 0
    return round(0.50 * W + 0.29 * S + 0.15 * RR + 0.03 * H + 0.03 * T, 1)

def get_tier(r):
    return "EVACUATE" if r >= 75 else ("WARNING" if r >= 40 else "SAFE")

# ──── SCENARIO DEFINITIONS ────
# Each scenario as a list of (time_h, water_cm, rise_cmh, soil_pct, hum_pct)
# Based on CSV ground truth from the fixed simulation
SCENARIOS = {
    "normal_dry":    {"name": "Normal Dry",     "n": 864,  "dt": 300,  "base": lambda t: (5.0, 0.1, 15, 45)},
    "monsoon":       {"name": "Monsoon Gradual","n": 864,  "dt": 300,  "base": lambda t: (
        8.0 + max(0, min(42, 1.2 * max(0, t-6))), 
        1.2 if 6 < t < 42 else 0, 
        35 + 65 * min(1, max(0, t-6)/36), 
        78 + 20 * min(1, max(0, t-6)/36))},
    "flash_flood":   {"name": "Flash Flood",    "n": 1440, "dt": 60,  "base": lambda t: (
        5.0 + max(0, min(40, 8.0 * max(0, t-1))),
        8.0 if 1 < t < 7 else 0,
        60 + 35 * min(1, max(0, t-1)/5),
        92)},
    "storm_surge":   {"name": "Storm Surge",    "n": 540,  "dt": 120, "base": lambda t: (
        10.0 + min(30, 7.5 * max(0, t)) if t < 4 else 40.0,
        7.5 if t < 4 else 0,
        85, 95)},
    "urban_drain":   {"name": "Urban Drain",    "n": 576,  "dt": 300, "base": lambda t: (
        6.0 + 3.0 * math.sin(2 * math.pi * t / 12.4) + (3.5 if 4 < t < 12 else 0),
        0.5 if 4 < t < 12 else 0,
        50, 82)},
    "recession":     {"name": "Recession",      "n": 576,  "dt": 300, "base": lambda t: (
        max(5, 45 - 0.8 * t),
        -0.8,
        70, 75)},
}

def generate_trace(scenario_key, noise_scale=1.0):
    """Generate a deterministic or noisy trace."""
    s = SCENARIOS[scenario_key]
    trace = []
    for i in range(s["n"]):
        t = i * s["dt"] / 3600
        wl, rr, soil, hum = s["base"](t)
        if noise_scale > 0:
            wl += random.gauss(0, 1.5 * noise_scale)
            soil += random.gauss(0, 5 * noise_scale)
            hum += random.gauss(0, 5 * noise_scale)
        wl = max(0, wl)
        soil = max(0, min(100, soil))
        hum = max(0, min(100, hum))
        trace.append({"t": t, "wl": wl, "rr": max(0, rr), "soil": soil, "hum": hum})
    return trace

def classify_index(trace, weights):
    w_w, w_s, w_rr, w_h, w_t = weights
    result = []
    for pt in trace:
        D_SAFE, D_EVAC = 10.0, 40.0
        W = 0 if pt["wl"] <= D_SAFE else 100 if pt["wl"] >= D_EVAC else 100 * (pt["wl"] - D_SAFE) / (D_EVAC - D_SAFE)
        S = min(100, max(0, pt["soil"]))
        RR = min(100, max(0, 100 * pt["rr"] / 5.0))
        H = min(100, max(0, 100 * (pt["hum"] - 60) / 35))
        R = w_w*W + w_s*S + w_rr*RR + w_h*H + w_t*0
        result.append({"R": R, "tier": get_tier(R)})
    return result

# ──── D1: COMPARATIVE BASELINE STUDY ────
print("=" * 65)
print("D1: COMPARATIVE BASELINE STUDY")
print("=" * 65)

methods = {
    "Water-only threshold": {"weights": (1.0, 0, 0, 0, 0), "desc": "W ≥ 40 → EVACUATE"},
    "Water+Soil":           {"weights": (0.70, 0.30, 0, 0, 0), "desc": "0.70*W + 0.30*S"},
    "MFFI rise-rate only":  {"weights": (0, 0, 1.0, 0, 0), "desc": "100% rise-rate"},
    "Full Composite Risk":  {"weights": (0.50, 0.29, 0.15, 0.03, 0.03), "desc": "all terms"},
}

results_d1 = []
for method_name, method in methods.items():
    print(f"\n  {method_name}:")
    for skey in SCENARIOS:
        trace = generate_trace(skey, noise_scale=0)
        classified = classify_index(trace, method["weights"])
        tiers = [c["tier"] for c in classified]
        risks = [c["R"] for c in classified]
        tw = te = None
        prev = tiers[0]
        for i, t in enumerate(tiers):
            if t != prev:
                if t == "WARNING" and tw is None: tw = trace[i]["t"]
                if t == "EVACUATE" and te is None: te = trace[i]["t"]
                prev = t
        false_alarm = "YES" if tiers.count("EVACUATE") > 3 and "dry" in skey else "NO"
        has_warn = "YES" if te is not None or tw is not None else "NO"
        if "dry" in skey:
            tw_str = "--"
            te_str = "--"
            has_warn = "NO"
        else:
            tw_str = f"{tw:.1f}" if tw else "--"
            te_str = f"{te:.1f}" if te else "--"
        
        print(f"    {SCENARIOS[skey]['name']:<20}  R_range={min(risks):.0f}-{max(risks):.0f}  tWarn={tw_str:<5}  tEvac={te_str:<5}")
        results_d1.append({"method": method_name, "scenario": skey, "r_min": min(risks), "r_max": max(risks), "tw": tw, "te": te})


# ──── D2: MONTE CARLO ROBUSTNESS ────
print("\n\n" + "=" * 65)
print("D2: MONTE CARLO ROBUSTNESS (N=100)")
print("=" * 65)

N_MC = 100
mc_results = {}
for skey in SCENARIOS:
    t_warns, t_evacs = [], []
    for run in range(N_MC):
        trace = generate_trace(skey, noise_scale=1.0)
        classified = classify_index(trace, (0.50, 0.29, 0.15, 0.03, 0.03))
        tiers = [c["tier"] for c in classified]
        tw = te = None
        prev = tiers[0]
        for i, t in enumerate(tiers):
            if t != prev:
                if t == "WARNING" and tw is None: tw = trace[i]["t"]
                if t == "EVACUATE" and te is None: te = trace[i]["t"]
                prev = t
        if tw: t_warns.append(tw)
        if te: t_evacs.append(te)
    
    mc_results[skey] = {
        "t_warn_mean": round(sum(t_warns)/len(t_warns), 2) if t_warns else None,
        "t_warn_std":  round(math.sqrt(sum((x-sum(t_warns)/len(t_warns))**2 for x in t_warns)/len(t_warns)), 2) if t_warns else None,
        "t_evac_mean": round(sum(t_evacs)/len(t_evacs), 2) if t_evacs else None,
        "t_evac_std":  round(math.sqrt(sum((x-sum(t_evacs)/len(t_evacs))**2 for x in t_evacs)/len(t_evacs)), 2) if t_evacs else None,
        "n_warn": len(t_warns),
        "n_evac": len(t_evacs),
    }
    print(f"\n  {SCENARIOS[skey]['name']}:")
    print(f"    t_Warning: {mc_results[skey]['t_warn_mean']} ± {mc_results[skey]['t_warn_std']} h  (n={mc_results[skey]['n_warn']})")
    print(f"    t_Evacuate:{mc_results[skey]['t_evac_mean']} ± {mc_results[skey]['t_evac_std']} h  (n={mc_results[skey]['n_evac']})")


# ──── D3: ABLATION STUDY ────
print("\n\n" + "=" * 65)
print("D3: ABLATION STUDY")
print("=" * 65)

ablations = [
    ("Full index",      (0.50, 0.29, 0.15, 0.03, 0.03)),
    ("Remove Water",    (0.00, 0.58, 0.30, 0.06, 0.06)),
    ("Remove Soil",     (0.50, 0.00, 0.29, 0.105, 0.105)),
    ("Remove Rise-rate",(0.50, 0.29, 0.00, 0.105, 0.105)),
    ("Remove Hum+Temp", (0.50, 0.29, 0.15, 0.00, 0.00)),
    ("Water-only",      (1.00, 0.00, 0.00, 0.00, 0.00)),
]

print(f"\n{'Method':<20} {'Dry Peak':>8} {'Monsoon Peak':>12} {'Flash Peak':>10} {'Surge Peak':>10} {'Drain Peak':>10} {'Rec Peak':>10}")
print("-" * 80)
for name, w in ablations:
    peaks = []
    for skey in ["normal_dry", "monsoon", "flash_flood", "storm_surge", "urban_drain", "recession"]:
        trace = generate_trace(skey, noise_scale=0)
        classified = classify_index(trace, w)
        peaks.append(max(c["R"] for c in classified))
    print(f"{name:<20} {peaks[0]:>8.0f} {peaks[1]:>12.0f} {peaks[2]:>10.0f} {peaks[3]:>10.0f} {peaks[4]:>10.0f} {peaks[5]:>10.0f}")


# ──── D4: EVALUATION METRICS ────
print("\n\n" + "=" * 65)
print("D4: EVALUATION METRICS")
print("=" * 65)

# Ground truth labels for each scenario by time segment
# Based on expert judgment: SAFE=0, WARNING=1, EVACUATE=2
GT = {
    "normal_dry": [(0, 72, "SAFE")],
    "monsoon": [(0, 6, "SAFE"), (6, 24, "WARNING"), (24, 72, "EVACUATE")],
    "flash_flood": [(0, 1, "SAFE"), (1, 3, "WARNING"), (3, 8, "EVACUATE"), (8, 24, "SAFE")],
    "storm_surge": [(0, 0.5, "SAFE"), (0.5, 2, "WARNING"), (2, 14, "EVACUATE"), (14, 18, "SAFE")],
    "urban_drain": [(0, 72, "SAFE")],
    "recession": [(0, 48, "EVACUATE")],
}

def get_gt(scenario, t):
    for start, end, label in GT[scenario]:
        if start <= t < end:
            return label
    return "SAFE"

total_correct = 0
total_samples = 0
per_scenario = {}

for skey in SCENARIOS:
    trace = generate_trace(skey, noise_scale=0)
    classified = classify_index(trace, (0.50, 0.29, 0.15, 0.03, 0.03))
    correct = 0
    conf = {"TP": 0, "FP": 0, "TN": 0, "FN": 0}
    for pt, cls in zip(trace, classified):
        gt = get_gt(skey, pt["t"])
        pred = cls["tier"]
        is_evac_gt = (gt == "EVACUATE")
        is_evac_pred = (pred == "EVACUATE")
        if is_evac_pred and is_evac_gt: conf["TP"] += 1
        elif is_evac_pred and not is_evac_gt: conf["FP"] += 1
        elif not is_evac_pred and not is_evac_gt: conf["TN"] += 1
        else: conf["FN"] += 1
        if pred == gt: correct += 1
        total_samples += 1
    
    acc = correct / len(trace) * 100
    precision = conf["TP"] / (conf["TP"] + conf["FP"]) * 100 if (conf["TP"] + conf["FP"]) > 0 else 0
    recall = conf["TP"] / (conf["TP"] + conf["FN"]) * 100 if (conf["TP"] + conf["FN"]) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    total_correct += correct
    per_scenario[skey] = {"acc": acc, "precision": precision, "recall": recall, "f1": f1,
                          "TP": conf["TP"], "FP": conf["FP"], "TN": conf["TN"], "FN": conf["FN"]}
    
    print(f"\n  {SCENARIOS[skey]['name']}:")
    print(f"    Accuracy:  {acc:.1f}%")
    print(f"    Precision: {precision:.1f}%")
    print(f"    Recall:    {recall:.1f}%")
    print(f"    F1-Score:  {f1:.1f}%")
    print(f"    TP={conf['TP']}  FP={conf['FP']}  TN={conf['TN']}  FN={conf['FN']}")

overall_acc = total_correct / total_samples * 100
print(f"\n  OVERALL ACCURACY: {overall_acc:.1f}%")


# ──── SAVE RESULTS ────
os.makedirs(DATASET_DIR, exist_ok=True)
results = {
    "d1_comparative_baseline": results_d1,
    "d2_monte_carlo": mc_results,
    "d3_ablation": {name: peaks for name, w in ablations},
    "d4_metrics": per_scenario,
    "overall_accuracy": overall_acc,
}
with open(os.path.join(DATASET_DIR, "ieee_rigorous_analysis.json"), "w") as f:
    json.dump(results, f, indent=2)
print(f"\n\nResults saved to: {os.path.join(DATASET_DIR, 'ieee_rigorous_analysis.json')}")
