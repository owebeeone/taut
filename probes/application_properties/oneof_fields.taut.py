"""Executable syntax probe; these helpers are not production Taut imports."""

from taut.ir.dsl import INT, STR, schema
from oneof_fields_probe import Case, Enum, F, Msg, OneOf

ContentKind = Enum("ContentKind", text=0, number=1, empty=2)

SCHEMA = schema(
    ContentKind,
    Content=Msg(
        kind=F(1, OneOf(ContentKind, virtual=False, exhaustive=False)),
        text=F(2, STR, Case(kind=ContentKind.text)),
        number=F(3, INT, Case(kind=ContentKind.number)),
        next_id=4,
    ),
)
