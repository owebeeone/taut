from taut.ir.dsl import BOOL, BYTES, FLOAT, INT, STR, Case, Enum, F, List, Map, Msg, OneOf, Ref, schema
Kind = Enum('Kind', text=0, number=1, empty=2, child=3, flag=4, items=5)
SCHEMA = schema(Kind,
    Content=Msg(kind=F(1, OneOf(Kind)), text=F(2, STR, Case(kind=Kind.text)),
                number=F(3, INT, Case(kind=Kind.number)),
                child=F(4, Ref('Content'), Case(kind=Kind.child)),
                flag=F(5, BOOL, Case(kind=Kind.flag)),
                items=F(6, List(INT), Case(kind=Kind.items)),
                next_id=9, reserved=(7,'retired')),
    Wrapper=Msg(child=F(1,Ref('Content')), children=F(2,List(Ref('Content'))),
                by_text=F(3,Map(STR,Ref('Content'))), by_int=F(4,Map(INT,Ref('Content'))),
                by_bool=F(5,Map(BOOL,Ref('Content')))),
    Virtual=Msg(kind=F(1,OneOf(Kind,virtual=True)), text=F(2,STR,Case(kind=Kind.text)),
                child=F(3,Ref('Content'))),
    Multi=Msg(left=F(1,OneOf(Kind)),right=F(2,OneOf(Kind)),
              a=F(3,STR,Case(left=Kind.text)),b=F(4,INT,Case(right=Kind.number))),
    Plain=Msg(value=F(1,INT), blob=F(2,BYTES,optional=True),ratio=F(3,FLOAT,optional=True)),
)
