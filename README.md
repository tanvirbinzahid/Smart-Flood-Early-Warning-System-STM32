
<p align="center">
  <img src="https://img.shields.io/badge/STM32-F103C8-blue?style=for-the-badge&logo=arm&logoColor=white"/>
  <img src="https://img.shields.io/badge/Language-C-00599C?style=for-the-badge&logo=c&logoColor=white"/>
  <img src="https://img.shields.io/badge/IDE-STM32CubeIDE-red?style=for-the-badge&logo=eclipse&logoColor=white"/>
  <img src="https://img.shields.io/badge/Status-Operational-brightgreen?style=for-the-badge"/>
</p>

<h1 align="center">🌊 Smart Flood Early Warning System</h1>

<p align="center">
  <b>A real-time embedded flood monitoring and alert system built on the STM32F103C8T6 (Blue Pill)</b><br>
  Integrating ultrasonic sensing, environmental monitoring, soil moisture analysis, and multi-tier alerting
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#features">Features</a> •
  <a href="#system-architecture">Architecture</a> •
  <a href="#hardware--pinout">Pinout</a> •
  <a href="#risk-index-algorithm">Algorithm</a> •
  <a href="#keypad-controls">Controls</a> •
  <a href="#project-structure">Structure</a> •
  <a href="#building--flashing">Build</a> •
  <a href="#paper">Paper</a>
</p>

---

<a name="overview"></a>
## 📋 Overview

This project implements a **Smart Flood Early Warning System** using the STM32F103C8T6 microcontroller. It continuously monitors water levels via ultrasonic sensing, environmental conditions via DHT11, and soil moisture via an ADC sensor. A **composite Risk Index (0-100)** is computed in real-time and drives a 3-tier alert system (SAFE → WARNING → EVACUATE) with visual (LEDs, OLED) and audible (buzzer) outputs, all controllable via a 4x4 matrix keypad.

---

<a name="features"></a>
## ✨ Features

| # | Feature | Detail |
|---|---------|--------|
| 1 | **📏 Ultrasonic Water Level** | HC-SR04 with 5-sample median filter + 8-sample moving average |
| 2 | **🌡️ Environmental Sensing** | DHT11 temperature & humidity with CRC validation |
| 3 | **🪴 Soil Moisture** | ADC on PA0 with 8-sample moving average |
| 4 | **📊 Risk Index Engine** | Weighted composite: 55% water + 31% soil + 7% rise rate + 5% humidity + 2% temp |
| 5 | **🚦 3-Tier Alert** | SAFE 🟢 → WARNING 🟡 → EVACUATE 🔴 with LED patterns |
| 6 | **🔊 Audible Alarm** | Buzzer with configurable interval (500ms warning / 125ms evacuate) + mute toggle |
| 7 | **🖥️ OLED Display** | 128×64 SSD1306 I2C with 4 switchable pages + inverted danger theme |
| 8 | **⌨️ Keypad Control** | 4×4 matrix keypad for full system interaction |
| 9 | **⚡ Sensitivity Tuning** | Adjustable SYS_SEN (1-10) for deadband / responsiveness |
| 10 | **📈 Session Statistics** | Min/max tracking for water level, rise rate, and risk index |
| 11 | **🔋 Power Save Mode** | Auto-enter after 1 hour of stable SAFE conditions |
| 12 | **🔄 Rise Rate Detection** | Calculates water level velocity (cm/s) for trend awareness |

---

<a name="system-architecture"></a>
## 🏗️ System Architecture

```mermaid
graph TB
    subgraph Sensors
        A[HC-SR04<br/>Ultrasonic] -->|PA2 TRIG/PA3 ECHO| B[STM32F103C8T6<br/>72 MHz ARM Cortex-M3]
        C[DHT11<br/>Temp & Humidity] -->|PA1| B
        D[Soil Moisture<br/>ADC] -->|PA0 ADC1_IN0| B
        E[4×4 Keypad] -->|PB8-PB15| B
    end

    subgraph Processing
        B --> F[Median Filter<br/>5-sample]
        F --> G[Moving Average<br/>8-sample]
        G --> H[Risk Index<br/>Weighted 0-100]
        H --> I[Tier Classification]
    end

    subgraph Outputs
        I --> J[OLED SSD1306<br/>I2C PB6/PB7]
        I --> K[5-LED Bar<br/>PA5-PA9]
        I --> L[Buzzer<br/>PB0]
    end

    style A fill:#4a90d9,color:#fff
    style C fill:#f5a623,color:#fff
    style D fill:#7ed321,color:#fff
    style E fill:#d0021b,color:#fff
    style B fill:#333,color:#fff,stroke:#fff,stroke-width:2px
    style J fill:#9013fe,color:#fff
    style K fill:#f8e71c,color:#333
    style L fill:#f5a623,color:#fff
```

