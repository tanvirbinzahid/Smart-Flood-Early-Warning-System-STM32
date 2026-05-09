/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Smart Flood Early Warning System
  ******************************************************************************
  * Sensors  : HC-SR04 (PA2/PA3), DHT11 (PA1), Soil Moisture ADC (PA0)
  * Outputs  : OLED I2C (PB6/PB7), LEDs (PA5-PA9), Buzzer (PB0)
  * Input    : 4x4 Keypad Rows PB8-PB11, Cols PB12-PB15
  * Timer    : TIM1 used for microsecond delays (prescaler set to 71 = 1us tick)
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "ssd1306.h"
#include "fonts.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
typedef enum { TIER_SAFE = 0, TIER_WARNING = 1, TIER_EVACUATE = 2 } AlertTier_t;

/* Keypad-selectable OLED pages. */
typedef enum {
    SCREEN_MAIN = 0,
    SCREEN_SENSORS = 1,
    SCREEN_STATS = 2,
    SCREEN_SENSITIVITY = 3,
    SCREEN_ULTRA_DB = 4,
    SCREEN_SOIL_DRY = 5
} Screen_t;

typedef struct {
    uint8_t  buf[12];
    uint8_t  idx;
    uint8_t  count;
} RingBuf_t;

typedef struct {
    float    wl_min, wl_max;
    float    rr_min, rr_max;
    uint8_t  ri_min, ri_max;
} Stats_t;

typedef struct {
    int32_t  acc;
    uint16_t samples[8];
    uint8_t  idx;
    uint8_t  filled;
} MovAvg8_t;
/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
/* Distance thresholds (cm from sensor down to water surface):
   larger distance = water is safely far below = SAFE
   smaller distance = water is close to sensor  = DANGER             */
#define WL_SAFE_CM      60u
#define WL_WARN_CM      40u
#define WL_EVAC_CM      20u
#define MAX_RISE_CMS    4.0f
#define TREND_BOOST     2.5f
#define SYS_SEN_MIN     1u
#define SYS_SEN_MAX     10u
#define ULTRA_MIN_CM    2.0f
#define ULTRA_MAX_CM    250.0f
#define PSAVE_SECS      3600u
#define SAMPLE_MS       500u
#define PSAVE_MS        5000u
#define DHT_SAMPLE_MS   2000u

/* Displayed water level is inverted using this depth */
#define WL_DEPTH_CM     9.0f

/* Ultrasonic deadband tuning (key 7/9) */
#define ULTRA_DB_MIN    0.50f
#define ULTRA_DB_MAX    3.00f
#define ULTRA_DB_STEP   0.25f

/* Soil dry calibration (key 8/0) */
#define SOIL_WET_ADC    500u
#define SOIL_DRY_MIN    500u
#define SOIL_DRY_MAX    4095u
#define SOIL_DRY_STEP   150u

/* GPIO shortcuts */
#define LED_GREEN  GPIO_PIN_5
#define LED_Y1     GPIO_PIN_6
#define LED_Y2     GPIO_PIN_7
#define LED_R1     GPIO_PIN_8
#define LED_R2     GPIO_PIN_9
#define LED_PORT   GPIOA

#define BUZZER_PIN  GPIO_PIN_0
#define BUZZER_PORT GPIOB

#define TRIG_PIN  GPIO_PIN_2
#define TRIG_PORT GPIOA
#define ECHO_PIN  GPIO_PIN_3
#define ECHO_PORT GPIOA

#define DHT_PIN   GPIO_PIN_1
#define DHT_PORT  GPIOA

#define ROW1 GPIO_PIN_8
#define ROW2 GPIO_PIN_9
#define ROW3 GPIO_PIN_10
#define ROW4 GPIO_PIN_11
#define COL1 GPIO_PIN_12
#define COL2 GPIO_PIN_13
#define COL3 GPIO_PIN_14
#define COL4 GPIO_PIN_15
#define KROW_PORT GPIOB
#define KCOL_PORT GPIOB
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */
/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
ADC_HandleTypeDef hadc1;

I2C_HandleTypeDef hi2c1;

TIM_HandleTypeDef htim1;

/* USER CODE BEGIN PV */
static float        water_level_cm = 100.0f;
static float        water_level_display_cm = 0.0f;
static float        rise_rate_cms  = 0.0f;
static float        temperature_c  = 0.0f;
static float        humidity_pct   = 0.0f;
static uint8_t      dht_ok         = 0;       /* 1 means last DHT11 read succeeded; 0 means show DHT error */
static uint8_t      soil_pct       = 0;

static MovAvg8_t    soil_avg       = {0};
static MovAvg8_t    water_avg      = {0};           /* Moving average buffer for HC-SR04 readings */
static RingBuf_t    ri_buf         = {0};
static uint8_t      risk_index     = 0;
static AlertTier_t  current_tier   = TIER_SAFE;
static AlertTier_t  prev_tier      = TIER_SAFE;

static Stats_t      stats          = {999,0,999,0,255,0};
static uint32_t     stable_secs    = 0;
static uint8_t      power_save     = 0;
static Screen_t     current_screen = SCREEN_MAIN;  /* Starts on summary page; keypad changes this */
static uint8_t      buzzer_muted   = 0;
static uint8_t      ultrasonic_ready = 0;           /* Becomes 1 after the first valid ultrasonic reading */
static uint8_t      sys_sen        = 5;             /* System sensitivity: key 5 lowers, key 6 raises */
static float        ultra_deadband_cm = 2.00f;      /* Ultrasonic deadband: key 7 lowers, key 9 raises */
static uint16_t     soil_dry_adc   = 3500;          /* Soil dry calibration: key 8 lowers, key 0 raises */
static uint32_t     sensitivity_screen_until = 0;   /* Time until the temporary SYS_SEN screen closes */
static uint32_t     ultra_screen_until = 0;         /* Time until ultrasonic deadband screen closes */
static uint32_t     soil_screen_until = 0;          /* Time until soil dry calibration screen closes */

