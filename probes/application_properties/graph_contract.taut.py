"""Minimal self-contained reference contract, not the full GARNS graph schema."""

from taut.ir.dsl import STR, Enum, Map, Ref, schema
from taut_app_probe import F, Msg
from graph_contract_probe import GraphIndex, GraphLink, GraphRules, ReferenceCheck, Tagged

NS = "garns.graph"

SCHEMA = schema(
    NodeTag=Enum(declaration=0, value=1),
    DeclarationView=Enum(type_view=0, field=1),
    NodeRef=Msg(node_id=F(1, STR), next_id=2),
    GraphDocument=Msg(
        nodes=F(1, Map(STR, Ref.NodeRecord), GraphIndex(
            NS, reference="NodeRef", key="node_id",
        )),
        next_id=2,
    ),
    NodeRecord=Msg(
        GraphRules(NS, tagged=Tagged("tag", {
            "declaration": "declaration",
            "value": "value",
        })),
        tag=F(1, Ref.NodeTag),
        declaration=F(2, Ref.DeclarationRecord, optional=True),
        value=F(3, Ref.ValueRecord, optional=True),
        next_id=4,
    ),
    DeclarationRecord=Msg(
        GraphRules(NS, tagged=Tagged("view", {
            "type_view": "type_details",
            "field": "field",
        })),
        name=F(1, STR),
        view=F(2, Ref.DeclarationView),
        type_details=F(3, Ref.TypeDetails, optional=True),
        field=F(4, Ref.FieldDetails, optional=True),
        next_id=5,
    ),
    TypeDetails=Msg(next_id=1),
    ValueRecord=Msg(text=F(1, STR), next_id=2),
    FieldDetails=Msg(
        GraphRules(NS, references=ReferenceCheck(
            graph="GraphDocument", function="validate_field_reference",
        )),
        declared_type=F(1, Ref.NodeRef, GraphLink(
            NS,
            index="GraphDocument.nodes",
            select=["declaration", "type_view"],
            null="reject",
            missing="reject",
            invalid_payload="reject",
            wrong_target="reject",
        )),
        next_id=2,
    ),
)
