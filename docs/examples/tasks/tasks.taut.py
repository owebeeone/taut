"""Tasks — the Getting Started web API as a runnable IR module.

Shows: composed messages (Task embeds an optional User and a list of Comment;
each Comment embeds a User), an enum, a service with unary calls + an Atom and a
Log streaming endpoint, and the `reserved` / `next_id` evolution features.
"""

import sys
from pathlib import Path

# make the taut builder importable when loaded by path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from taut.ir.dsl import BOOL, INT, STR, Enum, F, List, Map, Msg, Params, Ref, method, schema, service

SCHEMA = schema(
    service("Tasks",
        method("create", role="in",
               params=Params(title=STR), out=Ref.Task),
        method("comment", role="in",
               params=Params(task_id=INT, author=Ref.User, text=STR),
               out=Ref.Comment),
        method("set_state", role="ctl",
               params=Params(id=INT, state=Ref.TaskState), out=BOOL),
        method("tasks.subscribe", role="out", shape="atom",
               out=List(Ref.Task)),
        method("activity.subscribe", role="out", shape="log",
               out=Ref.Event),
    ),

    TaskState=Enum(open=0, doing=1, done=2),

    User=Msg(
        id=F(1, INT),
        name=F(2, STR),
        next_id=3),

    Comment=Msg(
        author=F(1, Ref.User),                 # composition: a message field
        text=F(2, STR),
        next_id=3),

    Task=Msg(
        id=F(1, INT),
        title=F(2, STR),
        state=F(3, Ref.TaskState),
        assignee=F(4, Ref.User, optional=True),  # nested message, optional
        comments=F(5, List(Ref.Comment)),        # list of messages
        labels=F(7, Map(STR, STR)),                 # keyed collection (e.g. {"team": "infra"})
        # tag 6 and the name "priority" were retired — never reuse them:
        reserved=[6, "priority"],
        next_id=8),

    Event=Msg(
        ts=F(1, INT),
        text=F(2, STR),
        next_id=3),
)
