"""Application examples: execute with -I -S to exclude installed packages/tools."""
import argparse
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=("source", "package", "disabled"), default="source")
parser.add_argument("--runtime-root", type=Path, help="application-selected package foundation root")
args = parser.parse_args()
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here / "generated" / args.mode / "python"))
if args.runtime_root:
    sys.path.insert(0, str(args.runtime_root.resolve()))

import importlib.abc


class NoCompiler(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("taut.ir", "taut.gen", "taut.cli", "taut.corpus", "setuptools")):
            raise RuntimeError("application unexpectedly requires compiler: " + fullname)


sys.meta_path.insert(0, NoCompiler())
import api as g
from taut.wire import cbor, codec, jsoncodec


def native(value):
    # Explicit application adapter for this generated type. No field reflection or factory.
    return {"kind": value.kind.name, "text": value.text, "number": value.number,
            "flag": value.flag, "items": value.items}


def show(label, value, *, recursive=True):
    report = value.validate(recursive=recursive)
    issues = [i.code + "@" + ".".join(p.field_name or str(p.index) for p in i.path)
              for i in report.issues]
    deferred = [d.reason_code for d in report.deferred_checks]
    print(f"{label}: valid={report.is_valid()} complete={report.is_complete()} "
          f"fast={value.is_valid(recursive=recursive)} scope={report.scope}; "
          f"issues={issues}; deferred={deferred}")
    return report


print(f"Runtime mode: {args.mode}; descriptors are shared static metadata, not dataclass fields.")
print("Descriptor:", g.Content.DESCRIPTOR.qualified_name,
      [f"{f.number}:{f.name}/{f.presence}" for f in g.Content.DESCRIPTOR.fields])
value = g.Content(g.ContentKind.number, number=42)
print("Valid number JSON:", jsoncodec.to_json(g.SCHEMA, "Content", native(value)))
if args.mode == "disabled":
    assert not hasattr(value, "validate")
    assert "taut.validation" not in sys.modules
    assert not (here / "generated/disabled/python/taut/validation.py").exists()
    print("Validation methods absent; descriptor/codec queries work with no validation engine.")
    raise SystemExit(0)

show("Valid number", value)
show("Missing selected", g.Content(g.ContentKind.number))
show("Extra nonselected", g.Content(g.ContentKind.number, text="extra", number=42))

print("\nPresence (each validates and keeps its JSON value):")
for selection, payload, data in (("number", "number", 0), ("flag", "flag", False),
                                  ("text", "text", ""), ("items", "items", []),
                                  ("empty", None, None)):
    value = g.Content(g.ContentKind[selection], **({payload: data} if payload else {}))
    assert value.is_valid()
    print(" ", selection, jsoncodec.to_json(g.SCHEMA, "Content", native(value)))

print("\nMutable draft -> serialize -> repair -> explicit validation:")
draft = g.Content(g.ContentKind.number, text="extra")
before = show("Draft", draft)
encoded = codec.encode(g.SCHEMA, "Content", native(draft))
assert codec.decode(g.SCHEMA, "Content", encoded) == native(draft)
print("Draft JSON:", jsoncodec.to_json(g.SCHEMA, "Content", native(draft)),
      "; dense CBOR fields:", len(cbor.loads(encoded)))
draft.text, draft.number = None, 42
show("Repaired", draft)
print("Earlier immutable report still has", len(before.issues), "issues.")

print("\nOwned child scopes and deferred virtual rules:")
child = g.Content(g.ContentKind.text)
envelope = g.Envelope(child)
show("Envelope local", envelope, recursive=False)
show("Envelope recursive", envelope)
virtual = g.VirtualEnvelope(content=child)
show("Virtual + bad child", virtual)
child.text = "fixed"
show("Virtual + repaired child", virtual)
print("Virtual JSON:", jsoncodec.to_json(g.SCHEMA, "VirtualEnvelope", {"content": native(child)}))
assert not any(name.startswith(("taut.ir", "taut.gen", "taut.cli")) for name in sys.modules)
print("Application completed without compiler, authoring loader, build tooling or shape engines.")