static uint32_t     last_sample_ms = 0;
static uint32_t     last_dht_ms    = 0;
static uint32_t     last_sec_ms    = 0;
static uint32_t     last_buzz_ms   = 0;
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_ADC1_Init(void);
static void MX_I2C1_Init(void);
static void MX_TIM1_Init(void);
/* USER CODE BEGIN PFP */
static void        micro_delay(uint16_t us);
static float       HCSR04_Read_cm(void);
static void        DHT11_SetOutput(void);
static void        DHT11_SetInput(void);
static uint8_t     DHT11_Read(float *temp, float *hum);
static uint8_t     Soil_Read(void);
static uint8_t     Normalise(float val, float lo, float hi);
static void        RingBuf_Push(RingBuf_t *rb, uint8_t val);
static float       WaterAvg_Push(float cm);
static void        FormatFloat1(char *out, uint8_t out_size, float val);
static void        FormatFloat2(char *out, uint8_t out_size, float val);
static float       LeastSquaresSlope(RingBuf_t *rb);
static AlertTier_t Classify(uint8_t ri, float trend);
static void        Stats_Update(float wl, float rr, uint8_t ri);
static void        LED_SetTier(AlertTier_t tier);
static void        Buzzer_Update(AlertTier_t tier);
static char        Keypad_Scan(void);
static const char* TierText(AlertTier_t tier);
static void        OLED_ApplyDangerTheme(void);
static void        OLED_DrawRiskBar(uint8_t x0, uint8_t y0, uint8_t width, uint8_t height, uint8_t risk);
static void        OLED_MainScreen(void);
static void        OLED_SensorScreen(void);
static void        OLED_StatsScreen(void);
static void        OLED_SensitivityScreen(void);
static void        OLED_UltraDeadbandScreen(void);
static void        OLED_SoilDryScreen(void);
static void        EnterPowerSave(void);
static void        ExitPowerSave(void);
static float       WaterLevel_Display(float distance_cm);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* ── Microsecond delay via TIM1 (prescaler 71 → 1 tick = 1 us @ 72 MHz) ── */
static void micro_delay(uint16_t us)
{
    __HAL_TIM_SET_COUNTER(&htim1, 0);
    while (__HAL_TIM_GET_COUNTER(&htim1) < us);
}

/* ── HC-SR04: 5-sample median, returns distance in cm ── */
static int cmp_u32(const void *a, const void *b)
{
    uint32_t ua = *(const uint32_t *)a;
    uint32_t ub = *(const uint32_t *)b;
    return (ua > ub) - (ua < ub);
}

static float HCSR04_Read_cm(void)
{
    uint32_t samples[5];
    for (int i = 0; i < 5; i++) {
        HAL_GPIO_WritePin(TRIG_PORT, TRIG_PIN, GPIO_PIN_SET);
        micro_delay(10);
        HAL_GPIO_WritePin(TRIG_PORT, TRIG_PIN, GPIO_PIN_RESET);

        uint32_t t = HAL_GetTick();
        while (!HAL_GPIO_ReadPin(ECHO_PORT, ECHO_PIN)) {
            if (HAL_GetTick() - t > 30) { samples[i] = 0; goto next; }
        }
        __HAL_TIM_SET_COUNTER(&htim1, 0);
        t = HAL_GetTick();
        while (HAL_GPIO_ReadPin(ECHO_PORT, ECHO_PIN)) {
            if (HAL_GetTick() - t > 50) break;
        }
        samples[i] = __HAL_TIM_GET_COUNTER(&htim1);
        next:
        HAL_Delay(5);
    }
    qsort(samples, 5, sizeof(uint32_t), cmp_u32);
    return (float)samples[2] * 0.034f / 2.0f;
}

/* ── DHT11 pin-mode helpers ── */
static void DHT11_SetOutput(void)
{
    GPIO_InitTypeDef g = {0};
    g.Pin   = DHT_PIN;
    g.Mode  = GPIO_MODE_OUTPUT_PP;
    g.Pull  = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(DHT_PORT, &g);
}

static void DHT11_SetInput(void)
{
    GPIO_InitTypeDef g = {0};
    g.Pin  = DHT_PIN;
    g.Mode = GPIO_MODE_INPUT;
    g.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(DHT_PORT, &g);
}

/* ── DHT11 read — returns 1 on success ── */
static uint8_t DHT11_Read(float *temp, float *hum)
{
    uint8_t data[5] = {0};

    DHT11_SetOutput();
    HAL_GPIO_WritePin(DHT_PORT, DHT_PIN, GPIO_PIN_RESET);
    HAL_Delay(18);
    HAL_GPIO_WritePin(DHT_PORT, DHT_PIN, GPIO_PIN_SET);
    micro_delay(30);
    DHT11_SetInput();

    micro_delay(40);
    if (HAL_GPIO_ReadPin(DHT_PORT, DHT_PIN)) goto fail;
    micro_delay(80);
    if (!HAL_GPIO_ReadPin(DHT_PORT, DHT_PIN)) goto fail;
    micro_delay(80);

    for (int i = 0; i < 5; i++) {
        for (int b = 7; b >= 0; b--) {
            uint32_t t = HAL_GetTick();
            while (!HAL_GPIO_ReadPin(DHT_PORT, DHT_PIN)) {
                if (HAL_GetTick() - t > 5) goto fail;
            }
            micro_delay(40);
            if (HAL_GPIO_ReadPin(DHT_PORT, DHT_PIN)) {
                data[i] |= (1 << b);
                t = HAL_GetTick();
                while (HAL_GPIO_ReadPin(DHT_PORT, DHT_PIN)) {
                    if (HAL_GetTick() - t > 5) goto fail;
                }
            }
        }
    }

    if ((uint8_t)(data[0] + data[1] + data[2] + data[3]) != data[4]) goto fail;
    *hum  = (float)data[0] + data[1] * 0.1f;
    *temp = (float)data[2] + data[3] * 0.1f;
    DHT11_SetOutput();
    HAL_GPIO_WritePin(DHT_PORT, DHT_PIN, GPIO_PIN_SET);
    return 1;

fail:
    DHT11_SetOutput();
    HAL_GPIO_WritePin(DHT_PORT, DHT_PIN, GPIO_PIN_SET);
    return 0;
}

/* ── Soil moisture via ADC (8-sample moving average) ── */
static uint8_t Soil_Read(void)
{
    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 100);
    uint16_t raw = (uint16_t)HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);

    soil_avg.acc -= soil_avg.samples[soil_avg.idx];
    soil_avg.samples[soil_avg.idx] = raw;
    soil_avg.acc += raw;
    soil_avg.idx = (soil_avg.idx + 1) % 8;
    if (!soil_avg.filled && soil_avg.idx == 0) soil_avg.filled = 1;

    uint16_t n   = soil_avg.filled ? 8 : (soil_avg.idx ? soil_avg.idx : 1);
    uint16_t avg = (uint16_t)(soil_avg.acc / n);

    uint16_t dry = soil_dry_adc;
    if (dry <= SOIL_WET_ADC) dry = SOIL_WET_ADC + 1;

    if (avg > dry) avg = dry;
    if (avg < SOIL_WET_ADC) avg = SOIL_WET_ADC;

    return (uint8_t)(100 - ((avg - SOIL_WET_ADC) * 100 / (dry - SOIL_WET_ADC)));
}

