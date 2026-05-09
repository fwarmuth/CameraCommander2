# firmware/

ESP8266 / ESP32 firmware for the CameraCommander2 motorised pan-tilt head.
Built with PlatformIO (`pio run`) against the Arduino framework.

The serial line protocol is documented in
[`specs/001-core-system/contracts/firmware-protocol.md`](../specs/001-core-system/contracts/firmware-protocol.md).

## Quick build

```bash
cd firmware
pio run                  # default env: nodemcuv2 (ESP8266)
pio run -e esp32         # alternate target
pio run --target upload  # flash whatever board is attached
pio device monitor       # watch the boot banner and protocol traffic
```

Native unit tests (no hardware required):

```bash
pio test -e native
```
