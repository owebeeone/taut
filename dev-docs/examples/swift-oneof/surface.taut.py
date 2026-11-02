from taut.ir.dsl import Enum, Msg, F, OneOf, Case, STR, INT, schema

Choice = Enum('Choice', text=0, number=1, empty=2)
SCHEMA = schema(Choice, Content=Msg(
    kind=F(1, OneOf(Choice)),
    text=F(2, STR, Case(kind=Choice.text)),
    number=F(3, INT, Case(kind=Choice.number)),
))
