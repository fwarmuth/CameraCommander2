# Firmware Serial Protocol — CameraCommander2

**Branch**: `004-movement-feedback` | **Date**: 2026-05-10
**Authoritative for**: ESP8266/ESP32 firmware ↔ Python host
**Status**: v1.1 (Movement feedback & non-blocking motion)

This contract defines the line-oriented ASCII protocol the firmware exposes over its serial UART. The host (Python) and the mock firmware server (Python TCP) MUST both speak it byte-for-byte. SemVer governs evolution: a major bump means hosts written against an earlier major MUST refuse to drive the firmware (FR-014, SC-008).

---

## 1. Transport

| Property | Value |
|---|---|
| Layer | Single UART, full duplex |
| Baud rate | `9600` (firmware default; configurable in firmware build) |
| Data framing | `8N1`, no flow control |
| Line terminator | `\n` (`0x0A`); the firmware tolerates `\r\n` on input but emits `\n` only |
| Encoding | 7-bit ASCII; no UTF-8, no escapes |
| Direction | Half-duplex turn-taking: host issues a single command line, then waits for one or more reply lines |

The mock firmware exposes the same protocol over a TCP socket. The host reaches it by passing `port: socket://127.0.0.1:9999` to the serial adapter (pyserial URL handler).

---

## 2. Versioning

- **Format**: SemVer string, e.g. `1.1.0`.
- **Discovery**: the host issues `V` immediately after opening the link. The firmware MUST reply `VERSION x.y.z`.
- **Backwards compatibility**: within a major version, new commands are additive. Hosts MUST tolerate (and ignore) unrecognized `OK ...` suffixes and MUST tolerate intermediate `PROGRESS` and `ESTIMATE` lines during `M` command processing.

---

## 3. Boot banner

After `Serial.begin(9600)` and a brief settle delay, the firmware emits a multi-line banner that begins with the literal:

```
Dual-axis turntable - firmware <FW_VERSION>
```

---

## 4. Commands and replies

### 4.2 `M <pan_deg> <tilt_deg>` — Absolute move

- **Request**: `M 30.000000 -5.250000\n`
- **Immediate Reply**: `ESTIMATE <seconds>\n` — emitted immediately after command parsing, before motion begins.
- **Progress**: While moving, the firmware SHOULD emit `PROGRESS <pan_deg> <tilt_deg>\n` lines periodically (every 200ms).
- **Final Reply**: `DONE\n` once both axes have reached the target and the firmware-internal settle delay has elapsed.
- **Pre-conditions**: drivers enabled (`e`). If the target is identical to the current position, the firmware MUST reply `ERR AlreadyAtTarget` and return to idle.
- **Concurrent Commands**: The firmware MUST remain responsive to `X` (Global Stop) and `S` (Status) during movement.

### 4.3 `S` — Status

- **Request**: `S\n`
- **Reply**: `STATUS <pan_deg> <tilt_deg> <drivers>\n` where:
  - `<pan_deg>` and `<tilt_deg>` are signed floats.
  - `<drivers>` is `1` (enabled) or `0` (disabled).

### 4.4 `ESTIMATE <seconds>` — Motion duration estimate

- **Format**: `ESTIMATE 15.4\n`
- **Context**: Emitted by firmware immediately after a valid `M` command.
- **Host behavior**: Used to set initial UI feedback and adjust internal watchdog margins.

### 4.5 `PROGRESS <pan_deg> <tilt_deg>` — Intermediate feedback

- **Format**: `PROGRESS 12.345 -2.000\n`
- **Context**: Emitted by firmware during `M` command processing at 5Hz.
- **Host behavior**: MUST refresh its command timeout deadline.

---

## 5. Error replies

| Reply | Cause |
|---|---|
| `ERR Syntax\n` | Command parse failure (e.g. wrong arity for `M`). |
| `ERR Unknown\n` | Unrecognized command token. |
| `ERR DRIVERS_DISABLED\n` | Move attempted with drivers off. |
| `ERR AlreadyAtTarget\n` | `M` command issued to the current position. |
| `ERR MotorStall\n` | Motion stopped prematurely before reaching target. |

---

## 6. Timing budget

| Operation | Host-side allowance |
|---|---|
| Open link + drain banner + receive `VERSION` reply | 1 s |
| `S` round trip | 200 ms |
| `M` round trip (initial / between progress) | `safety.move_timeout_margin_s` (default `2 s`); deadline is refreshed by each `PROGRESS` line. |
| Microstep / driver / step / speed commands | 200 ms |
| `X` round trip | 500 ms |
