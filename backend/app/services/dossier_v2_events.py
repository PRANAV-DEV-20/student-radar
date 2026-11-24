"""In-process SSE event bus for Dossier v2 runs.

Events are also replayed from memory so a client connecting after a section
finishes still sees the full timeline. Persistent state lives in the database;
this bus is only a transport.
"""
from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class _Channel:
    history: List[Dict[str, Any]] = field(default_factory=list)
    subscribers: List[asyncio.Queue] = field(default_factory=list)
    closed: bool = False


class EventStore:
    def __init__(self) -> None:
        self._channels: Dict[uuid.UUID, _Channel] = defaultdict(_Channel)

    async def publish(self, run_id: uuid.UUID, event_type: str, data: Dict[str, Any]) -> None:
        channel = self._channels[run_id]
        event = {"type": event_type, "data": data}
        channel.history.append(event)
        for queue in list(channel.subscribers):
            queue.put_nowait(event)

    async def close(self, run_id: uuid.UUID) -> None:
        self._channels[run_id].closed = True

    def snapshot(self, run_id: uuid.UUID) -> List[Dict[str, Any]]:
        return list(self._channels[run_id].history)

    def subscribe(self, run_id: uuid.UUID) -> tuple[List[Dict[str, Any]], asyncio.Queue, _Channel]:
        channel = self._channels[run_id]
        queue: asyncio.Queue = asyncio.Queue()
        channel.subscribers.append(queue)
        return list(channel.history), queue, channel


event_store = EventStore()
