"""Illustrative field/message-local properties; uses only the probe helpers."""

from taut.ir.dsl import STR, Ref, schema
from taut_app_probe import F, Msg, app

SCHEMA = schema(
    NodeRef=Msg(node_id=F(1, STR), next_id=2),
    FieldDetails=Msg(
        app("garns.graph", {"reference_check": "check_field_type"}),
        declared_type=F(
            1, Ref.NodeRef,
            app("garns.graph", {"target": {"tag": "declaration", "view": "type_view"}}),
        ),
        next_id=2,
    ),
)