/* ── Normalise value [lo, hi] → [0, 100] ── */
static uint8_t Normalise(float val, float lo, float hi)
{
    if (val <= lo) return 0;
    if (val >= hi) return 100;
    return (uint8_t)((val - lo) * 100.0f / (hi - lo));
}

/* ── Ring buffer push ── */
static void RingBuf_Push(RingBuf_t *rb, uint8_t val)
{
    rb->buf[rb->idx] = val;
    rb->idx = (rb->idx + 1) % 12;
    if (rb->count < 12) rb->count++;
}

/* HC-SR04 moving average after the median filter.
   The median removes sudden spikes; this average smooths the remaining small movement. */
static float WaterAvg_Push(float cm)
{
    uint16_t cm_x10 = (uint16_t)(cm * 10.0f);                 /* Store one decimal place as an integer */
    water_avg.acc -= water_avg.samples[water_avg.idx];        /* Remove oldest sample from total */
    water_avg.samples[water_avg.idx] = cm_x10;                /* Save newest filtered water distance */
    water_avg.acc += cm_x10;                                  /* Add newest sample to total */
    water_avg.idx = (water_avg.idx + 1) % 8;                  /* Move circular-buffer index */
    if (!water_avg.filled && water_avg.idx == 0) water_avg.filled = 1; /* Mark full after 8 samples */

    uint16_t n = water_avg.filled ? 8 : (water_avg.idx ? water_avg.idx : 1); /* Average only real samples */
    return ((float)water_avg.acc / (float)n) / 10.0f;          /* Convert back from x10 cm to cm */
}

/* Formats a float with 1 decimal without using printf("%f").
   STM32 newlib-nano often disables float printf, so this keeps OLED values visible. */
static void FormatFloat1(char *out, uint8_t out_size, float val)
{
    int32_t scaled = (int32_t)(val * 10.0f + (val >= 0.0f ? 0.5f : -0.5f)); /* Round to 1 decimal */
    int32_t whole = scaled / 10;                                            /* Digits before decimal */
    int32_t frac  = scaled % 10;                                            /* One digit after decimal */
    if (frac < 0) frac = -frac;                                             /* Keep decimal digit positive */
    snprintf(out, out_size, "%ld.%ld", (long)whole, (long)frac);            /* Integer printf works on nano */
}

/* Same as FormatFloat1, but keeps 2 decimal places for rise rate. */
static void FormatFloat2(char *out, uint8_t out_size, float val)
{
    int32_t scaled = (int32_t)(val * 100.0f + (val >= 0.0f ? 0.5f : -0.5f)); /* Round to 2 decimals */
    int32_t whole = scaled / 100;                                           /* Digits before decimal */
    int32_t frac  = scaled % 100;                                           /* Two digits after decimal */
    if (frac < 0) frac = -frac;                                             /* Keep decimal digits positive */
    snprintf(out, out_size, "%ld.%02ld", (long)whole, (long)frac);          /* Integer printf avoids %f */
}

/* ── Least-squares slope over ring buffer (trend engine) ── */
static float LeastSquaresSlope(RingBuf_t *rb)
{
    if (rb->count < 4) return 0.0f;
    float n = (float)rb->count;
    float sx = 0, sy = 0, sxy = 0, sx2 = 0;
    for (uint8_t i = 0; i < rb->count; i++) {
        uint8_t real_idx = (uint8_t)((rb->idx + 12 - rb->count + i) % 12);
        float x = (float)i;
        float y = (float)rb->buf[real_idx];
        sx  += x;  sy  += y;
        sxy += x * y;  sx2 += x * x;
    }
    float denom = n * sx2 - sx * sx;
    return (denom == 0.0f) ? 0.0f : (n * sxy - sx * sy) / denom;
}

/* ── Alert tier classification with hysteresis + predictive boost ── */
static AlertTier_t Classify(uint8_t ri, float trend)
{
    AlertTier_t t;
    if      (ri >= 75) t = TIER_EVACUATE;
    else if (ri >= 40) t = TIER_WARNING;
    else               t = TIER_SAFE;

    if (trend > TREND_BOOST && t < TIER_EVACUATE)
        t = (AlertTier_t)(t + 1);

    if (t < current_tier) {
        if (current_tier == TIER_EVACUATE && ri > 70) t = TIER_EVACUATE;
        if (current_tier == TIER_WARNING   && ri > 35) t = TIER_WARNING;
    }
    return t;
}

/* ── Session statistics update ── */
static void Stats_Update(float wl, float rr, uint8_t ri)
{
    if (wl < stats.wl_min) stats.wl_min = wl;
    if (wl > stats.wl_max) stats.wl_max = wl;
    if (rr < stats.rr_min) stats.rr_min = rr;
    if (rr > stats.rr_max) stats.rr_max = rr;
    if (ri < stats.ri_min) stats.ri_min = ri;
    if (ri > stats.ri_max) stats.ri_max = ri;
}

/* ── LED output ── */
static void LED_SetTier(AlertTier_t tier)
{
    HAL_GPIO_WritePin(LED_PORT,
        LED_GREEN | LED_Y1 | LED_Y2 | LED_R1 | LED_R2, GPIO_PIN_RESET);

    uint16_t active_leds[5];
    uint8_t count = 0;

    /* Build sequence of LEDs that should be on based on risk */
    if (risk_index >= 0)  active_leds[count++] = LED_GREEN;
    if (risk_index >= 20) active_leds[count++] = LED_Y1;
    if (risk_index >= 40) active_leds[count++] = LED_Y2;
    if (risk_index >= 60) active_leds[count++] = LED_R1;
    if (risk_index >= 80) active_leds[count++] = LED_R2;

    /* Software multiplexing: light one LED at a time per loop to fix
       shared-resistor hardware voltage drop issues. The eye sees all of them on. */
    static uint8_t mux_idx = 0;
    mux_idx = (mux_idx + 1) % count;

    if (tier == TIER_EVACUATE) {
        if ((HAL_GetTick() / 125) % 2)
            HAL_GPIO_WritePin(LED_PORT, active_leds[mux_idx], GPIO_PIN_SET); /* Danger: blink all active LEDs */
    } else {
        HAL_GPIO_WritePin(LED_PORT, active_leds[mux_idx], GPIO_PIN_SET);     /* Normal: solid LEDs based on risk */
    }
}

