"""Common Rust/Python conformance input for explicit oneof validation."""

from taut.ir.dsl import BOOL, INT, STR, Ref, schema
from oneof_fields_probe import Case, Enum, F, Msg, OneOf

ContentKind = Enum("ContentKind", text=0, number=1, flag=2, empty=3)
EnvelopeKind = Enum("EnvelopeKind", content=0, empty=1)

SCHEMA = schema(
    ContentKind,
    EnvelopeKind,
    Content=Msg(
        kind=F(1, OneOf(ContentKind, virtual=False, exhaustive=False)),
        text=F(2, STR, Case(kind=ContentKind.text)),
        number=F(3, INT, Case(kind=ContentKind.number)),
        flag=F(4, BOOL, Case(kind=ContentKind.flag)),
        next_id=5,
    ),
    Envelope=Msg(
        selection=F(1, OneOf(EnvelopeKind, virtual=False, exhaustive=False)),
        content=F(2, Ref.Content, Case(selection=EnvelopeKind.content)),
        next_id=3,
    ),
    VirtualContent=Msg(
        kind=F(1, OneOf(ContentKind, virtual=True, exhaustive=False)),
        text=F(2, STR, Case(kind=ContentKind.text)),
        number=F(3, INT, Case(kind=ContentKind.number)),
        flag=F(4, BOOL, Case(kind=ContentKind.flag)),
        next_id=5,
    ),
)
