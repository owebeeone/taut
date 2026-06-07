"""GENERATED server stubs: a handler Protocol + IR-driven registration."""
from __future__ import annotations
from typing import Protocol
from .api import *  # noqa: F401,F403

class TasksHandlers(Protocol):
    async def create(self, title: str) -> Task: ...
    async def comment(self, task_id: int, author: User, text: str) -> Comment: ...
    async def set_state(self, id: int, state: TaskState) -> bool: ...
    def tasks_subscribe(self): ...  # -> Subscription (atom)
    def activity_subscribe(self): ...  # -> Subscription (log)

def register(transport, schema, handlers: "TasksHandlers") -> None:
    bind = {
        "create": handlers.create,
        "comment": handlers.comment,
        "set_state": handlers.set_state,
        "tasks.subscribe": handlers.tasks_subscribe,
        "activity.subscribe": handlers.activity_subscribe,
    }
    for m in schema.services["Tasks"].methods:
        transport.register_method(m, bind[m.name])
