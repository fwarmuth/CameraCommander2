# Firmware Serial Protocol — CameraCommander2

**Branch**: `001-core-system` | **Date**: 2026-05-09
**Authoritative for**: ESP8266/ESP32 firmware ↔ Python host
**Status**: v1 (compatible with the existing `1.0.1` firmware)

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
| Direction | Half-duplex turn-taking: host issues a single command line, then waits for one reply line |

The mock firmware exposes the same protocol over a TCP socket. The host reaches it by passing `port: socket://127.0.0.1:9999` to the serial adapter (pyserial URL handler).

---

## 2. Versioning

- **Format**: SemVer string, e.g. `1.0.1`.
- **Discovery**: the host issues `V` immediately after opening the link. The firmware MUST reply `VERSION x.y.z`. The host then compares `x` (major) against the operator-configured `expected_protocol_major`. If mismatched, the host disconnects, marks the tripod connection `error`, and reports the mismatch to the operator (SC-008).
- **Backwards compatibility**: within a major version, new commands are additive. Hosts written against an older minor MUST tolerate (and ignore) unrecognised banner lines and unrecognised `OK ...` suffixes.
- **Reservation**: command tokens are case-insensitive single ASCII letters (or `+`/`-`); future versions MUST NOT repurpose a token. New commands take an unused letter.

The current contract is `v1.0.x` (matches the firmware in `old_implementation/firmware/src/main.cpp`).

---

## 3. Boot banner

After `Serial.begin(9600)` and a brief settle delay, the firmware emits a multi-line banner that begins with the literal:

```
Dual-axis turntable – firmware <FW_VERSION>
```

Hosts MUST NOT depend on the banner. They SHOULD drain whatever is in the receive buffer for up to 250 ms before sending `V`.

---

## 4. Commands and replies

Tokens are case-insensitive unless noted. Numeric arguments use ASCII decimal with optional sign and decimal point (e.g. `-12.345`).

### 4.1 `V` — Firmware version

- **Request**: `V\n`
- **Reply**: `VERSION <major>.<minor>.<patch>\n`
- **Notes**: idempotent. Always answered, even when drivers are disabled.

### 4.2 `M <pan_deg> <tilt_deg>` — Absolute move

- **Request**: `M 30.000000 -5.250000\n`
- **Reply**: `DONE\n` once both axes have reached the target and the firmware-internal settle delay has elapsed.
- **Pre-conditions**: drivers enabled (`e`). When disabled, the firmware does not move and replies `ERR DRIVERS_DISABLED` (planned addition; v1.0.x emits no reply because the host-side guard rejects the call).
- **Semantics**: angles are absolute relative to the firmware's current position counter; the counter is zeroed by `e`/`d` (driver toggle) and is otherwise persistent across moves.
- **Synchronous**: firmware blocks (yielding) until motion completes; this is what makes the `Q` query historically unnecessary.

### 4.3 `S` — Status

- **Request**: `S\n`
- **Reply**: `STATUS <pan_deg> <tilt_deg> <drivers>\n` where:
  - `<pan_deg>` and `<tilt_deg>` are signed floats (3-decimal precision suffices in v1).
  - `<drivers>` is `1` (enabled) or `0` (disabled).
- **Notes**: hosts treat any other prefix as a protocol error and disconnect.

### 4.4 Microstep selection — `1`, `2`, `4`, `8`, `6`

- **Request**: a single token; `6` means microstep-16 (token chosen for keypad ergonomics on the original PCB).
- **Reply**: `OK MICROSTEP <res>\n`.
- **Effect**: applied to both axes simultaneously.

### 4.5 Pan-axis helpers

| Token | Meaning | Reply |
|---|---|---|
| `n` / `N` | Single µ-step in current pan direction | `OK ROT STEP\n` |
| `c` / `C` | Full revolution in current pan direction | `OK ROT REV\n` |
| `r` / `R` | Toggle pan direction sign | `OK ROT DIR\n` |
| `x` | Stop pan axis | `OK ROT STOP\n` |

### 4.6 Tilt-axis helpers

| Token | Meaning | Reply |
|---|---|---|
| `w` / `W` | Single µ-step in current tilt direction | `OK TILT STEP\n` |
| `p` / `P` | Full revolution in current tilt direction | `OK TILT REV\n` |
| `t` / `T` | Toggle tilt direction sign | `OK TILT DIR\n` |
| `z` | Stop tilt axis | `OK TILT STOP\n` |

### 4.7 `X` — Global stop (emergency)

- **Request**: `X\n`
- **Reply**: `OK STOP\n`
- **Effect**: both axes decelerate to zero. The position counter is **not** reset; the host considers calibration `unknown` after `X` because the operator usually intervenes physically.

### 4.8 `+` / `-` — Speed adjust

- **Request**: `+\n` or `-\n`
- **Reply**: `OK SPEED\n`
- **Effect**: scales both axes' speed and acceleration by ±10 %.

### 4.9 `d` / `e` — Driver disable / enable

- **Request**: `d\n` or `e\n`
- **Reply**: `OK DRIVERS OFF\n` or `OK DRIVERS ON\n`
- **Effect**: also resets the firmware position counter to (0, 0). Hosts treat this as `calibration.state = unknown` (FR-011).

---

## 5. Error replies

Any reply beginning with `ERR ` is a protocol-level failure. Defined codes:

| Reply | Cause |
|---|---|
| `ERR Syntax\n` | Command parse failure (e.g. wrong arity for `M`). |
| `ERR Unknown\n` | Unrecognised command token. |
| `ERR DRIVERS_DISABLED\n` | Move attempted with drivers off (planned for `1.1.x`; host-side guard prevents this in v1.0.x). |

Hosts MUST log the error code, mark the operation failed, and surface a `tripod.error` fault to the operator.

---

### 6. Timing budget

| Operation | Host-side allowance |
|---|---|
| Open link + drain banner + receive `VERSION` reply | 1 s |
| `S` round trip | 200 ms |
| `M` round trip (initial / between progress) | `safety.move_timeout_margin_s` (default `2 s`); deadline is refreshed by each `PROGRESS` message. |
| Microstep / driver / step / speed commands | 200 ms |
| `X` round trip | 500 ms |


Exceeding these budgets fires a `motor_stall` or `serial_lost` fault (host-side; the spec edge case treats them identically).

---

## 7. Mock firmware conformance

The Python TCP server in `host/src/cameracommander/mock_firmware/server.py` MUST emit byte-identical replies. It SHOULD also support test-only flags:

- `--deg-per-second` — simulate motion time so `M` round-trips reflect real-world latency.
- `--initial-pan` / `--initial-tilt` / `--microstep` / `--drivers-disabled` — preset state for repeatable tests.
- `--fw-version` — override `VERSION` reply (used to test SC-008 mismatch handling).

A protocol unit test in `host/tests/contract/test_firmware_protocol.py` MUST run against both the mock TCP server and a `pyserial`-loopback fixture and assert byte-for-byte responses.
-deg-per-second` — simulate motion time so `M` round-trips reflect real-world latency.
- `--initial-pan` / `--initial-tilt` / `--microstep` / `--drivers-disabled` — preset state for repeatable tests.
- `--fw-version` — override `VERSION` reply (used to test SC-008 mismatch handling).

A protocol unit test in `host/tests/contract/test_firmware_protocol.py` MUST run against both the mock TCP server and a `pyserial`-loopback fixture and assert byte-for-byte responses.
