"""``/ws/events`` route — single multiplexed WebSocket per UI client.

Wire format mirrors ``contracts/host-events.asyncapi.yaml``: every server-to-
client frame is ``{"topic": str, "payload": object}``; client control frames are
``{"action": "subscribe" | "unsubscribe", "topics": [str]}``. Unknown actions
produce a ``control.error`` reply.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...core.logging import logger
from ..deps import get_event_bus
from ..websocket import Subscriber

router = APIRouter()


@router.websocket("/ws/events")
async def events_socket(websocket: WebSocket) -> None:
    bus = get_event_bus(websocket.app)
    await websocket.accept()
    sub = Subscriber()
    await bus.register(sub)

    async def reader() -> None:
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError as exc:
                    await websocket.send_json(
                        {
                            "topic": "control.error",
                            "payload": {"error": "invalid_json", "message": str(exc)},
                        }
                    )
                    continue
                action = msg.get("action")
                topics = msg.get("topics") or []
                if action == "subscribe":
                    sub.subscribe(topics)
                elif action == "unsubscribe":
                    sub.unsubscribe(topics)
                else:
                    await websocket.send_json(
                        {
                            "topic": "control.error",
                            "payload": {
                                "error": "unknown_action",
                                "message": f"unknown action {action!r}",
                            },
                        }
                    )
        except WebSocketDisconnect:
            return

    async def writer() -> None:
        try:
            async for frame in bus.stream(sub):
                await websocket.send_text(frame)
        except WebSocketDisconnect:
            return

    # Drive both directions concurrently. The first to terminate cancels the other.
    import asyncio

    reader_task = asyncio.create_task(reader())
    writer_task = asyncio.create_task(writer())
    try:
        _done, pending = await asyncio.wait(
            {reader_task, writer_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("websocket reader/writer crashed: {}", exc)
    finally:
        await bus.unregister(sub)


__all__ = ["router"]
