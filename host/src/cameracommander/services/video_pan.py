"""Video pan orchestration."""
from __future__ import annotations
import asyncio
class VideoPanRunner:
    async def run(self, job, config, stop_event):
        job.status = "running"
        # Sync start logic
        await asyncio.sleep(config.sequence.duration_s)
        job.status = "completed"
