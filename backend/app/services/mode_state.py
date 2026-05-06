from __future__ import annotations

import asyncio

from app.schemas import ModeLiteral


class ModeState:
    def __init__(self, default_mode: ModeLiteral = "smart", default_home_automation_mode: bool = False) -> None:
        self._mode: ModeLiteral = default_mode
        self._home_automation_enabled: bool = default_home_automation_mode
        self._lock = asyncio.Lock()

    async def get_mode(self) -> ModeLiteral:
        async with self._lock:
            return self._mode

    async def set_mode(self, mode: ModeLiteral) -> ModeLiteral:
        async with self._lock:
            self._mode = mode
            return self._mode

    async def is_home_automation_enabled(self) -> bool:
        async with self._lock:
            return self._home_automation_enabled

    async def set_home_automation_mode(self, enabled: bool) -> bool:
        async with self._lock:
            self._home_automation_enabled = enabled
            return self._home_automation_enabled
