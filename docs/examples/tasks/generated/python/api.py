"""GENERATED native Python types — do not edit."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class TaskState(Enum):
    open = 0
    doing = 1
    done = 2

@dataclass(slots=True)
class User:
    id: int
    name: str

@dataclass(slots=True)
class Comment:
    author: User
    text: str

@dataclass(slots=True)
class Task:
    id: int
    title: str
    state: TaskState
    assignee: User | None
    comments: list[Comment]
    labels: dict[str, str]

@dataclass(slots=True)
class Event:
    ts: int
    text: str

