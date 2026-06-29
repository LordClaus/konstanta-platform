"""WebSocket fan-out hub for the CRM desktop panels.

A single process-wide :class:`ConnectionManager` holds the live sockets and
broadcasts events (new application, ticket locked/completed, new review/
registration) to every connected panel.
"""

from __future__ import annotations

import logging

from fastapi import WebSocket

log = logging.getLogger("api.ws")


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def add(self, websocket: WebSocket) -> None:
        """Register an already-accepted socket (used after the auth handshake)."""
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        # Iterate a snapshot: send_json awaits, so a concurrent connect/disconnect
        # could otherwise mutate the list mid-loop.
        dead: list[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as exc:  # noqa: BLE001
                log.error("WebSocket broadcast error: %s", exc)
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


manager = ConnectionManager()
