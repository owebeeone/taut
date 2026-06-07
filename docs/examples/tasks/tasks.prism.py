"""Tasks — the Getting Started web API as a runnable IR module.

Shows: composed messages (Task embeds an optional User and a list of Comment;
each Comment embeds a User), an enum, a service with unary calls + an Atom and a
Log streaming endpoint, and the `reserved` / `next_id` evolution features.
"""

import sys
from pathlib import Path

# make the prism builder importable when loaded by path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from prism.ir.dsl import BOOL, INT, STR, Enum, F, List, Msg, Ref, method, schema, service

SCHEMA = schema(
    Enum("TaskState", open=0, doing=1, done=2),

    Msg("User",
        F("id", 1, INT),
        F("name", 2, STR),
        next_id=3),

    Msg("Comment",
        F("author", 1, Ref("User")),                 # composition: a message field
        F("text", 2, STR),
        next_id=3),

    Msg("Task",
        F("id", 1, INT),
        F("title", 2, STR),
        F("state", 3, Ref("TaskState")),
        F("assignee", 4, Ref("User"), optional=True),  # nested message, optional
        F("comments", 5, List(Ref("Comment"))),        # list of messages
        # tag 6 and the name "priority" were retired — never reuse them:
        reserved=[6, "priority"],
        next_id=7),

    Msg("Event",
        F("ts", 1, INT),
        F("text", 2, STR),
        next_id=3),

    service("Tasks",
        method("create", kind="unary", role="in",
               params=[("title", STR)], output=Ref("Task")),
        method("comment", kind="unary", role="in",
               params=[("task_id", INT), ("author", Ref("User")), ("text", STR)],
               output=Ref("Comment")),
        method("set_state", kind="unary", role="ctl",
               params=[("id", INT), ("state", Ref("TaskState"))], output=BOOL),
        method("tasks.subscribe", kind="server_stream", role="out", shape="atom",
               events={"replace": List(Ref("Task"))}),
        method("activity.subscribe", kind="server_stream", role="out", shape="log",
               events={"append": Ref("Event")}),
    ),
)
