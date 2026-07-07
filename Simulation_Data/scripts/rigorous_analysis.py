#!/usr/bin/env python3
"""
Rigorous analysis for HardwareX paper:
  D3: Ablation study — remove each term, report tier mismatches + mean |ΔR|
  D4: Evaluation metrics — accuracy, precision/recall/F1 per scenario

Output: datasets/rigorous_analysis.json

Run:  python rigorous_analysis.py
"""
import json, math, random, os

random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "datasets")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Normalization helpers ──
D_SAFE, D_EVAC = 10.0, 40.0

def norm_water(water_cm):
    if water_cm <= D_SAFE: return 0
    if water_cm >= D_EVAC: return 100
    return 100 * (water_cm - D_SAFE) / (D_EVAC - D_SAFE)

def norm_soil(soil_pct):
    return min(100, max(0, soil_pct))

def norm_rise(rise_cmh):
    return min(100, max(0, 100 * rise_cmh / 5.0))

def norm_hum(hum_pct):
    return min(100, max(0, 100 * (hum_pct - 60) / 35))

def compute_risk(water_cm, rise_cmh, soil_pct, hum_pct, weights):
    w_w, w_s, w_rr, w_h, _ = weights
    R = w_w * norm_water(water_cm) + w_s * norm_soil(soil_pct) \
        + w_rr * norm_rise(rise_cmh) + w_h * norm_hum(hum_pct)
    return R

def classify(R):
    return "EVACUATE" if R >= 75 else ("WARNING" if R >= 40 else "SAFE")

# ── Scenario definitions ──
SCENARIOS = {
    "normal_dry": {
        "name": "Normal Dry", "n": 864, "dt": 300,
        "func": lambda t: (5.0, 0.1, 15, 45),
        "gt": [(0, 72, "SAFE")],
    },
    "monsoon": {
        "name": "Monsoon Gradual", "n": 864, "dt": 300,
        "func": lambda t: (
            8.0 + max(0, min(42, 1.2 * max(0, t-6))),
            1.2 if 6 < t < 42 else 0,
            35 + 65 * min(1, max(0, t-6)/36),
            78 + 20 * min(1, max(0, t-6)/36)),
        "gt": [(0, 6, "SAFE"), (6, 24, "WARNING"), (24, 72, "EVACUATE")],
    },
    "flash_flood": {
        "name": "Flash Flood", "n": 1440, "dt": 60,
        "func": lambda t: (
            5.0 + max(0, min(40, 8.0 * max(0, t-1))),
            8.0 if 1 < t < 7 else 0,
            60 + 35 * min(1, max(0, t-1)/5),
            92),
        "gt": [(0, 1, "SAFE"), (1, 3, "WARNING"), (3, 8, "EVACUATE"), (8, 24, "SAFE")],
    },
    "storm_surge": {
        "name": "Storm Surge", "n": 540, "dt": 120,
        "func": lambda t: (
            10.0 + min(30, 7.5 * max(0, t)) if t < 4 else 40.0,
            7.5 if t < 4 else 0,
            85, 95),
        "gt": [(0, 0.5, "SAFE"), (0.5, 2, "WARNING"), (2, 14, "EVACUATE"), (14, 18, "SAFE")],
    },
    "urban_drain": {
        "name": "Urban Drain", "n": 576, "dt": 300,
        "func": lambda t: (
            6.0 + 3.0 * math.sin(2 * math.pi * t / 12.4) + (3.5 if 4 < t < 12 else 0),
            0.5 if 4 < t < 12 else 0,
            50, 82),
        "gt": [(0, 72, "SAFE")],
    },
    "recession": {
        "name": "Recession", "n": 576, "dt": 300,
        "func": lambda t: (max(5, 45 - 0.8 * t), -0.8, 70, 75),
        "gt": [(0, 6, "EVACUATE"), (6, 24, "WARNING"), (24, 48, "SAFE")],
    },
}

def get_gt(skey, t):
    for start, end, label in SCENARIOS[skey]["gt"]:
        if start <= t < end:
            return label
    return "SAFE"

def generate_trace(skey, noise=0):
    s = SCENARIOS[skey]
    trace = []
    for i in range(s["n"]):
        t = i * s["dt"] / 3600
        wl, rr, soil, hum = s["func"](t)
        if noise:
            wl += random.gauss(0, 1.5 * noise)
            soil += random.gauss(0, 5 * noise)
            hum += random.gauss(0, 5 * noise)
        trace.append({"t": t, "wl": max(0, wl), "rr": max(0, rr),
                      "soil": max(0, min(100, soil)),
                      "hum": max(0, min(100, hum))})
    return trace

def classify_trace(trace, weights):
    return [{"R": compute_risk(pt["wl"], pt["rr"], pt["soil"], pt["hum"], weights),
             "tier": classify(compute_risk(pt["wl"], pt["rr"], pt["soil"], pt["hum"], weights))}
            for pt in trace]

# ── Generate all traces ──
FULL = (0.50, 0.29, 0.15, 0.03, 0.03)
traces = {skey: generate_trace(skey) for skey in SCENARIOS}
full_results = {skey: classify_trace(traces[skey], FULL) for skey in SCENARIOS}

# ═══════════════════════════════════════════════
# D3: ABLATION STUDY
# ═══════════════════════════════════════════════
ABLATIONS = [
    ("Full index",       (0.50, 0.29, 0.15, 0.03, 0.03)),
    ("Remove Water",     (0.00, 0.58, 0.30, 0.06, 0.06)),
    ("Remove Soil",      (0.50, 0.00, 0.29, 0.105, 0.105)),
    ("Remove Rise-rate", (0.50, 0.29, 0.00, 0.105, 0.105)),
    ("Remove Hum+Temp",  (0.50, 0.29, 0.15, 0.00, 0.00)),
    ("Water-only",       (1.00, 0.00, 0.00, 0.00, 0.00)),
]

