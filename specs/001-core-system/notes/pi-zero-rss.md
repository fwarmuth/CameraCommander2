# Pi Zero 2 W RSS Budget

Target budget from the implementation plan:

- Idle host RSS: <= 200 MB
- In-job host RSS: <= 280 MB

This workspace is not a Raspberry Pi Zero 2 W or an ARM emulation environment,
so the final hardware RSS measurement cannot be truthfully validated here.
The measurement procedure for the rig is:

```bash
cd /opt/cameracommander/host
uv run cameracommander serve --mock --port 8000 &
HOST_PID=$!
sleep 5
ps -o pid,rss,cmd -p "$HOST_PID"
uv run cameracommander timelapse --mock examples/timelapse_mock.yaml
ps -o pid,rss,cmd -p "$HOST_PID"
kill "$HOST_PID"
```

Record RSS in KiB and divide by 1024 for MB. If the in-job value exceeds
280 MB, first disable video assembly during capture and reduce preview usage;
both are already architected to avoid retaining full-resolution frames in
memory.

Local x86_64 validation should not be treated as a substitute for the rig
measurement.