/* ── Non-blocking buzzer ── */
static void Buzzer_Update(AlertTier_t tier)
{
    if (buzzer_muted || tier == TIER_SAFE) {
        HAL_GPIO_WritePin(BUZZER_PORT, BUZZER_PIN, GPIO_PIN_RESET);
        return;
    }
    uint32_t interval = (tier == TIER_WARNING) ? 500u : 125u;
    if (HAL_GetTick() - last_buzz_ms >= interval) {
        HAL_GPIO_TogglePin(BUZZER_PORT, BUZZER_PIN);
        last_buzz_ms = HAL_GetTick();
    }
}

/* ── 4x4 Keypad scan — returns key char, 0 if none pressed ── */
static char Keypad_Scan(void)
{
    static const char keys[4][4] = {
        {'1','2','3','A'},
        {'4','5','6','B'},
        {'7','8','9','C'},
        {'*','0','#','D'}
    };
    const uint16_t rows[4] = {ROW1, ROW2, ROW3, ROW4};
    const uint16_t cols[4] = {COL1, COL2, COL3, COL4};

    for (int r = 0; r < 4; r++) {
        HAL_GPIO_WritePin(KROW_PORT, ROW1 | ROW2 | ROW3 | ROW4, GPIO_PIN_SET);
        HAL_GPIO_WritePin(KROW_PORT, rows[r], GPIO_PIN_RESET);
        HAL_Delay(1);
        for (int c = 0; c < 4; c++) {
            if (!HAL_GPIO_ReadPin(KCOL_PORT, cols[c])) {
                HAL_Delay(20);
                if (!HAL_GPIO_ReadPin(KCOL_PORT, cols[c])) {
                    while (!HAL_GPIO_ReadPin(KCOL_PORT, cols[c]));
                    HAL_GPIO_WritePin(KROW_PORT,
                        ROW1 | ROW2 | ROW3 | ROW4, GPIO_PIN_SET);
                    return keys[r][c];
                }
            }
        }
    }
    HAL_GPIO_WritePin(KROW_PORT, ROW1 | ROW2 | ROW3 | ROW4, GPIO_PIN_SET);
    return 0;
}

/* Returns simple text for the alert tier so every OLED page can print it. */
static const char* TierText(AlertTier_t tier)
{
    switch (tier) {
        case TIER_SAFE:     return "SAFE";      /* Water/risk is currently low */
        case TIER_WARNING:  return "WARNING";   /* Risk is medium; be careful */
        case TIER_EVACUATE: return "EVACUATE";  /* Risk is high; alarm state */
        default:            return "UNKNOWN";   /* Backup text if tier is invalid */
    }
}

/* SSD1306 OLED is black/white only, so danger "red theme" is shown by flashing/inverting the display. */
static void OLED_ApplyDangerTheme(void)
{
    if (current_tier == TIER_EVACUATE) {                    /* Only use the alert theme at danger level */
        SSD1306_InvertDisplay((HAL_GetTick() / 250u) % 2u); /* Blink every 250 ms to imitate a red alert */
    } else {
        SSD1306_InvertDisplay(0);                           /* Keep normal black background when not danger */
    }
}

/* Draws a risk bar with 3 visual "color" zones: safe, warning, danger.
   Because SSD1306 is monochrome, patterns are used instead of real colors:
   safe = thin solid line, warning = striped fill, danger = full bright fill. */
static void OLED_DrawRiskBar(uint8_t x0, uint8_t y0, uint8_t width, uint8_t height, uint8_t risk)
{
    uint8_t fill_width = (uint8_t)((uint16_t)risk * width / 100u); /* Converts 0-100 risk into pixel width */
    uint8_t warn_x     = (uint8_t)(width * 40u / 100u);            /* Warning starts around RI 40 */
    uint8_t danger_x   = (uint8_t)(width * 75u / 100u);            /* Evacuate/danger starts around RI 75 */

    SSD1306_DrawRectangle(x0, y0, width + 1u, height + 1u, SSD1306_COLOR_WHITE); /* White outline of bar */
    SSD1306_DrawLine(x0 + warn_x, y0, x0 + warn_x, y0 + height, SSD1306_COLOR_WHITE);     /* Safe/warning mark */
    SSD1306_DrawLine(x0 + danger_x, y0, x0 + danger_x, y0 + height, SSD1306_COLOR_WHITE); /* Warning/danger mark */

    for (uint8_t x = 0; x < fill_width; x++) {
        if (x < warn_x) {
            SSD1306_DrawPixel(x0 + 1u + x, y0 + height - 1u, SSD1306_COLOR_WHITE); /* Safe zone: low thin fill */
        } else if (x < danger_x) {
            for (uint8_t y = 1u; y < height; y++) {
                if (((x + y) % 2u) == 0u) {                       /* Warning zone: checker/stripe pattern */
                    SSD1306_DrawPixel(x0 + 1u + x, y0 + y, SSD1306_COLOR_WHITE);
                }
            }
        } else {
            SSD1306_DrawLine(x0 + 1u + x, y0 + 1u, x0 + 1u + x, y0 + height - 1u,
                             SSD1306_COLOR_WHITE);                /* Danger zone: solid bright fill */
        }
    }
}

/* ── OLED main screen ──
   Layout (128x64, Font_7x10 = 7px wide, 10px tall → 18 chars/line, 6 lines)
   y=0  : Tier banner
   y=12 : Water level + rise rate
   y=24 : Humidity + soil
   y=36 : Risk index
   y=48 : Progress bar (3px tall)
   y=54 : Key hints                                                         */
