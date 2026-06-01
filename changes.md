# Changes

## Display and keypad
- Added keypad-selectable OLED pages.
- Key `3` swaps between the summary page and all-sensor live data page.
- Key `4` opens the dedicated min/max statistics menu.
- Key `2` resets min/max statistics only while the statistics menu is open.
- Key `5` decreases `SYS_SEN`.
- Key `6` increases `SYS_SEN`.
- OLED menu shows `SYS_SEN` so the active sensitivity can be checked while running.
- Added a temporary sensitivity screen that appears after pressing `5` or `6`.

## Sensor display
- Added live display of water level, rise rate, temperature, humidity, soil moisture, Risk Index, and alert tier.
- Added a dedicated all-sensor OLED page.
- Revised the all-sensor page so water level, rise rate, temperature, humidity, soil moisture, Risk Index, tier, and `SYS_SEN` are all visible.
- Added a dedicated min/max OLED page for water level, rise rate, and Risk Index.
- Replaced OLED float `printf` formatting with integer-based formatting helpers so water level, rise rate, temperature, and humidity display correctly with STM32 `nano.specs`.
- Increased OLED formatting buffers to remove GCC `-Wformat-truncation` warnings during STM32CubeIDE builds.
- DHT11 is now sampled every 2 seconds instead of every 500 ms, because reading it too fast can cause failed readings.
- Added `DHT:ERR` display when DHT11 communication/checksum fails, so failed reads do not look like real `0` values.

## Filtering and false-trigger reduction
- HC-SR04 ultrasonic water level now uses median filtering inside `HCSR04_Read_cm()`.
- HC-SR04 water level also uses an 8-sample moving average after the median filter.
- Invalid HC-SR04 readings outside the accepted range are ignored.
- Small HC-SR04 changes are ignored using an adjustable deadband controlled by `SYS_SEN`.
- Soil moisture ADC readings use an 8-sample moving average before converting to percent.

- Risk Index weighting was adjusted so ultrasonic water level is highly important.
- Current weights: 55% water level, 31% soil moisture, 7% rise rate, 5% humidity, 2% temperature.
- The predictive trend engine was removed. Tier classification uses the raw risk_index directly.
- Value normalizing clamps were removed so that extreme danger (e.g., water distance extremely close to the sensor) can push the Risk Index naturally to 100 regardless of the other sensors.
- Removed the exponential alpha filter from the ultrasonic reading pipeline. The system now uses median + 8-sample moving average + deadband only. This fixes the bug where EVACUATE appeared briefly then disappeared because the alpha filter was preventing water_level_cm from converging to the real distance.
- Warning LEDs were changed so both yellow LEDs do not light together.
- Danger mode now blinks the red LEDs only.
- OLED danger mode uses flashing/inverted display because the SSD1306 OLED is monochrome.

## Notes
- The project has two `main.c` copies: root `main.c` and `Core/Src/main.c`.
- STM32CubeIDE builds `Core/Src/main.c`, so changes were kept mirrored in both files.
