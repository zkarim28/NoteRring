// ESP32-S3 as a BLE HID host (central) for the D06 ring.
// Prints each mouse report as a line the Python side parses:  [id 3 h45] 00 07 00 20 00 00 -> btn=00 dx=7 dy=32 wheel=0
// Scans for "D06", bonds, subscribes to every HID Report notification and prints raw bytes.
// Needs NimBLE-Arduino 2.x. Build with CDCOnBoot=cdc so Serial shows up over native USB.
//
// Heat: runs the CPU at 80 MHz (BLE and this job need very little compute) and prints the chip's own temperature every
// 10 s as a comment line ("# temp 41.2 C, cpu 80 MHz"); the Python side ignores lines that start with '#'.
// Each report is formatted into one buffer and written once, instead of ~20 separate USB writes.
#include <NimBLEDevice.h>

#ifndef RING_CPU_MHZ
#define RING_CPU_MHZ 80
#endif
static uint32_t lastTempMs = 0;

static void printTemperature() {
  if (millis() - lastTempMs < 10000) return;
  lastTempMs = millis();
  Serial.printf("# temp %.1f C, cpu %u MHz\n", temperatureRead(), (unsigned)getCpuFrequencyMhz());
}

static const char* TARGET_NAME = "D06";  // substring match on advertised name
static const NimBLEUUID HID_SVC((uint16_t)0x1812);
static const NimBLEUUID REPORT_CHR((uint16_t)0x2A4D);
static const NimBLEUUID REPORT_REF((uint16_t)0x2908);

static NimBLEAddress targetAddr;
static bool haveTarget = false;
static NimBLEClient* client = nullptr;

class ScanCB : public NimBLEScanCallbacks {
  void onResult(const NimBLEAdvertisedDevice* d) override {
    bool nameMatch = d->haveName() && d->getName().find(TARGET_NAME) != std::string::npos;
    bool hidMatch = d->isAdvertisingService(HID_SVC);
    if (nameMatch || hidMatch) {
      Serial.printf("Found %s  %s  rssi=%d  hid=%d\n", d->getName().c_str(),
                    d->getAddress().toString().c_str(), d->getRSSI(), hidMatch);
      if (nameMatch) {  // only auto-pick by name; HID-only matches are just listed
        targetAddr = d->getAddress();
        haveTarget = true;
        NimBLEDevice::getScan()->stop();
      }
    }
  }
} scanCB;

class ClientCB : public NimBLEClientCallbacks {
  void onConnect(NimBLEClient*) override { Serial.println("Connected"); }
  void onDisconnect(NimBLEClient*, int reason) override {
    Serial.printf("Disconnected (reason %d), will rescan\n", reason);
  }
  void onAuthenticationComplete(NimBLEConnInfo& info) override {
    Serial.printf("Auth done: encrypted=%d bonded=%d\n", info.isEncrypted(), info.isBonded());
  }
} clientCB;

// Notification callback. Report ID/type comes from each characteristic's Report Reference.
// IDs are read once at subscribe time: a GATT read inside the callback blocks the BLE stack
// and exhausts its buffers.
struct RefEntry { uint16_t handle; uint8_t id; };
static RefEntry refs[8];
static int nRefs = 0;

static void onReport(NimBLERemoteCharacteristic* c, uint8_t* data, size_t len, bool) {
  uint8_t id = 0xFF;
  for (int i = 0; i < nRefs; i++) if (refs[i].handle == c->getHandle()) id = refs[i].id;
  char line[128];
  int n = snprintf(line, sizeof(line), "[id %u h%u] ", id, c->getHandle());
  for (size_t i = 0; i < len && n < (int)sizeof(line) - 48; i++) n += snprintf(line + n, sizeof(line) - n, "%02x ", data[i]);
  // Mouse decode (mouse report 3 of the D06's HID descriptor): buttons, dx16, dy16, wheel8
  if (id == 3 && len >= 6) {
    int16_t dx = (int16_t)(data[1] | (data[2] << 8));
    int16_t dy = (int16_t)(data[3] | (data[4] << 8));
    n += snprintf(line + n, sizeof(line) - n, " -> btn=%02x dx=%d dy=%d wheel=%d", data[0], dx, dy, (int8_t)data[5]);
  }
  line[n++] = '\n';
  Serial.write((const uint8_t*)line, n);                 // one USB write per report
}

static bool connectRing() {
  client = NimBLEDevice::createClient();
  client->setClientCallbacks(&clientCB, false);
  client->setConnectTimeout(10);
  if (!client->connect(targetAddr)) {
    Serial.println("Connect failed");
    NimBLEDevice::deleteClient(client);
    client = nullptr;
    return false;
  }
  // HID characteristics are encrypted, so make sure we are bonded before subscribing.
  if (!client->secureConnection()) Serial.println("secureConnection failed (continuing)");

  NimBLERemoteService* svc = client->getService(HID_SVC);
  if (!svc) {
    Serial.println("No HID service");
    client->disconnect();
    return false;
  }
  int n = 0;
  nRefs = 0;
  for (auto* c : svc->getCharacteristics(true)) {
    if (c->getUUID() == REPORT_CHR && c->canNotify()) {
      uint8_t id = 0xFF, type = 0xFF;
      NimBLERemoteDescriptor* ref = c->getDescriptor(REPORT_REF);
      if (ref) {
        std::string v = ref->readValue();
        if (v.size() >= 2) { id = (uint8_t)v[0]; type = (uint8_t)v[1]; }
      }
      if (nRefs < 8) refs[nRefs++] = {c->getHandle(), id};
      Serial.printf("Report char h%u: id=%u type=%u\n", c->getHandle(), id, type);
      if (c->subscribe(true, onReport)) n++;
    }
  }
  Serial.printf("Subscribed to %d HID report characteristics. Use the ring now.\n", n);
  return n > 0;
}

void setup() {
  setCpuFrequencyMhz(RING_CPU_MHZ);
  Serial.begin(115200);
  delay(1500);
  Serial.println("ESP32-S3 BLE HID host for D06");
  NimBLEDevice::init("esp32s3-host");
  NimBLEDevice::setSecurityAuth(true, false, true);  // bond, no MITM, secure connections
  NimBLEDevice::setSecurityIOCap(BLE_HS_IO_NO_INPUT_OUTPUT);
}

void loop() {
  printTemperature();
  if (client && client->isConnected()) {
    delay(500);
    return;
  }
  haveTarget = false;
  Serial.println("Scanning 8 s... (put the ring in pairing mode / wake it)");
  NimBLEScan* scan = NimBLEDevice::getScan();
  scan->setScanCallbacks(&scanCB, false);
  scan->setActiveScan(true);
  scan->start(8000, false);
  while (scan->isScanning()) delay(100);
  if (haveTarget) connectRing();
  else delay(1000);
}