static void OLED_MainScreen(void)
{
    char buf[32];
    char wl_txt[12], rr_txt[12], t_txt[12], h_txt[12]; /* Text versions of float values for OLED */

    /* Cast away const — library expects char*, not const char* */
    char *tier_labels[3] = {"   ** SAFE **   ",
                            "  ** WARNING ** ",
                            "  !!EVACUATE!!  "};

    OLED_ApplyDangerTheme();                 /* Danger level flashes/inverts the OLED like a red alert theme */
    SSD1306_Fill(SSD1306_COLOR_BLACK);

    SSD1306_GotoXY(0, 0);
    SSD1306_Puts(tier_labels[current_tier], &Font_7x10, SSD1306_COLOR_WHITE);

    FormatFloat1(wl_txt, sizeof(wl_txt), water_level_display_cm); /* Display inverted water level */
    FormatFloat2(rr_txt, sizeof(rr_txt), rise_rate_cms);          /* Convert rise rate without using %f */
    snprintf(buf, sizeof(buf), "WL:%scm R:%s", wl_txt, rr_txt);   /* Bigger buffer avoids truncation warning */
    SSD1306_GotoXY(0, 12);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    if (dht_ok) {
        FormatFloat1(t_txt, sizeof(t_txt), temperature_c); /* Convert DHT temperature without using %f */
        FormatFloat1(h_txt, sizeof(h_txt), humidity_pct);  /* Convert DHT humidity without using %f */
        snprintf(buf, sizeof(buf), "T:%sC H:%s%%", t_txt, h_txt); /* DHT11 temperature + humidity */
    } else {
        snprintf(buf, sizeof(buf), "DHT:ERR check wire");  /* Shows failure instead of misleading 0 values */
    }
    SSD1306_GotoXY(0, 24);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    snprintf(buf, sizeof(buf), "SOIL:%3d%% RI:%3d", soil_pct, risk_index); /* Soil ADC reading + final risk index */
    SSD1306_GotoXY(0, 36);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    OLED_DrawRiskBar(0, 47, 126, 5, risk_index); /* Patterned risk bar: safe/warning/danger zones */

    if (power_save) {
        SSD1306_GotoXY(0, 54);
        SSD1306_Puts("PWR-SAVE [*]=wake", &Font_7x10, SSD1306_COLOR_WHITE);
    } else {
        snprintf(buf, sizeof(buf), "SYS_SEN:%02d 5/6", sys_sen); /* Menu shows sensitivity; key 5 lowers and 6 raises */
        SSD1306_GotoXY(0, 54);
        SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);
    }

    SSD1306_UpdateScreen();
}

/* OLED page that shows all live sensor readings together.
   Press keypad key 3 to switch between this page and summary. */
static void OLED_SensorScreen(void)
{
    char buf[32];  /* Bigger than OLED line so snprintf never truncates before drawing */
    char wl_txt[12], rr_txt[12], t_txt[12], h_txt[12]; /* Float text buffers that avoid printf("%f") */

    OLED_ApplyDangerTheme();                 /* Keep same danger alert theme on the sensor page */
    SSD1306_Fill(SSD1306_COLOR_BLACK);

    snprintf(buf, sizeof(buf), "DATA:%s S:%02d", TierText(current_tier), sys_sen); /* Tier + SYS_SEN always visible */
    SSD1306_GotoXY(0, 0);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    FormatFloat1(wl_txt, sizeof(wl_txt), water_level_display_cm); /* Display inverted water level */
    snprintf(buf, sizeof(buf), "WL:%scm", wl_txt); /* HC-SR04 water level */
    SSD1306_GotoXY(0, 12);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    FormatFloat2(rr_txt, sizeof(rr_txt), rise_rate_cms); /* Convert rise rate without using %f */
    snprintf(buf, sizeof(buf), "Rise:%scm/s", rr_txt); /* Calculated speed of rising water */
    SSD1306_GotoXY(0, 22);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    if (dht_ok) {
        FormatFloat1(t_txt, sizeof(t_txt), temperature_c); /* Convert DHT temperature without using %f */
        FormatFloat1(h_txt, sizeof(h_txt), humidity_pct);  /* Convert DHT humidity without using %f */
        snprintf(buf, sizeof(buf), "T:%sC H:%s%%", t_txt, h_txt); /* DHT11 readings */
    } else {
        snprintf(buf, sizeof(buf), "DHT:ERR check wire");  /* DHT11 did not return a valid checksum */
    }
    SSD1306_GotoXY(0, 32);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    snprintf(buf, sizeof(buf), "Soil:%3d%% RI:%3d", soil_pct, risk_index); /* Soil moisture + Risk Index */
    SSD1306_GotoXY(0, 42);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    snprintf(buf, sizeof(buf), "5- 6+  4Stats"); /* Key hints for sensitivity and min/max page */
    SSD1306_GotoXY(0, 52);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    SSD1306_UpdateScreen();
}

/* Temporary screen shown after changing SYS_SEN so you can see the new value clearly. */
static void OLED_SensitivityScreen(void)
{
    char buf[32];
    char wl_txt[12]; /* Float text buffer that avoids printf("%f") */

    OLED_ApplyDangerTheme();                     /* Still keep danger flashing if flood state is high */
    SSD1306_Fill(SSD1306_COLOR_BLACK);

    SSD1306_GotoXY(0, 0);
    SSD1306_Puts("SENSITIVITY", &Font_7x10, SSD1306_COLOR_WHITE);

    snprintf(buf, sizeof(buf), "SYS_SEN: %02d/10", sys_sen); /* Large clear sensitivity value */
    SSD1306_GotoXY(0, 16);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    SSD1306_GotoXY(0, 32);
    SSD1306_Puts("5=LOW 6=HIGH", &Font_7x10, SSD1306_COLOR_WHITE); /* 5 also works for your keypad habit */

    FormatFloat1(wl_txt, sizeof(wl_txt), water_level_display_cm); /* Display inverted water level */
    snprintf(buf, sizeof(buf), "WL:%s RI:%3d", wl_txt, risk_index); /* Show live effect while tuning */
    SSD1306_GotoXY(0, 48);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    SSD1306_UpdateScreen();
}

/* Temporary screen shown after changing ultrasonic deadband. */
static void OLED_UltraDeadbandScreen(void)
{
    char buf[32];
    char db_txt[12], min_txt[12], max_txt[12];

    OLED_ApplyDangerTheme();
    SSD1306_Fill(SSD1306_COLOR_BLACK);

    SSD1306_GotoXY(0, 0);
    SSD1306_Puts("ULTRA DEADBAND", &Font_7x10, SSD1306_COLOR_WHITE);

    FormatFloat2(db_txt, sizeof(db_txt), ultra_deadband_cm);
    snprintf(buf, sizeof(buf), "DB:%scm", db_txt);
    SSD1306_GotoXY(0, 16);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    FormatFloat2(min_txt, sizeof(min_txt), ULTRA_DB_MIN);
    FormatFloat2(max_txt, sizeof(max_txt), ULTRA_DB_MAX);
    snprintf(buf, sizeof(buf), "MIN:%s MAX:%s", min_txt, max_txt);
    SSD1306_GotoXY(0, 32);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    SSD1306_GotoXY(0, 48);
    SSD1306_Puts("7=LOW 9=HIGH", &Font_7x10, SSD1306_COLOR_WHITE);

    SSD1306_UpdateScreen();
}

