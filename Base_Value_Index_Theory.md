# Composite Flood Risk Index: Base Value Theory
## Scientific Foundation for Default Weights and Thresholds

### Version 1.0 | June 2026 | CSE331L.7 — North South University

---

## 1. Introduction

The Smart Flood Early Warning System uses a Composite Flood Risk Index (CFRI) defined as:

**R = 0.50 W + 0.29 S + 0.15 RR + 0.03 H + 0.03 T**

This document provides the complete scientific derivation of each default weight and threshold value, citing peer-reviewed literature, authoritative engineering handbooks, and government agency data.

---

## 2. Water Level Weight: w = 0.50 (50%)

### 2.1 Theoretical Justification

Water level is the **most direct and immediate measure of flood hazard**. Unlike precursor indicators (soil moisture, humidity) or derivative indicators (rise rate), water level measures the physical threat itself: the depth of water that can cause property damage, infrastructure disruption, and loss of life.

### 2.2 Supporting Citations

| Source | Relevance |
|--------|-----------|
| USDA-NRCS National Engineering Handbook (2004) | Establishes water depth as the primary variable in flood damage estimation curves |
| Zeng et al. (2025) IEEE YAC | Uses STM32+FMCW radar for direct water level measurement; water level is their sole primary sensor input |
| Shui et al. (2022) Sensors, 22(3), 1236 | FMCW radar waterlogging sensor; water depth is the core measured parameter |
| Sulistyowati et al. (2017) AIP Conf. Proc. 1855 | Ultrasonic sensor-based flood early warning; water level is the primary detected variable |
| Izzil Haq et al. (2024) engrXiv | Wireless flood EWS combining ultrasonic + water level sensors |

### 2.3 Threshold Derivation

The defaults assume a typical canal/drain scenario in urban Bangladesh:
- **SAFE threshold (WL < 10 cm)**: Normal dry-season water level, no action needed
- **EVACUATE threshold (WL >= 40 cm)**: Depth at which pedestrian movement becomes dangerous; based on flood damage studies showing 30-50 cm water depth causes significant hazard

**Data reference**: FFWC/BWDB historical station data for Dhaka canals (SW-265, SW-266) shows dry-season base levels of 2-8 cm and flood-stage levels exceeding 50 cm during monsoon.

---

## 3. Soil Saturation Weight: w = 0.29 (29%)

### 3.1 Theoretical Justification

Soil saturation is the **second most important factor** because it determines the runoff generation potential of the local ground. The relationship between antecedent soil moisture and flood generation is formalized by the **Soil Conservation Service Curve Number (SCS-CN) method** (USDA-NRCS, 2004), which classifies Antecedent Moisture Conditions (AMC) into three classes:

| AMC Class | Condition | 5-Day Antecedent Rainfall (mm) | Runoff Potential |
|-----------|-----------|-------------------------------|------------------|
| AMC I | Dry | < 12.7 (dormant) / < 35.6 (growing) | Low |
| AMC II | Normal | 12.7-27.9 (dormant) / 35.6-53.3 (growing) | Medium |
| AMC III | Wet | > 27.9 (dormant) / > 53.3 (growing) | High |

Under AMC III (wet soil), the Curve Number increases by approximately 15-30 points compared to AMC II, resulting in **2-3 times more runoff** for the same rainfall event.

### 3.2 Supporting Citations

| Source | Key Finding |
|--------|-------------|
| **USDA-NRCS (2004) National Engineering Handbook Part 630** | SCS-CN method: AMC directly modulates runoff curve number by 15-30 points |
| **Hassini & Guo (2020) J. Hydrology, 585, 124713** | Saturation-excess runoff is a dominant mechanism in urban flood frequency |
| **Tangdamrongsub (2021) Natural Hazards, 109, 2489-2510** | Satellite soil moisture (SMAP, SMOS) anomalies correlate significantly with flood occurrence. Thailand 2011 Great Flood validation. |
| **Verma et al. (2020) J. Hydrology, 585, 125114** | Activation Soil Moisture Accounting (ASMA) for runoff estimation using SCS-CN method |
| **Assouline et al. (2024) Advances in Water Resources** | Role of antecedent soil moisture in runoff generation in semiarid environments |

