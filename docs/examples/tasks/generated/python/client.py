"""GENERATED typed client over a generic taut transport (call/subscribe)."""
from __future__ import annotations
from .api import *  # noqa: F401,F403

class TasksClient:
    def __init__(self, transport):
        self._t = transport

    async def create(self, title: str) -> Task:
        return await self._t.call("create", Task, title=title)

    async def comment(self, task_id: int, author: User, text: str) -> Comment:
        return await self._t.call("comment", Comment, task_id=task_id, author=author, text=text)

    async def set_state(self, id: int, state: TaskState) -> bool:
        return await self._t.call("set_state", bool, id=id, state=state)

    def tasks_subscribe(self):  # atom stream
        return self._t.subscribe("tasks.subscribe")

    def activity_subscribe(self):  # log stream
        return self._t.subscribe("activity.subscribe")

