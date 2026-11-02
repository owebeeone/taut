"""Native Python checkpoint schema; no probe annotations."""
from taut.ir.dsl import BOOL, INT, STR, Case, Enum, F, List, Map, Msg, OneOf, Ref, schema

ContentKind = Enum("ContentKind", text=0, number=1, flag=2, items=3, empty=4)

SCHEMA = schema(
    ContentKind,
    Content=Msg(
        kind=F(1, OneOf(ContentKind)),
        text=F(2, STR, Case(kind=ContentKind.text)),
        number=F(3, INT, Case(kind=ContentKind.number)),
        flag=F(4, BOOL, Case(kind=ContentKind.flag)),
        items=F(5, List(INT), Case(kind=ContentKind.items)), next_id=6),
    Envelope=Msg(content=F(1, Ref.Content)),
    VirtualEnvelope=Msg(
        kind=F(1, OneOf(ContentKind, virtual=True)),
        content=F(2, Ref.Content, Case(kind=ContentKind.text)), next_id=3),
    Collection=Msg(entries=F(1, List(Ref.Content)), by_key=F(2, Map(STR, Ref.Content))),
    Tree=Msg(content=F(1, Ref.Content, optional=True), children=F(2, List(Ref.Tree))),
)
