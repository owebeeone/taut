from taut.ir.dsl import BOOL, BYTES, FLOAT, INT, STR, Case, Enum, F, List, Map, Msg, OneOf, Ref, schema
ContentKind = Enum('ContentKind', text=0, number=1, empty=2, child=3, flag=4, items=5)
SCHEMA = schema(ContentKind,
    Content=Msg(kind=F(1, OneOf(ContentKind)), text=F(2, STR, Case(kind=ContentKind.text)),
                number=F(3, INT, Case(kind=ContentKind.number)),
                child=F(4, Ref('Content'), Case(kind=ContentKind.child)),
                flag=F(5, BOOL, Case(kind=ContentKind.flag)),
                items=F(6, List(INT), Case(kind=ContentKind.items)),
                next_id=9, reserved=(7,'retired')),
    Wrapper=Msg(child=F(1,Ref('Content')), children=F(2,List(Ref('Content'))),
                by_text=F(3,Map(STR,Ref('Content'))), by_int=F(4,Map(INT,Ref('Content'))),
                by_bool=F(5,Map(BOOL,Ref('Content')))),
    Virtual=Msg(kind=F(1,OneOf(ContentKind,virtual=True)), text=F(2,STR,Case(kind=ContentKind.text)),
                child=F(3,Ref('Content'))),
    Multi=Msg(left=F(1,OneOf(ContentKind)),right=F(2,OneOf(ContentKind)),
              a=F(3,STR,Case(left=ContentKind.text)),b=F(4,INT,Case(right=ContentKind.number))),
    Plain=Msg(value=F(1,INT), blob=F(2,BYTES,optional=True),ratio=F(3,FLOAT,optional=True)),
)

