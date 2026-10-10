# Wiring: ESP32-S3 Super Mini + 0.91" OLED + microSD module

Verified working on real hardware (OLED answers at I2C 0x3C; SD card mounts, writes and reads back a file).
Pin numbers are GPIO numbers. They are chosen from pins with no boot or USB role; the SPI and I2C pins are set explicitly in code, not taken from defaults.

| Module pin | ESP32-S3 Super Mini |
|:--|:--|
| OLED SDA | GPIO5 |
| OLED SCL | GPIO6 |
| OLED VCC, GND | 3V3, GND |
| SD CS | GPIO1 |
| SD CLK (SCK) | GPIO2 |
| SD MOSI | GPIO4 |
| SD MISO | GPIO7 |
| SD 3V3, GND | 3V3, GND |

Notes
- The SD module used here has a 3V3 pin (no regulator or level shifter): power it from 3V3, never 5V. A module with a regulator and level shifter would want 5V instead.
- Use a FAT32 microSD card of 32 GB or less. Insert or remove it with USB unplugged.
- Keep clear of GPIO0, 3, 45, 46 (boot), 19/20 (USB), 26-32 (flash) and 48 (onboard LED).
- Build with `--board-options CDCOnBoot=cdc`; needs the U8g2 library. The test sketch replaces `ring_host` on the board; re-flash `ring_host` afterwards.
