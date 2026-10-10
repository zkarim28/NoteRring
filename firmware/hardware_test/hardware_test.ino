// Wiring test for the OLED (SSD1306 128x32, I2C) and the microSD module (SPI) on an ESP32-S3 Super Mini.
// Replaces ring_host on the board while you test; re-flash ring_host afterwards.
// Results go to the OLED and to Serial (115200). Build with CDCOnBoot=cdc. Needs the U8g2 library.
//
// Pins (change here if your wiring differs; numbers are GPIO numbers):
#define OLED_SDA 5
#define OLED_SCL 6
#define SD_CS    1
#define SD_SCK   2
#define SD_MOSI  4
#define SD_MISO  7

#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <U8g2lib.h>

U8G2_SSD1306_128X32_UNIVISION_F_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE, OLED_SCL, OLED_SDA);
SPIClass sdSpi(FSPI);

static String lines[4];
static void show(int row, const String& s) {
  lines[row] = s;
  Serial.println(s);
  oled.clearBuffer();
  oled.setFont(u8g2_font_6x10_tf);
  for (int i = 0; i < 4; i++) oled.drawStr(0, 8 + i * 8, lines[i].c_str());
  oled.sendBuffer();
}

static bool i2cSeen(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("\n== hardware test ==");

  // 1) OLED: is anything answering on the I2C bus?
  Wire.begin(OLED_SDA, OLED_SCL);
  bool found3c = i2cSeen(0x3C), found3d = i2cSeen(0x3D);
  Serial.printf("I2C: 0x3C %s, 0x3D %s\n", found3c ? "ANSWERS" : "no answer", found3d ? "ANSWERS" : "no answer");
  if (found3d && !found3c) oled.setI2CAddress(0x3D << 1);
  oled.begin();
  show(0, "OLED OK (I2C 0x3C)");
  if (!found3c && !found3d) Serial.println("  -> nothing answered: check SDA/SCL wires, VCC and GND (the screen may still be blank)");

  // 2) SD card
  show(1, "SD: starting...");
  sdSpi.begin(SD_SCK, SD_MISO, SD_MOSI, SD_CS);
  if (!SD.begin(SD_CS, sdSpi, 4000000)) {
    show(1, "SD: NOT FOUND");
    show(2, "check card + wires");
    show(3, "CS1 CLK2 MOSI4 MISO7");
    return;
  }
  uint8_t type = SD.cardType();
  const char* names[] = {"none", "MMC", "SD", "SDHC", "unknown"};
  show(1, String("SD ") + names[type < 4 ? type : 4] + " " + String((uint32_t)(SD.cardSize() / (1024 * 1024))) + "MB");

  // 3) write a file, read it back
  String stamp = "ring-writer test, uptime ms: " + String(millis());
  File f = SD.open("/hwtest.txt", FILE_WRITE);
  if (!f) { show(2, "SD: cannot write"); return; }
  f.println(stamp);
  f.close();
  f = SD.open("/hwtest.txt", FILE_READ);
  String back = "";
  while (f && f.available()) back = f.readStringUntil('\n');
  if (f) f.close();
  back.trim();
  bool ok = back.length() > 0 && back.startsWith("ring-writer test");
  show(2, ok ? "SD write+read OK" : "SD read MISMATCH");
  show(3, ok ? "ALL GOOD" : "see serial output");
  Serial.printf("last line read back: %s\n", back.c_str());
}

void loop() { delay(1000); }
