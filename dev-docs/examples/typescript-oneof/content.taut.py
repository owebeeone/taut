"""A mutable draft: choose text, number, or a payload-free empty choice."""
from taut.ir.dsl import Enum, Msg, F, OneOf, Case, STR, INT, schema
ContentKind=Enum('ContentKind',text=0,number=1,empty=2)
SCHEMA=schema(ContentKind,Content=Msg(
    kind=F(1,OneOf(ContentKind)),
    text=F(2,STR,Case(kind=ContentKind.text)),
    number=F(3,INT,Case(kind=ContentKind.number)),next_id=4))
