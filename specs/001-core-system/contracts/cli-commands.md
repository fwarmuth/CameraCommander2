# CLI Contract — `cameracommander`

**Branch**: `001-core-system` | **Date**: 2026-05-09
**Authoritative for**: Typer-based command-line interface in `host/src/cameracommander/cli/`

The CLI is mandated by FR-034 and FR-035: every core workflow (test capture, manual tripod control, timelapse execution, configuration validation, mock startup) must be available without the web UI, and CLI commands must use the same services as the API. Subcommands import lazily — `cameracommander --help` MUST NOT load `gphoto2` or `pyserial`.

Run as `uv run cameracommander <subcommand> [...]` during development or `cameracommander <subcommand> [...]` once installed.

---

## Global flags

| Flag | Default | Effect |
|---|---|---|
| `--log-level [trace\|debug\|info\|warn\|error]` | `info` | Sets the loguru sink level. |
| `--log-file <path>` | `~/.cameracommander/logs/host.log` | Path for the file sink (rotated daily). Use `-` to log only to stderr. |
| `--no-banner` | off | Suppress the Pi-friendly ASCII banner on startup. |
| `--version` | — | Print host SemVer and exit. |

---

## `cameracommander snapshot`

Capture a single still image. Mirrors `POST /api/camera/capture` but writes the image directly to disk.

```
cameracommander snapshot [OPTIONS] [CONFIG] OUTPUT
```

| Argument / Option | Type | Required | Notes |
|---|---|---|---|
| `CONFIG` | path | no | YAML configuration. If supplied, only the `camera` block is honoured (settings applied before capture). |
| `OUTPUT` | path | yes | File path or directory. If a directory, the filename is `capture_<unix>.<ext>` matching the camera output. |
| `--model-substring TEXT` | string | no | Selects a connected camera by model substring (FR-001). Overrides the value in the config. |
| `--no-autofocus / --autofocus` | flag | no | Default `--no-autofocus` (matches `capture_image_no_af`). |

**Exit codes**

| Code | Meaning |
|---|---|
| `0` | Capture succeeded; final path printed to stdout. |
| `2` | Validation error (bad config, unwritable output dir). |
| `10` | Camera not found / not connectable. |
| `11` | Capture failed (gphoto2 error). |

Example: `cameracommander snapshot settings.yaml ./testshot.jpg`

---

## `cameracommander tripod`

Interactive tripod control (REPL). Continues the old-implementation `tripod` shell.

```
cameracommander tripod CONFIG
```

`CONFIG` is required and must contain a `tripod` block. The command does **not** require calibration to be `homed` — manual nudges are allowed even when calibration is `unknown` (a warning is logged).

REPL inputs:
- `<pan_deg> <tilt_deg>` — relative move, e.g. `5 -2`
- `to <pan_deg> <tilt_deg>` — absolute move
- `home` — set the current physical position as `(0, 0)`
- `e` / `d` — enable / disable drivers
- `s` — print status (pan, tilt, drivers, calibration)
- `stop` — emergency stop
- `q` / `quit` / `exit` — leave the loop

Exit codes mirror `snapshot` but use `12` and `13` for tripod-specific failures.

---

## `cameracommander timelapse`

Run a complete timelapse session. Equivalent to `POST /api/jobs/timelapse` followed by waiting for terminal status.

```
cameracommander timelapse [OPTIONS] CONFIG
```

| Argument / Option | Type | Required | Notes |
|---|---|---|---|
| `CONFIG` | path | yes | Full session YAML (`metadata`, `camera`, `tripod`, `safety`, `output`, `sequence: kind=timelapse`). |
| `--no-video` | flag | no | Override `output.video.assemble` to `false`. |
| `--dry-run` | flag | no | Validate the config, run safety + calibration gates, exit without capturing. |
| `--mock` | flag | no | Implies `--mock-camera` and `--mock-tripod` (sets the adapters before the runner starts). |
| `--mock-camera` | flag | no | Use `MockCameraAdapter` regardless of config. |
| `--mock-tripod` | flag | no | Force tripod port to `socket://127.0.0.1:9999` (the default mock firmware). |

