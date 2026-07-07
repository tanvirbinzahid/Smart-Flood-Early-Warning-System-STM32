# Simulation Scripts — Smart Flood EWS

This directory contains all scripts used to generate simulation data and analysis results for the STM32-based Smart Flood Early Warning System.

## Scripts

| Script | Purpose | Paper Reference |
|--------|---------|-----------------|
| `generate_data.py` | Generates synthetic flood scenario traces (7 scenarios, CSV datasets) | §7.2–7.3 |
| `generate_plots.py` | Generates scenario response figures (time-series plots) | §7.4–7.5 |
| `generate_hw_plots.py` | Generates hardware accuracy characterisation figures | §7.1 |
| `generate_ffwc_plots.py` | Generates FFWC historical timeline figures | §7.6 |
| `ieee_rigorous_analysis.py` | D1–D2: Comparative baseline study + Monte Carlo robustness (N=100) | §8, §9 |
| `rigorous_analysis.py` | D3–D4: Ablation study + evaluation metrics | §10, §11 |
| `fetch_usgs_data.py` | Fetches USGS water level data for 3 flood events | §8.3 |
| `fetch_terraclimate_data.py` | Fetches TerraClimate soil moisture data for US stations | §8.3 |

## Datasets (in `datasets/`)

| File | Contents | Script |
|------|----------|--------|
| `normal_dry.csv` | Normal dry season (864 samples, 300s interval) | `generate_data.py` |
| `monsoon_gradual.csv` | Monsoon gradual rise (864 samples) | `generate_data.py` |
| `flash_flood.csv` | Flash flood scenario (1440 samples, 60s interval) | `generate_data.py` |
| `coastal_storm_surge.csv` | Storm surge with pre-saturated soil (540 samples) | `generate_data.py` |
| `urban_drain_overload.csv` | Urban drain with tidal + rainfall (576 samples) | `generate_data.py` |
| `post_flood_recession.csv` | Post-flood recession (576 samples) | `generate_data.py` |
| `ieee_rigorous_analysis.json` | D1–D2 results (comparative baseline + Monte Carlo) | `ieee_rigorous_analysis.py` |
| `rigorous_analysis.json` | D3–D4 results (ablation + metrics) | `rigorous_analysis.py` |

## Usage

```bash
# Generate scenario data
python scripts/generate_data.py

# Generate all figures
python scripts/generate_plots.py

# Run comparative baseline + Monte Carlo
python scripts/ieee_rigorous_analysis.py

# Run ablation + metrics
python scripts/rigorous_analysis.py

# Fetch external validation data
python scripts/fetch_usgs_data.py
python scripts/fetch_terraclimate_data.py
```

All scripts run from the `Simulation_Data/` directory. Output datasets go to `scripts/datasets/`, figures to `figures/`.

## Reproducibility

All stochastic runs use a **fixed random seed** (`random.seed(42)` in Python, `np.random.seed(42)` in NumPy-based scripts) so that every noise realisation is exactly reproducible. The seed is set at the top of each script that uses randomness:

| Script | Seed | Source of randomness |
|--------|------|---------------------|
| `generate_data.py` | `random.seed(42)` | Sensor noise (water level, soil moisture) |
| `generate_hw_plots.py` | `np.random.seed(42)` | Monte Carlo noise for hardware accuracy |
| `ieee_rigorous_analysis.py` | `random.seed(42)` | Monte Carlo N=100 noise realisations |
| `rigorous_analysis.py` | `random.seed(42)` | (Deterministic — seed included for consistency) |

Running any script twice with the same seed produces identical outputs. This is verified by the JSON hash checksums in the `datasets/` directory.

## Dependencies

- Python 3.8+ (stdlib only for data generation and analysis scripts)
- matplotlib (for plot generation)
- No external API keys required (USGS and TerraClimate are free, anonymous, no login)
