"""GENERATED native Python types — do not edit."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class TaskState(Enum):
    open = 0
    doing = 1
    done = 2

@dataclass
class User:
    id: int
    name: str

@dataclass
class Comment:
    author: User
    text: str

@dataclass
class Task:
    id: int
    title: str
    state: TaskState
    assignee: User | None
    comments: list[Comment]

@dataclass
class Event:
    ts: int
    text: str