### Sensor Fusion Pipeline

```
HC-SR04 ──► Median(5) ──► MovingAvg(8) ──► Deadband Filter ──┐
DHT11   ──► CRC Check   ──────────────────────────────────────┤
Soil    ──► MovingAvg(8) ─────────────────────────────────────┤
                                                               ▼
                                                      RISK INDEX
                                                     0.55×WL + 0.31×Soil
                                                     0.07×RR + 0.05×Hum
                                                     0.02×Temp
                                                         │
                                                         ▼
                                          ┌──────────┴──────────┐
                                          │  < 40     40-74   ≥ 75 │
                                          │  SAFE   WARNING EVACUATE│
                                          └────────────────────────┘
```

---

<a name="hardware--pinout"></a>
## 🧩 Hardware & Pinout

<p align="center">
  <img src="assets/circuit-breadboard.png" alt="Circuit Diagram on Breadboard" width="700"/>
  <br/>
  <em>Full system assembled on breadboard — STM32F103C8T6 with HC-SR04, DHT11, soil moisture sensor, OLED, keypad, LEDs, and buzzer</em>
</p>

| Component | Pin | Function |
|-----------|-----|----------|
| **HC-SR04 TRIG** | PA2 | Ultrasonic trigger output |
| **HC-SR04 ECHO** | PA3 | Ultrasonic echo input |
| **DHT11 Data** | PA1 | Temperature/humidity data |
| **Soil Moisture** | PA0 | ADC1_IN0 analog input |
| **OLED SCL** | PB6 | I2C1 clock |
| **OLED SDA** | PB7 | I2C1 data |
| **Green LED** | PA5 | SAFE indicator |
| **Yellow LED 1** | PA6 | WARNING (low) |
| **Yellow LED 2** | PA7 | WARNING (high) |
| **Red LED 1** | PA8 | EVACUATE |
| **Red LED 2** | PA9 | EVACUATE |
| **Buzzer** | PB0 | Audible alarm |
| **Keypad Rows** | PB8-PB11 | 4×4 matrix rows |
| **Keypad Cols** | PB12-PB15 | 4×4 matrix columns |

### Hardware Bill of Materials

| Item | Quantity |
|------|----------|
| STM32F103C8T6 (Blue Pill) | 1 |
| HC-SR04 Ultrasonic Sensor | 1 |
| DHT11 Temp/Humidity Sensor | 1 |
| Soil Moisture Sensor (FC-28) | 1 |
| SSD1306 OLED 128×64 I2C | 1 |
| 4×4 Matrix Keypad | 1 |
| 5× LED (1G, 2Y, 2R) + 220Ω resistors | 5 |
| Active Buzzer (5V) | 1 |
| Breadboard + Jumper Wires | - |
| 8 MHz Crystal + 2×22pF caps | 1 set |
| 2× 100nF decoupling caps | 2 |

---

<a name="risk-index-algorithm"></a>
## ⚙️ Risk Index Algorithm

The composite Risk Index (0-100) is computed every 500ms:

```
wl_inv     = WL_SAFE_CM - water_level_cm          // Invert so lower water = higher risk
wl_s       = Scale(wl_inv, 0, WL_SAFE_CM - WL_EVAC_CM)
rr_s       = Scale(rise_rate_cms, 0, MAX_RISE_CMS)
hum_s      = Scale(humidity_pct, 60, 95)
tmp_s      = Scale(temperature_c, 25, 35)

risk_index = 0.55 × wl_s + 0.31 × soil_pct + 0.07 × rr_s + 0.05 × hum_s + 0.02 × tmp_s
```

### Tier Thresholds

```
SAFE     ──► Risk Index < 40   ──► Green LED ON
WARNING  ──► Risk Index 40-74  ──► Yellow LED(s) ON, buzzer every 500ms
EVACUATE ──► Risk Index ≥ 75   ──► Red LEDs flash, buzzer every 125ms
```

### Risk Index Visualization