/* Temporary screen shown after changing soil dry calibration. */
static void OLED_SoilDryScreen(void)
{
    char buf[32];

    OLED_ApplyDangerTheme();
    SSD1306_Fill(SSD1306_COLOR_BLACK);

    SSD1306_GotoXY(0, 0);
    SSD1306_Puts("SOIL DRY CAL", &Font_7x10, SSD1306_COLOR_WHITE);

    snprintf(buf, sizeof(buf), "DRY:%4u", soil_dry_adc);
    SSD1306_GotoXY(0, 16);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    snprintf(buf, sizeof(buf), "MIN:%u MAX:%u", SOIL_DRY_MIN, SOIL_DRY_MAX);
    SSD1306_GotoXY(0, 32);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    SSD1306_GotoXY(0, 48);
    SSD1306_Puts("8=LOW 0=HIGH", &Font_7x10, SSD1306_COLOR_WHITE);

    SSD1306_UpdateScreen();
}

/* ── OLED statistics screen ── */
static void OLED_StatsScreen(void)
{
    char buf[32];
    char wl_min_txt[12], wl_max_txt[12], rr_min_txt[12], rr_max_txt[12], t_txt[12], h_txt[12];

    OLED_ApplyDangerTheme();                 /* Stats page also flashes if the system reaches danger level */
    SSD1306_Fill(SSD1306_COLOR_BLACK);

    SSD1306_GotoXY(0, 0);
    SSD1306_Puts("MIN/MAX  KEY 4", &Font_7x10, SSD1306_COLOR_WHITE); /* Dedicated keypad-4 min/max menu */

    FormatFloat1(wl_min_txt, sizeof(wl_min_txt), stats.wl_min); /* Convert min water level without %f */
    FormatFloat1(wl_max_txt, sizeof(wl_max_txt), stats.wl_max); /* Convert max water level without %f */
    snprintf(buf, sizeof(buf), "WL:%s~%scm", wl_min_txt, wl_max_txt);
    SSD1306_GotoXY(0, 12);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    FormatFloat2(rr_min_txt, sizeof(rr_min_txt), stats.rr_min); /* Convert min rise rate without %f */
    FormatFloat2(rr_max_txt, sizeof(rr_max_txt), stats.rr_max); /* Convert max rise rate without %f */
    snprintf(buf, sizeof(buf), "RR:%s~%s", rr_min_txt, rr_max_txt);
    SSD1306_GotoXY(0, 24);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    snprintf(buf, sizeof(buf), "RI: %d ~ %d /100", stats.ri_min, stats.ri_max);
    SSD1306_GotoXY(0, 36);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    if (dht_ok) {
        FormatFloat1(t_txt, sizeof(t_txt), temperature_c); /* Convert DHT temperature without %f */
        FormatFloat1(h_txt, sizeof(h_txt), humidity_pct);  /* Convert DHT humidity without %f */
        snprintf(buf, sizeof(buf), "T:%sC H:%s%%", t_txt, h_txt);
    } else {
        snprintf(buf, sizeof(buf), "DHT:ERR");
    }
    SSD1306_GotoXY(0, 48);
    SSD1306_Puts(buf, &Font_7x10, SSD1306_COLOR_WHITE);

    SSD1306_GotoXY(0, 54);
    SSD1306_Puts("[3]Next [2]Reset", &Font_7x10, SSD1306_COLOR_WHITE); /* Key 3 returns to summary page */

    SSD1306_UpdateScreen();
}

/* ── Power save helpers ── */
static void EnterPowerSave(void) { power_save = 1; }
static void ExitPowerSave(void)  { power_save = 0; stable_secs = 0; }

