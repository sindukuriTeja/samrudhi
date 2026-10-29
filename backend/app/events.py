"""Real-time event bus.

A small in-process pub/sub hub that fans out lifecycle events to:
  * SSE subscribers (the Command Centre live feed)
  * the audit ledger (so every event is also persisted per deliverable)

Events are plain dicts: {type, ts, agent_id, name, deliverable_id, detail, ...}
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
from collections import deque
from typing import Any, Callable


class EventBus:
    def __init__(self, history_limit: int = 300):
        self._subs: dict[int, asyncio.Queue] = {}
        self._lock = threading.Lock()
        self._next_sub = 0
        self.history: deque[dict] = deque(maxlen=history_limit)
        # optional hook: called for every event (e.g. ledger persistence)
        self.on_event: Callable[[dict], None] | None = None

    # ------------------------------------------------------------------ #
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        with self._lock:
            self._next_sub += 1
            self._subs[self._next_sub] = q
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._lock:
            for k, v in list(self._subs.items()):
                if v is q:
                    del self._subs[k]
                    break

    # ------------------------------------------------------------------ #
    def emit(self, etype: str, detail: str = "", agent_id: str = "",
             name: str = "", deliverable_id: str = "", **extra: Any) -> dict:
        event = {
            "type": etype,
            "ts": time.time(),
            "agent_id": agent_id,
            "name": name or agent_id,
            "deliverable_id": deliverable_id,
            "detail": detail,
            **extra,
        }
        with self._lock:
            self.history.append(event)
            subs = list(self._subs.values())
        if self.on_event is not None:
            try:
                self.on_event(event)
            except Exception:  # noqa: BLE001 — ledger must never break a run
                pass
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # slow consumer — drop oldest, keep the stream alive
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:  # noqa: BLE001
                    pass
        return event

    # ------------------------------------------------------------------ #
    async def stream(self, q: asyncio.Queue, heartbeat: float = 15.0):
        """Async generator of SSE frames for one subscriber."""
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=heartbeat)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
        finally:
            self.unsubscribe(q)


_bus: EventBus | None = None
_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = EventBus()
        return _bus