```
Risk Bar (OLED mockup):

  0             40            75          100
  ├──────────────┼──────────────┼──────────┤
  │   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
  │   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
  │   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
  │░░░░░░░░░░░░│░░░░░░░░░░░░░░░░░░░░░░░░░░│
  │░░░░░░░░░░░░│░░░░░░░░░░░░░░░░░░░░░░░░░░│
  └──────────────┴──────────────┴──────────┘
    ██████████████░░░░░░░░░░░░░░░░░░░░░░░░
    ↑ Current RI  ↑ WARNING      ↑ EVACUATE
      (e.g., 22)    starts        starts
```

### Moving Average Performance

```
Water Level Readings (simulated):
cm
80 ┤╭────────────────────────────────────╮
   ││                                    │
60 ┤│        ╭──╮    Raw HC-SR04         │
   ││       ╭╯  ╰╮   After Median(5)+Avg(8)│
40 ┤│       │    ╰╮                       │
   ││      ╭╯     ╰╮                     │
20 ┤│     ╭╯       ╰╮                    │
   ││    ╭╯         ╰──╮                 │
 0 ┤╰────╯──────────────╰────────────────╯
   └───────────────────────────────────────▶
    0    10    20    30    40    50   time(s)
```

---

<a name="keypad-controls"></a>
## ⌨️ Keypad Controls

| Key | Function | Context |
|-----|----------|---------|
| **1** | Toggle buzzer mute | Any screen |
| **2** | Reset stats / System reset | Stats screen / Other screens |
| **3** | Swap OLED page (Main ↔ Sensors) | Any screen |
| **4** | Open statistics screen | Any screen |
| **5** | Decrease SYS_SEN (↓ sensitivity) | Any screen |
| **6** | Increase SYS_SEN (↑ sensitivity) | Any screen |
| **7** | (Reserved) | - |
| **8** | (Reserved) | - |
| **9** | (Reserved) | - |
| **0** | (Reserved) | - |
| ***\*** | Wake from power-save | Power-save mode |
| **#** | (Reserved) | - |

---

## 🖥️ OLED Pages

### Page 1: Main Summary
```
┌──────────────────────────┐
│    !! EVACUATE !!        │  ← Tier banner (flashes in danger)
│ WL:12.5cm R:3.20         │  ← Water level + rise rate
│ T:28.5C H:72%            │  ← DHT11 readings
│ SOIL: 45% RI: 82         │  ← Soil moisture + Risk Index
│ ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░ │  ← Risk bar graphic
│ SYS_SEN:05  3/4          │  ← Sensitivity + key hints
└──────────────────────────┘
```

### Page 2: All Sensors
```
┌──────────────────────────┐
│ DATA:EVACUATE S:05       │
│ WL:12.5cm                │
│ Rise:3.20cm/s            │
│ T:28.5C H:72%            │
│ Soil: 45% RI: 82         │
│ 5- 6+  4Stats            │
└──────────────────────────┘
```

### Page 3: Statistics
```
┌──────────────────────────┐
│ MIN/MAX  KEY 4           │
│ WL:3.2~82.1cm            │
│ RR:0.00~5.40             │
│ RI: 0 ~ 96 /100          │
│ T:26.0C H:55%            │
│ [3]Next [2]Reset         │
└──────────────────────────┘
```

---

<a name="project-structure"></a>
## 📁 Project Structure

```
Smart-Flooding-Detector-STM32/
├── Core/                          # Core firmware
│   ├── Inc/                       # Header files
│   │   ├── fonts.h                # OLED font definitions
│   │   ├── main.h                 # HAL externs, pin defines
│   │   ├── ssd1306.h              # OLED driver header
│   │   ├── stm32f1xx_hal_conf.h   # HAL configuration
│   │   └── stm32f1xx_it.h        # Interrupt handlers header
│   ├── Src/                       # Source files
│   │   ├── main.c                 # Main application (1288 lines)
│   │   ├── fonts.c                # OLED font bitmap data
│   │   ├── ssd1306.c              # SSD1306 OLED driver
│   │   ├── stm32f1xx_hal_msp.c    # HAL MSP init
│   │   ├── stm32f1xx_it.c         # Interrupt service routines
│   │   ├── syscalls.c             # Syscall stubs
│   │   ├── sysmem.c               # Heap implementation
│   │   └── system_stm32f1xx.c     # System clock config
│   └── Startup/                   # Startup assembly
├── Drivers/                       # STM32 HAL drivers
│   ├── CMSIS/                     # Cortex-M CMSIS core
│   └── STM32F1xx_HAL_Driver/      # STM32F1 HAL peripheral drivers
├── .cproject                      # Eclipse/CDT project config
├── .project                       # Eclipse project file
├── .mxproject                     # STM32CubeMX project metadata
├── CSE331_Final.ioc               # STM32CubeMX IOC configuration
├── CSE331_Final.pdf               # Project schematic (PDF)
├── CSE331_Final.txt               # Pinout/configuration report
├── STM32F103C8TX_FLASH.ld         # Linker script
├── main.c                         # Root copy of main (mirrors Core/Src/main.c)
├── changes.md                     # Detailed changelog
├── Paper.pdf                      # Academic paper
└── README.md                      # This file
```