### 3.3 Default Value Justification

- **Dry soil (15-25%)**: Normal dry season conditions; runoff generation is minimal
- **Moderate soil (35-50%)**: Transitional; soil is approaching saturation; runoff begins to increase significantly
- **Wet soil (60-85%)**: Near-saturated to saturated; rainfall becomes surface runoff immediately; flood risk amplified

The weight of 0.29 is set so that saturated soil alone contributes approximately 29 points to the risk index, which is enough to push the index from SAFE toward WARNING even without significant water level change. This models the real-world phenomenon where pre-saturated ground accelerates flooding.

---

## 4. Rise Rate Weight: w = 0.15 (15%)

### 4.1 Theoretical Justification

Water level rise rate captures the **urgency dimension** of flood hazard. A rapid rate of rise indicates a flash-flood scenario requiring immediate evacuation, while a slow rise allows more lead time. This parameter differentiates between:
- **Slow seepage**: ~0.1-0.5 cm/h (manageable, longer lead time)
- **Moderate rise**: ~1-3 cm/h (typical monsoon river rise)
- **Flash flood**: >5 cm/h (emergency evacuation required)

### 4.2 Supporting Citations

| Source | Key Finding |
|--------|-------------|
| **Kim & Choi (2014) J. Flood Risk Management, 7(4), 344-356** | Modified Flash Flood Index (MFFI) incorporates rate of water-level rise as a key severity parameter |
| **Guo et al. (2026) J. Flood Risk Management** | Flash Flood Risk Index is validated as an early warning signal; rate of change is critical |
| **Zeng et al. (2025) IEEE YAC** | STM32-based system computes rise rate at 500ms intervals for prediction |

### 4.3 Default Normalization

|Rise rate (RR) is normalized via a **least-squares trend engine** with noise deadband:

1. A ring buffer of the last N=40 water-level readings is maintained
2. Linear regression (least-squares) is computed over this window
3. The slope is converted to cm/h: `v = slope * 3600`
4. Rise rate only contributes if:
   - The net water-level rise over the window exceeds 1.5 cm (noise floor)
   - The absolute slope exceeds 1.0 cm/h (noise deadband)
   - The water level is above the SAFE threshold ( > 10 cm)

The normalised score is:
```
RR_score = min(100, max(0, 100 * v / V_max))
```
where `V_max = 5.0 cm/h` represents an extreme flash flood rate. Under normal monsoon conditions (v ≈ 1.2 cm/h), RR contributes approximately 3.6 points. During flash flood conditions (v = 8 cm/h, clipped to V_max = 5 cm/h), the contribution reaches the full 15 points.

---

## 5. Humidity Weight: w = 0.03 (3%)

### 5.1 Theoretical Justification

Relative humidity serves as a **supporting meteorological indicator** of ongoing or imminent precipitation. High humidity (>80%) combined with warm temperatures creates conditions conducive to convective rainfall, which can trigger flash floods. The low weight reflects:

1. Humidity is a **precursor indicator**, not a direct hazard measure
2. The DHT11 sensor has ±5% accuracy, limiting quantitative precision
3. Humidity alone cannot determine flood risk without water level data

### 5.2 Default Value

- **Normal (45-65%)**: No additional risk
- **High (65-80%)**: Marginal contribution
- **Very high (80-95%)**: Active contribution begins
- **Saturation (95-100%)**: Maximum contribution

### 5.3 Citation

| Source | Relevance |
|--------|-----------|
| Tao et al. (2024) Sensors, 24(21), 7090 | Review confirms environmental sensors (including humidity) contribute to multi-sensor flood monitoring |
| Rohan et al. (2025) IoTCC, 13(1) | SentryLeaf includes humidity as part of environmental monitoring suite |

---

## 6. Temperature Weight: w = 0.03 (3%)

### 6.1 Theoretical Justification

Temperature is the **lowest weighted parameter** because:
1. Direct correlation with immediate flood risk is weak
2. Temperature primarily affects **evapotranspiration rates** and **snowmelt** (irrelevant in Bangladesh)
3. High temperatures can indicate thunderstorm potential (convective rainfall)

