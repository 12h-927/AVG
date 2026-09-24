"""WebSocket 端点管理器与广播逻辑。"""
import asyncio
from fastapi import WebSocket
from typing import List


class ConnectionManager:
    """管理所有 WebSocket 客户端连接。"""

    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        """向所有连接的客户端广播 JSON 数据。"""
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