ablation_data = {}
for name, weights in ABLATIONS:
    total_mismatch = 0
    total_n = 0
    total_dr = 0
    tier_scenarios = set()
    per_scenario = {}

    for skey in SCENARIOS:
        results = classify_trace(traces[skey], weights)
        n = len(results)
        mismatches = sum(1 for r, f in zip(results, full_results[skey]) if r["tier"] != f["tier"])
        dr = sum(abs(r["R"] - f["R"]) for r, f in zip(results, full_results[skey])) / n
        total_mismatch += mismatches
        total_n += n
        total_dr += dr * n
        if mismatches > 0:
            tier_scenarios.add(skey)
        per_scenario[skey] = {
            "mismatches": mismatches,
            "mean_abs_dr": round(dr, 2),
            "peak_r": max(r["R"] for r in results),
        }

    ablation_data[name] = {
        "mismatches": f"{total_mismatch}/{total_n}",
        "pct_mismatch": round(100 * total_mismatch / total_n, 1),
        "mean_abs_dr": round(total_dr / total_n, 2),
        "scenarios_tier_changed": len(tier_scenarios),
        "per_scenario": per_scenario,
    }

print("D3: ABLATION STUDY")
print(f"{'Method':<20} {'Mismatches':>12} {'Mean |DR|':>10} {'Tiers changed':>14}")
for name, w in ABLATIONS:
    a = ablation_data[name]
    print(f"{name:<20} {a['mismatches']:>12} {a['mean_abs_dr']:>10.2f} {a['scenarios_tier_changed']:>4}")

# ═══════════════════════════════════════════════
# D4: EVALUATION METRICS
# ═══════════════════════════════════════════════
metrics_data = {}
overall = {"correct": 0, "total": 0, "TP": 0, "FP": 0, "TN": 0, "FN": 0}

for skey in SCENARIOS:
    results = full_results[skey]
    trace = traces[skey]
    sname = SCENARIOS[skey]["name"]

    correct = 0
    conf = {"TP": 0, "FP": 0, "TN": 0, "FN": 0}

    for pt, cls in zip(trace, results):
        gt = get_gt(skey, pt["t"])
        pred = cls["tier"]
        if pred == gt:
            correct += 1
        overall["total"] += 1
        # EVACUATE detection (binary EVAC vs non-EVAC)
        if pred == "EVACUATE" and gt == "EVACUATE":
            conf["TP"] += 1
        elif pred == "EVACUATE" and gt != "EVACUATE":
            conf["FP"] += 1
        elif pred != "EVACUATE" and gt != "EVACUATE":
            conf["TN"] += 1
        else:
            conf["FN"] += 1

    overall["correct"] += correct
    overall["TP"] += conf["TP"]
    overall["FP"] += conf["FP"]
    overall["TN"] += conf["TN"]
    overall["FN"] += conf["FN"]

    acc = correct / len(trace) * 100
    prec = conf["TP"] / (conf["TP"] + conf["FP"]) * 100 if conf["TP"] + conf["FP"] else 0
    rec = conf["TP"] / (conf["TP"] + conf["FN"]) * 100 if conf["TP"] + conf["FN"] else 0
    f1 = 2*prec*rec/(prec+rec) if prec+rec else 0
    spec = conf["TN"] / (conf["TN"] + conf["FP"]) * 100 if conf["TN"] + conf["FP"] else 0

    # Lead times
    tw = te = None
    prev = results[0]["tier"]
    for i, r in enumerate(results):
        if r["tier"] != prev:
            if r["tier"] == "WARNING" and tw is None:
                tw = trace[i]["t"]
            if r["tier"] == "EVACUATE" and te is None:
                te = trace[i]["t"]
            prev = r["tier"]

    metrics_data[skey] = {
        "scenario": sname,
        "n_samples": len(trace),
        "accuracy_pct": round(acc, 1),
        "evac_precision_pct": round(prec, 1),
        "evac_recall_pct": round(rec, 1),
        "evac_f1_pct": round(f1, 1),
        "specificity_pct": round(spec, 1),
        "t_warn_h": round(tw, 2) if tw else None,
        "t_evac_h": round(te, 2) if te else None,
        "confusion_evac": conf,
    }

# ── Save ──
output = {
    "d3_ablation": ablation_data,
    "d4_metrics": metrics_data,
    "overall": {
        "accuracy_pct": round(overall["correct"] / overall["total"] * 100, 1),
        "evac_precision_pct": round(overall["TP"] / (overall["TP"] + overall["FP"]) * 100, 1)
            if overall["TP"] + overall["FP"] else 0,
        "evac_recall_pct": round(overall["TP"] / (overall["TP"] + overall["FN"]) * 100, 1)
            if overall["TP"] + overall["FN"] else 0,
        "evac_f1_pct": round(
            2 * (overall["TP"]/(overall["TP"]+overall["FP"])) * (overall["TP"]/(overall["TP"]+overall["FN"]))
            / ((overall["TP"]/(overall["TP"]+overall["FP"])) + (overall["TP"]/(overall["TP"]+overall["FN"]))) * 100, 1)
            if overall["TP"]+overall["FP"] and overall["TP"]+overall["FN"] else 0,
        "total_TP": overall["TP"], "total_FP": overall["FP"],
        "total_TN": overall["TN"], "total_FN": overall["FN"],
    },
}

path = os.path.join(OUTPUT_DIR, "rigorous_analysis.json")
with open(path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\nResults saved to: {path}")