The weight acknowledges temperature's role in the overall environmental context while ensuring it does not dominate the risk calculation.

### 6.2 Citation

| Source | Relevance |
|--------|-----------|
| Mdegela et al. (2023) Sensors, 23(8), 4055 | Multi-parameter monitoring includes temperature as supporting environmental data |
| Tao et al. (2024) Sensors, 24(21), 7090 | Background environmental parameters are part of comprehensive flood monitoring |

---

## 7. Alert Thresholds with Hysteresis

### 7.1 Default Thresholds

| Tier | Risk Index Range | Visual | Audio | Conditions |
|------|-----------------|--------|-------|------------|
| **SAFE** | R < 40 | Green LED | Silent | No action needed |
| **WARNING** | 40 <= R < 75 | Yellow LEDs | 2 Hz beep | Prepare for evacuation |
| **EVACUATE** | R >= 75 | Red LEDs blink | 8 Hz continuous | Evacuate immediately |

### 7.2 Hysteresis Deadbands

Hysteresis prevents false oscillation between tiers:

| Transition | Ascending threshold | Descending threshold |
|-----------|-------------------|---------------------|
| SAFE <-> WARNING | R >= 40 | R <= 35 |
| WARNING <-> EVACUATE | R >= 75 | R <= 70 |

This ±5 point deadband is a standard control systems technique adapted from Schmitt trigger circuits. It is consistent with the recommendation that "hysteresis prevents false oscillation between adjacent tiers" in embedded sensor fusion applications (Zeng et al., 2025).

The least-squares trend engine provides an additional **predictive boost**: if the recent risk-index slope exceeds a threshold, the alert is promoted by one tier. This is derived from:
- **Kim & Choi (2014)**: MFFI includes rate of change as a severity parameter
- **Guo et al. (2026)**: Flash Flood Risk Index as early warning signal in ungauged basins

---

## 8. Default Values Summary Table

| Parameter | Symbol | Default | Rationale Source |
|-----------|--------|---------|------------------|
| Water level weight | w_W | 0.50 | Primary direct hazard (USDA-NRCS, 2004; Zeng et al., 2025) |
| Soil saturation weight | w_S | 0.29 | SCS-CN AMC modulation (USDA-NRCS, 2004; Tangdamrongsub, 2021) |
| Rise rate weight | w_RR | 0.15 | MFFI severity parameter (Kim & Choi, 2014; Guo et al., 2026) |
| Humidity weight | w_H | 0.03 | Supporting context (Tao et al., 2024; Rohan et al., 2025) |
| Temperature weight | w_T | 0.03 | Supporting context (Mdegela et al., 2023; Tao et al., 2024) |
| SAFE threshold | R_S | < 40 | Normal conditions, no alert needed |
| WARNING threshold | R_W | 40-74 | Action preparation (BWDB reference) |
| EVACUATE threshold | R_E | >= 75 | Immediate evacuation (BWDB flood stage) |
| Hysteresis band | H | ±5 points | Control theory (Schmitt trigger) |
| Dry soil baseline | S_dry | 15% | Dry season (FFWC station data) |
| Saturated soil | S_wet | 85% | Fully saturated (Tangdamrongsub, 2021) |
| VL_SAFE | D_safe | 10 cm | Normal canal level (BWDB data) |
|| VL_EVAC | D_evac | 40 cm | Danger depth for pedestrians |
| Max rise rate (cap) | V_max | 5.0 cm/h | Extreme flash flood (clipped) |
| Trend window | N | 40 samples | ~3.3 h at 300s; least-squares buffer |
| Rise-rate deadband | v_min | 1.0 cm/h | Below this, slope treated as noise |
| Net-rise threshold | Δh_min | 1.5 cm | Min. rise over window for valid trend |
| Rise-rate activation | -- | Only if water > D_safe | Prevents noise at safe levels |

---

## 9. References

1. USDA-NRCS. "National Engineering Handbook: Part 630 -- Hydrology." U.S. Department of Agriculture, 2004.