---

<a name="building--flashing"></a>
## 🏗️ Building & Flashing

### Prerequisites

1. **STM32CubeIDE** (recommended) — Download from [STMicroelectronics](https://www.st.com/en/development-tools/stm32cubeide.html)
2. **STM32CubeMX** (optional, for reconfiguration) — v6.15.0 used
3. **STM32F1 Firmware Package** v1.8.7

### Build Steps

```bash
# 1. Clone the repository
git clone https://github.com/tanvirbinzahid/Smart-Flooding-Detector-STM32.git

# 2. Open STM32CubeIDE
#    File → Import → Existing Projects into Workspace
#    Select the cloned directory

# 3. Build the project
#    Project → Build All (or Ctrl+B)

# 4. Flash via ST-Link
#    Run → Debug (or the green bug icon)
```

### Flashing with ST-Link (CLI)

```bash
# Using openocd (included with STM32CubeIDE)
openocd -f board/stm32f1bluepill.cfg -c "program CSE331_Final.elf verify reset exit"
```

---

## 📊 Performance Characteristics

| Parameter | Value |
|-----------|-------|
| Sampling Interval | 500 ms (normal), 5 s (power-save) |
| DHT11 Update | 2 s |
| Power-Save Entry | 1 hour of stable SAFE |
| Ultrasonic Range | 2–250 cm |
| Sensor Fusion | Median(5) + MovingAvg(8) + Deadband |
| Alert Latency | < 1 s (within 2 samples) |
| MCU Clock | 72 MHz (HSE 8 MHz × 9 PLL) |
| OLED Refresh | 50–60 FPS (tied to main loop) |

---

## 🔬 Signal Processing Details

### Ultrasonic Filtering Pipeline

```
Raw Echo ──► 5-sample Median ──► 8-sample Moving Avg ──► Deadband ──► Water Level
               (removes spikes)    (smoothing)            (±cm filter)
```

The deadband is dynamically adjusted by `SYS_SEN`:
- `SYS_SEN = 1` → deadband = 2.75 cm (least sensitive)
- `SYS_SEN = 5` → deadband = 1.75 cm (default)
- `SYS_SEN = 10` → deadband = 0.50 cm (most sensitive)

### Formula: `deadband = 3.00 - (0.25 × SYS_SEN)`

---

<a name="paper"></a>
## 📄 Paper

The academic paper detailing this project is included in this repository:

<p align="center">
  <a href="./Paper.pdf">
    <img src="https://img.shields.io/badge/Download-PDF-red?style=for-the-badge&logo=adobeacrobatreader&logoColor=white"/>
  </a>
</p>

<object data="./Paper.pdf" type="application/pdf" width="100%" height="600px">
  <p>Your browser does not support embedded PDFs. <a href="./Paper.pdf">Download the paper</a> instead.</p>
</object>

---

## 🧪 Testing

The system has been tested with:
- Real water-level simulation using hand/object proximity to HC-SR04
- DHT11 in various ambient conditions (25–35°C, 60–95% RH)
- Soil moisture sensor in dry/moist/wet soil samples
- Continuous 24-hour stability test
- Power-save mode current measurement (~15 mA active, ~5 mA power-save)

---

## 📜 Changelog

See [changes.md](./changes.md) for a detailed version history.

---

## 👨‍💻 Author

**Tanvir Bin Zahid**  
Project submitted for **CSE331: Microprocessor Interfacing and Embedded System Design**

---

## 📝 License

This project is open-source and available for educational and research purposes.

---

<p align="center">
  <sub>Built with ❤️ using STM32CubeIDE & STM32 HAL Library</sub>
</p>
