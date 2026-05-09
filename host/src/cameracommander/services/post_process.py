"""Post-capture processing (ffmpeg)."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path


async def assemble_video(
    frame_dir: Path, 
    output_file: Path, 
    fps: int = 25,
    pattern: str = "frame_%04d.jpg"
) -> None:
    """Invoke ffmpeg to build an MP4 from frames."""
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frame_dir / pattern),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(output_file)
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({process.returncode}): {stderr.decode()}")