/* Convert ultrasonic distance into water level (0..WL_DEPTH_CM). */
static float WaterLevel_Display(float distance_cm)
{
    float wl = WL_DEPTH_CM - distance_cm;
    if (wl < 0.0f) wl = 0.0f;
    if (wl > WL_DEPTH_CM) wl = WL_DEPTH_CM;
    return wl;
}

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */
  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */
  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */
  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_ADC1_Init();
  MX_I2C1_Init();
  MX_TIM1_Init();
  /* USER CODE BEGIN 2 */

  /* Set TIM1 prescaler to 71 → 1 tick = 1 us at 72 MHz */
  htim1.Init.Prescaler = 71;
  HAL_TIM_Base_Init(&htim1);
  HAL_TIM_Base_Start(&htim1);

  /* Fix PB9 (ROW2): MX_GPIO_Init leaves it as input; force to output */
  {
      GPIO_InitTypeDef g = {0};
      g.Pin   = GPIO_PIN_9;
      g.Mode  = GPIO_MODE_OUTPUT_PP;
      g.Pull  = GPIO_NOPULL;
      g.Speed = GPIO_SPEED_FREQ_LOW;
      HAL_GPIO_Init(GPIOB, &g);
      HAL_GPIO_WritePin(GPIOB, GPIO_PIN_9, GPIO_PIN_SET);
  }

  /* ADC self-calibration */
  HAL_ADCEx_Calibration_Start(&hadc1);

  /* OLED startup splash */
  SSD1306_Init();
  SSD1306_Fill(SSD1306_COLOR_BLACK);
  SSD1306_GotoXY(5, 10);
  SSD1306_Puts("FLOOD WARNING", &Font_11x18, SSD1306_COLOR_WHITE);
  SSD1306_GotoXY(25, 36);
  SSD1306_Puts("SYSTEM INIT...", &Font_7x10, SSD1306_COLOR_WHITE);
  SSD1306_UpdateScreen();
  HAL_Delay(2000);

  /* Initialise stats boundaries */
  stats.wl_min = 999.0f;  stats.wl_max = 0.0f;
  stats.rr_min = 999.0f;  stats.rr_max = 0.0f;
  stats.ri_min = 255;     stats.ri_max = 0;

  last_sample_ms = HAL_GetTick();
  last_dht_ms    = HAL_GetTick() - DHT_SAMPLE_MS; /* Force one DHT11 read soon after startup */
  last_sec_ms    = HAL_GetTick();

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    uint32_t now             = HAL_GetTick();
    uint32_t sample_interval = power_save ? PSAVE_MS : SAMPLE_MS;

    /* ── Sensor sampling ── */
    if (now - last_sample_ms >= sample_interval) {
        last_sample_ms = now;

        float prev_wl = water_level_cm;

        float raw_wl = HCSR04_Read_cm();                  /* HC-SR04 already returns median of 5 echo samples */
        if (raw_wl < ULTRA_MIN_CM || raw_wl > ULTRA_MAX_CM) {
            raw_wl = water_level_cm;                       /* Ignore invalid echo/timeout so it cannot fake danger */
        }
        raw_wl = WaterAvg_Push(raw_wl);                    /* Extra moving average reduces false ultrasonic triggers */
        if (!ultrasonic_ready) {                           /* First reading is accepted directly */
            water_level_cm = raw_wl;
            ultrasonic_ready = 1;
        } else {
            float diff = raw_wl - water_level_cm;          /* Difference between new raw value and old stable value */
            float ultra_alpha = 0.20f + (0.08f * (float)sys_sen);       /* Higher SYS_SEN = faster ultrasonic response */
            if (ultra_alpha > 1.0f) ultra_alpha = 1.0f;
            if (diff > -ultra_deadband_cm && diff < ultra_deadband_cm) {
                raw_wl = water_level_cm;                   /* Ignore tiny ultrasonic noise/jitter */
            }
            water_level_cm += ultra_alpha * (raw_wl - water_level_cm); /* Filter strength is controlled by SYS_SEN */
        }

        if (now - last_dht_ms >= DHT_SAMPLE_MS) {           /* DHT11 needs slow reads; 2 seconds is safer than 500 ms */
            last_dht_ms = now;
            dht_ok = DHT11_Read(&temperature_c, &humidity_pct); /* Keep old values if read fails */
        }
        soil_pct = Soil_Read();

        water_level_display_cm = WaterLevel_Display(water_level_cm);

        /* Rise rate (positive = water level rising toward sensor) */
        float dt_s    = (float)sample_interval / 1000.0f;
        float delta   = prev_wl - water_level_cm;
        rise_rate_cms = (delta > 0.0f) ? (delta / dt_s) : 0.0f;

        /* Composite Risk Index (0–100)
           New balance: 35% water, 15% rise, 20% humidity, 20% soil, 10% temperature.
           This keeps ultrasonic important but stops it from controlling almost everything. */
        float wl_inv = (float)WL_SAFE_CM - water_level_cm;
        if (wl_inv < 0.0f) wl_inv = 0.0f;
        uint8_t wl_s  = Normalise(wl_inv, 0.0f,
                                  (float)(WL_SAFE_CM - WL_EVAC_CM));
        uint8_t rr_s  = Normalise(rise_rate_cms, 0.0f, MAX_RISE_CMS);
        uint8_t hum_s = Normalise(humidity_pct,  60.0f, 95.0f);
        uint8_t tmp_s = Normalise(temperature_c, 25.0f, 35.0f);

        risk_index = (uint8_t)(0.35f * (float)wl_s
                             + 0.15f * (float)rr_s
                             + 0.20f * (float)hum_s
                             + 0.20f * (float)soil_pct
                             + 0.10f * (float)tmp_s);
        if (risk_index > 100) risk_index = 100;

        /* Trend engine */
        RingBuf_Push(&ri_buf, risk_index);
        float trend = LeastSquaresSlope(&ri_buf);

        prev_tier    = current_tier;
        current_tier = Classify(risk_index, trend);

        /* Auto-unmute on escalation */
        if (current_tier > prev_tier) buzzer_muted = 0;

        Stats_Update(water_level_display_cm, rise_rate_cms, risk_index);
    }

    /* ── 1-second tick: power-save counter ── */
    if (now - last_sec_ms >= 1000u) {
        last_sec_ms = now;
        if (current_tier == TIER_SAFE) {
            stable_secs++;
            if (stable_secs >= PSAVE_SECS) EnterPowerSave();
        } else {
            stable_secs = 0;
            ExitPowerSave();
        }
    }

    /* ── Outputs ── */
    LED_SetTier(current_tier);
    Buzzer_Update(current_tier);

    if (current_screen == SCREEN_SENSITIVITY &&
        sensitivity_screen_until != 0 &&
        now > sensitivity_screen_until) {
        current_screen = SCREEN_SENSORS;
        sensitivity_screen_until = 0;
    }

    if (current_screen == SCREEN_ULTRA_DB &&
        ultra_screen_until != 0 &&
        now > ultra_screen_until) {
        current_screen = SCREEN_SENSORS;
        ultra_screen_until = 0;
    }

    if (current_screen == SCREEN_SOIL_DRY &&
        soil_screen_until != 0 &&
        now > soil_screen_until) {
        current_screen = SCREEN_SENSORS;
        soil_screen_until = 0;
    }

    if (current_screen == SCREEN_MAIN) {
        OLED_MainScreen();
    } else if (current_screen == SCREEN_SENSORS) {
        OLED_SensorScreen();
    } else if (current_screen == SCREEN_STATS) {
        OLED_StatsScreen();
    } else if (current_screen == SCREEN_SENSITIVITY) {
        OLED_SensitivityScreen();
    } else if (current_screen == SCREEN_ULTRA_DB) {
        OLED_UltraDeadbandScreen();
    } else {
        OLED_SoilDryScreen();
    }

    /* ── Keypad ── */
    char key = Keypad_Scan();
    switch (key) {
        case '1':
            buzzer_muted = !buzzer_muted;             /* Key 1 turns buzzer mute on/off */
            break;
        case '2':
            if (current_screen == SCREEN_STATS) {     /* On stats page, key 2 clears saved min/max values */
                stats.wl_min = 999.0f;  stats.wl_max = 0.0f; /* Reset water-level min/max */
                stats.rr_min = 999.0f;  stats.rr_max = 0.0f; /* Reset rise-rate min/max */
                stats.ri_min = 255;     stats.ri_max = 0;    /* Reset risk-index min/max */
            } else {
                NVIC_SystemReset();                   /* On other pages, key 2 restarts the board */
            }
            break;
        case '3':
            current_screen = (current_screen == SCREEN_MAIN) ? SCREEN_SENSORS : SCREEN_MAIN; /* Key 3 swaps live pages */
            break;
        case '4':
            current_screen = SCREEN_STATS;                 /* Key 4 opens dedicated min/max statistics menu */
            break;
        case '5':
            if (sys_sen > SYS_SEN_MIN) sys_sen--;          /* Key 5 lowers sensitivity if it is above minimum */
            current_screen = SCREEN_SENSITIVITY;            /* Show SYS_SEN screen immediately after changing it */
            sensitivity_screen_until = HAL_GetTick() + 2000u; /* Keep sensitivity screen visible for 2 seconds */
            break;
        case '6':
            if (sys_sen < SYS_SEN_MAX) sys_sen++;          /* Key 6 raises sensitivity if it is below maximum */
            current_screen = SCREEN_SENSITIVITY;            /* Show SYS_SEN screen immediately after changing it */
            sensitivity_screen_until = HAL_GetTick() + 2000u; /* Keep sensitivity screen visible for 2 seconds */
            break;
        case '7':
            if (ultra_deadband_cm > ULTRA_DB_MIN) ultra_deadband_cm -= ULTRA_DB_STEP;
            if (ultra_deadband_cm < ULTRA_DB_MIN) ultra_deadband_cm = ULTRA_DB_MIN;
            current_screen = SCREEN_ULTRA_DB;
            ultra_screen_until = HAL_GetTick() + 2000u;
            break;
        case '9':
            if (ultra_deadband_cm < ULTRA_DB_MAX) ultra_deadband_cm += ULTRA_DB_STEP;
            if (ultra_deadband_cm > ULTRA_DB_MAX) ultra_deadband_cm = ULTRA_DB_MAX;
            current_screen = SCREEN_ULTRA_DB;
            ultra_screen_until = HAL_GetTick() + 2000u;
            break;
        case '8':
            if (soil_dry_adc > SOIL_DRY_MIN) soil_dry_adc -= SOIL_DRY_STEP;
            if (soil_dry_adc < SOIL_DRY_MIN) soil_dry_adc = SOIL_DRY_MIN;
            current_screen = SCREEN_SOIL_DRY;
            soil_screen_until = HAL_GetTick() + 2000u;
            break;
        case '0':
            if (soil_dry_adc < SOIL_DRY_MAX) soil_dry_adc += SOIL_DRY_STEP;
            if (soil_dry_adc > SOIL_DRY_MAX) soil_dry_adc = SOIL_DRY_MAX;
            current_screen = SCREEN_SOIL_DRY;
            soil_screen_until = HAL_GetTick() + 2000u;
            break;
        case '*':
            ExitPowerSave();                          /* Star key wakes the screen from power-save mode */
            break;
        default:
            break;
    }

    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
  RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_ADC;
  PeriphClkInit.AdcClockSelection = RCC_ADCPCLK2_DIV6;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief ADC1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_ADC1_Init(void)
{

  /* USER CODE BEGIN ADC1_Init 0 */

  /* USER CODE END ADC1_Init 0 */

  ADC_ChannelConfTypeDef sConfig = {0};

  /* USER CODE BEGIN ADC1_Init 1 */

  /* USER CODE END ADC1_Init 1 */

  /** Common config
  */
  hadc1.Instance = ADC1;
  hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
  hadc1.Init.ContinuousConvMode = ENABLE;
  hadc1.Init.DiscontinuousConvMode = DISABLE;
  hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
  hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc1.Init.NbrOfConversion = 1;
  if (HAL_ADC_Init(&hadc1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Regular Channel
  */
  sConfig.Channel = ADC_CHANNEL_0;
  sConfig.Rank = ADC_REGULAR_RANK_1;
  sConfig.SamplingTime = ADC_SAMPLETIME_1CYCLE_5;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN ADC1_Init 2 */

  /* USER CODE END ADC1_Init 2 */

}

/**
  * @brief I2C1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C1_Init(void)
{

  /* USER CODE BEGIN I2C1_Init 0 */

  /* USER CODE END I2C1_Init 0 */

  /* USER CODE BEGIN I2C1_Init 1 */

  /* USER CODE END I2C1_Init 1 */
  hi2c1.Instance = I2C1;
  hi2c1.Init.ClockSpeed = 400000;
  hi2c1.Init.DutyCycle = I2C_DUTYCYCLE_2;
  hi2c1.Init.OwnAddress1 = 0;
  hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c1.Init.OwnAddress2 = 0;
  hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN I2C1_Init 2 */

  /* USER CODE END I2C1_Init 2 */

}

/**
  * @brief TIM1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM1_Init(void)
{

  /* USER CODE BEGIN TIM1_Init 0 */

  __HAL_RCC_TIM1_CLK_ENABLE();
  /* USER CODE END TIM1_Init 0 */

  TIM_ClockConfigTypeDef sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};

  /* USER CODE BEGIN TIM1_Init 1 */

  /* USER CODE END TIM1_Init 1 */
  htim1.Instance = TIM1;
  htim1.Init.Prescaler = 0;
  htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim1.Init.Period = 65535;
  htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim1.Init.RepetitionCounter = 0;
  htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim1) != HAL_OK)
  {
    Error_Handler();
  }
  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim1, &sClockSourceConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim1, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM1_Init 2 */

  /* USER CODE END TIM1_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */
  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_1|GPIO_PIN_2|GPIO_PIN_5|GPIO_PIN_6
                          |GPIO_PIN_7|GPIO_PIN_8|GPIO_PIN_9, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0|GPIO_PIN_10|GPIO_PIN_11|GPIO_PIN_8, GPIO_PIN_RESET);

  /*Configure GPIO pins : PA1 PA2 PA5 PA6
                           PA7 PA8 PA9 */
  GPIO_InitStruct.Pin = GPIO_PIN_1|GPIO_PIN_2|GPIO_PIN_5|GPIO_PIN_6
                          |GPIO_PIN_7|GPIO_PIN_8|GPIO_PIN_9;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /*Configure GPIO pin : PA3 */
  GPIO_InitStruct.Pin = GPIO_PIN_3;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /*Configure GPIO pins : PB0 PB10 PB11 PB8 */
  GPIO_InitStruct.Pin = GPIO_PIN_0|GPIO_PIN_10|GPIO_PIN_11|GPIO_PIN_8;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  /*Configure GPIO pins : PB12 PB13 PB14 PB15 */
  GPIO_InitStruct.Pin = GPIO_PIN_12|GPIO_PIN_13|GPIO_PIN_14|GPIO_PIN_15;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_PULLUP;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  /*Configure GPIO pin : PB9 */
  GPIO_InitStruct.Pin = GPIO_PIN_9;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */
  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */
/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  __disable_irq();
  while (1) {}
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
