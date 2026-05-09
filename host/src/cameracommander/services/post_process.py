"""Timelapse frame video assembly."""

from __future__ import annotations

import asyncio
import shlex
import subprocess
from pathlib import Path

from ..api.websocket import EventBus
from ..core.config import OutputConfig


class VideoAssembler:
    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus

    async def assemble(self, *, frames_dir: Path, output: OutputConfig, session_id: str) -> Path:
        video_path = frames_dir / "timelapse.mp4"
        fps = output.video.fps
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-framerate",
            str(fps),
            "-i",
            "frame_%04d.jpg",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
        ]
        if output.video.ffmpeg_extra:
            cmd.extend(shlex.split(output.video.ffmpeg_extra))
        cmd.append(str(video_path))
        if self._event_bus is not None:
            await self._event_bus.publish(f"session.{session_id}.assemble", {"status": "running"})
        await asyncio.to_thread(
            subprocess.run,
            cmd,
            cwd=frames_dir,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if self._event_bus is not None:
            await self._event_bus.publish(
                f"session.{session_id}.assemble",
                {"status": "completed", "path": str(video_path)},
            )
        return video_path


__all__ = ["VideoAssembler"]