Progress is rendered as a single line `Captured X/Y (Z%)` updated in place. After capture, the rendered video path (or "—") is printed to stdout.

**Exit codes**

| Code | Meaning |
|---|---|
| `0` | Job completed. |
| `2` | Validation error. |
| `3` | Calibration required (`unknown` state). |
| `9` | Disk-space fault. |
| `10` | Camera fault. |
| `11` | Capture failed. |
| `12` | Motor stall / serial loss. |
| `15` | Operator interrupt (Ctrl+C, partial output preserved). |

---

## `cameracommander pan`

Run a video-pan job. Equivalent to `POST /api/jobs/video-pan`.

```
cameracommander pan [OPTIONS] CONFIG
```

Same options as `timelapse` (sans `--no-video`); `CONFIG.sequence.kind` must be `video_pan`.

**Exit codes**: same numeric scheme as `timelapse`.

---

## `cameracommander validate`

Validate a configuration file and print any errors. Pure offline — never connects to hardware.

```
cameracommander validate [OPTIONS] CONFIG
```

| Option | Effect |
|---|---|
| `--strict` (default) | Reject unknown keys. |
| `--no-strict` | Accept extra keys (forward-compatibility check). |
| `--json` | Emit the parsed `Configuration` document as JSON on stdout. |

**Exit codes**

| Code | Meaning |
|---|---|
| `0` | Configuration valid. |
| `2` | Validation failed; error report printed to stderr. |

---

## `cameracommander mock-firmware`

Start the in-process mock firmware server (replaces `old_implementation/firmware/mock_firmware_server.py`).

```
cameracommander mock-firmware [OPTIONS]
```

| Option | Default | Effect |
|---|---|---|
| `--host TEXT` | `127.0.0.1` | Bind address. |
| `--port INTEGER` | `9999` | Bind port. |
| `--initial-pan FLOAT` | `0.0` | Starting pan angle. |
| `--initial-tilt FLOAT` | `0.0` | Starting tilt angle. |
| `--microstep [1\|2\|4\|8\|16]` | `1` | Starting microstep. |
| `--drivers-disabled` | off | Start with drivers off. |
| `--deg-per-second FLOAT` | `60.0` | Motion speed simulation. `0` for instant. |
| `--settle-delay FLOAT` | `0.25` | Extra delay after each `M`. |
| `--fw-version TEXT` | matches host expectations | Override `VERSION` reply (used to test SC-008 mismatch). |

The command runs in the foreground. SIGINT shuts down cleanly.

---

## `cameracommander serve`

Start the host application (FastAPI + uvicorn).

```
cameracommander serve [OPTIONS]
```

| Option | Default | Effect |
|---|---|---|
| `--host TEXT` | `0.0.0.0` | Bind address. |
| `--port INTEGER` | `8000` | Bind port. |
| `--config PATH` | `~/.cameracommander/host.yaml` | Host-level configuration (camera selection hint, default tripod port, session library root). |
| `--mock` | flag | Implies `--mock-camera` and `--mock-tripod`. Spawns the mock firmware server in-process. |
| `--mock-camera` | flag | Use the mock camera adapter. |
| `--mock-tripod` | flag | Use `socket://127.0.0.1:9999` as the tripod port. |
| `--reload` | flag | Dev-only: enable uvicorn reload (skipped on Pi by default). |

The command serves the prebuilt SPA from `web/dist/` (if present) at `/`. Static asset serving uses FastAPI's `StaticFiles` (no extra dependency). When `web/dist/` is missing the host logs a warning and exposes only the API.

---

## Common behaviours across commands

- All commands honour `XDG_CONFIG_HOME` / `XDG_DATA_HOME` for default paths.
- All commands read configuration via the same Pydantic models, so a config that passes `validate` is guaranteed to load identically in `serve`, `timelapse`, and `pan`.
- All commands are non-interactive by default (no TTY prompts). `tripod` is the sole REPL; everything else exits on completion or fault.
- All commands set process exit codes per the tables above so they can be wired into scripts and CI.