2. Y. Zeng, D. Li, J. Zheng, Y. Zhang, and J. Sun. "Research and implementation of tunnel flooding early warning system based on FMCW millimeter-wave radar and STM32." Proc. 40th Youth Academic Annual Conference of Chinese Association of Automation (YAC), 2025. DOI: 10.1109/YAC66630.2025.11150218

3. H. Shui, H. Geng, Q. Li, L. Du, and Y. Du. "A low-power high-accuracy urban waterlogging depth sensor based on millimeter-wave FMCW radar." Sensors, vol. 22, no. 3, art. 1236, 2022. DOI: 10.3390/s22031236

4. N. Tangdamrongsub. "The analysis of using satellite soil moisture observations for flood detection, evaluating over the Thailand's Great Flood of 2011." Natural Hazards, vol. 109, pp. 2489-2510, 2021. DOI: 10.1007/s11069-021-04804-8

5. S. Hassini and Y. Guo. "Analytical derivation of urban flood frequency models accounting saturation-excess runoff generation." Journal of Hydrology, vol. 585, art. 124713, 2020. DOI: 10.1016/j.jhydrol.2020.124713

6. E. S. Kim and H. I. Choi. "Evaluation of flash flood severity in Korea using the modified flash flood index (MFFI)." Journal of Flood Risk Management, vol. 7, no. 4, pp. 344-356, 2014. DOI: 10.1111/jfr3.12057

7. D. Guo et al. "Can flash flood risk index be an early warning signal of flash floods in ungauged basin?" Journal of Flood Risk Management, 2026. DOI: 10.1111/jfr3.70176

8. Y. Tao, B. Tian, B. R. Adhikari, Q. Zuo, X. Luo, and B. Di. "A review of cutting-edge sensor technologies for improved flood monitoring and damage assessment." Sensors, vol. 24, no. 21, art. 7090, 2024. DOI: 10.3390/s24217090

9. M. R. R. Rohan, M. A. Khatun, M. A. Rahman, and A. Pathak. "Enhancing flood disaster response through real-time monitoring and IoT: The case of SentryLeaf." Internet of Things and Cloud Computing, vol. 13, no. 1, pp. 1-14, 2025. DOI: 10.11648/j.iotcc.20251301.11

10. R. Sulistyowati et al. "Design and field test equipment of river water level detection based on ultrasonic sensor and SMS gateway as flood early warning." AIP Conference Proceedings, vol. 1855, art. 040016, 2017. DOI: 10.1063/1.4985517

11. M. Izzil Haq et al. "Wireless flood early warning system for high-density population areas by combining ultrasonic and water level sensors." engrXiv, 2024. DOI: 10.31224/7096

12. L. Mdegela et al. "A multi-modal wireless sensor system for river monitoring: A case for Kikuletwa River floods in Tanzania." Sensors, vol. 23, no. 8, art. 4055, 2023. DOI: 10.3390/s23084055

13. E. A. Basha, S. Ravela, and D. Rus. "Model-based monitoring for early warning flood detection." Proc. 6th ACM Conference on Embedded Network Sensor Systems (SenSys), pp. 295-308, 2008. DOI: 10.1145/1460412.1460442

14. Z. Boulouard et al. "An integrated artificial intelligence of things environment for river flood prevention." Sensors, vol. 22, no. 23, art. 9485, 2022. DOI: 10.3390/s22239485

15. R. K. Verma et al. "Activation soil moisture accounting (ASMA) for runoff estimation using soil conservation service curve number (SCS-CN) method." Journal of Hydrology, vol. 585, art. 125114, 2020. DOI: 10.1016/j.jhydrol.2020.125114

16. S. Assouline et al. "Runoff generation in a semiarid environment: The role of rainstorm intra-event temporal variability and antecedent soil moisture." Advances in Water Resources, 2024. DOI: 10.1016/j.advwatres.2024.104715

17. Bangladesh Water Development Board. "Annual Flood Report 2022." Ministry of Water Resources, Government of Bangladesh, 2022.

18. STMicroelectronics. "STM32F103x8/xB Datasheet." DS5319, Rev. 17, 2021.

---

*Document prepared for CSE331L.7 Embedded Systems Laboratory, North South University, June 2026.*
