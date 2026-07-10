"""``tautc`` — the taut codegen CLI.

Generate native types + encoders/decoders (and optional client/server stubs) from
a taut IR, so a build script can produce ahead-of-time struct defs for compiled
targets (Rust/C++) and typed surfaces for Python/TS. The IR is the single governed
artifact; this just projects it.

    tautc gen IR --out DIR [--lang python,rust,...] [--service NAME,...] [--api-only]

Examples:
    tautc gen api.taut.py -o gen/                 # all languages, api + client/server
    tautc gen api.taut.py -o gen/ -l rust,cpp --api-only   # just structs + codecs
    tautc gen api.ir.json -o gen/ -l rust -s Tasks        # one language, one service
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .corpus import kit, parity, synth
from .gen import scaffold
from .ir.load import load_schema, schema_from_json
from .ir.validate import validate_or_raise
from .wire import jsoncodec


def _load(path: Path):
    """Load a schema from a `.taut.py` DSL module or an exported `.ir.json`."""
    if path.suffix == ".json":
        return schema_from_json(json.loads(path.read_text()))
    return load_schema(path)


def _split(arg: str | None) -> list[str] | None:
    return [p.strip() for p in arg.split(",") if p.strip()] if arg else None


def _cmd_gen(args: argparse.Namespace) -> int:
    schema = _load(Path(args.ir))
    validate_or_raise(schema)  # never generate from incoherent IR
    if args.api_only:
        services: list[str] | None = []
    else:
        services = _split(args.service)  # None => all services in the IR
    # D1 (ratified): fail-closed is the DEFAULT codec since v0.8.0. `--legacy-codec`
    # is the deprecated opt-out (removed at v0.10.0); `--fail-closed` is now a no-op.
    fail_closed = not args.legacy_codec
    if args.legacy_codec:
        print("tautc gen: WARNING --legacy-codec emits the DEPRECATED fail-open Rust "
              "codec (from_cbor -> Self; panics on malformed input). It is removed at "
              "taut v0.10.0 — migrate by regenerating without --legacy-codec.",
              file=sys.stderr)
    if args.fail_closed:
        msg = ("tautc gen: note --fail-closed is now the default and a no-op "
               "(fail-closed decode became the v0.8.0 default).")
        if args.legacy_codec:
            msg += " It conflicts with --legacy-codec, which wins (legacy codec emitted)."
        print(msg, file=sys.stderr)
    written = scaffold.emit(
        schema, Path(args.out), langs=_split(args.lang), services=services,
        runtime=args.with_runtime, forward_compat=args.forward_compat,
        fail_closed=fail_closed,
    )
    for p in written:
        print(p)
    print(f"# {len(written)} files generated", file=sys.stderr)
    return 0


def _emit_or_check(path: Path, content: str, check: bool, stale: list[str]) -> None:
    if check:
        current = path.read_text() if path.exists() else None
        if current != content:
            stale.append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(path)


def _cmd_corpus(args: argparse.Namespace) -> int:
    schema = _load(Path(args.ir))
    validate_or_raise(schema)
    corpus = kit.build_corpus(schema, synth.synth_values(schema))  # auto-synth coverage values
    out = Path(args.out)
    stale: list[str] = []
    _emit_or_check(out / "golden.json", kit.golden_json(corpus), args.check, stale)
    for lang in (_split(args.lang) or []):
        if lang not in kit._HARNESS:
            print(f"# no parity harness for {lang!r} yet (golden.json is language-neutral)", file=sys.stderr)
            continue
        rel, emit = kit._HARNESS[lang]
        _emit_or_check(out / rel, emit(schema, corpus), args.check, stale)
    if args.check and stale:
        print("STALE (regenerate with `tautc corpus`):\n  " + "\n  ".join(stale), file=sys.stderr)
        return 2
    if not args.check:
        print(f"# {len(corpus)} vectors", file=sys.stderr)
    return 0


def _cmd_json(args: argparse.Namespace) -> int:
    schema = _load(Path(args.ir))
    validate_or_raise(schema)
    if args.from_json:  # JSON text -> CBOR bytes
        text = Path(args.input).read_text() if args.input else sys.stdin.read()
        data = jsoncodec.json_to_cbor(schema, args.message, text)
        if args.output:
            Path(args.output).write_bytes(data)
        else:
            sys.stdout.buffer.write(data)
    else:               # CBOR bytes -> JSON text
        data = Path(args.input).read_bytes() if args.input else sys.stdin.buffer.read()
        text = jsoncodec.cbor_to_json(schema, args.message, data, indent=args.indent)
        if args.output:
            Path(args.output).write_text(text + "\n")
        else:
            print(text)
    return 0


def _cmd_parity(args: argparse.Namespace) -> int:
    try:
        outcome = parity.run_gate(target=args.target, run_compiled=not args.no_compile)
    except parity.ParityValidationError as exc:
        print(f"parity: {exc}", file=sys.stderr)
        return 2
    for line in outcome.lines:
        print(line)
    # Nonzero ONLY on a governance violation: a gated target failing, or a green
    # target still allowlisted. Observed reds on allowlisted targets do not fail.
    return 1 if outcome.violations else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tautc", description="taut codegen — IR -> code")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen", help="generate native types + codec (and client/server) from an IR")
    g.add_argument("ir", help="path to a taut IR (.taut.py DSL module or .ir.json)")
    g.add_argument("-o", "--out", required=True, help="output directory")
    g.add_argument("-l", "--lang", help="comma-separated targets (default: all): python,typescript,rust,cpp")
    g.add_argument("-s", "--service", help="comma-separated services for client/server stubs (default: all in the IR)")
    g.add_argument("--api-only", action="store_true", help="emit only api (types + encoders/decoders), no client/server")
    g.add_argument("--with-runtime", action="store_true",
                   help="also emit the vendored CBOR runtime for compiled targets (rust->cbor.rs, cpp->taut/cbor.hpp)")
    g.add_argument("--forward-compat", action="store_true",
                   help="generated structs carry a wire_residual field preserving unknown/newer tags (Rust; required if the IR has extensions)")
    g.add_argument("--fail-closed", action="store_true",
                   help="(deprecated no-op) fail-closed decode is the DEFAULT Rust codec since taut "
                        "v0.8.0; this flag is accepted for back-compat but has no effect and will be removed.")
    g.add_argument("--legacy-codec", action="store_true",
                   help="(deprecated opt-out) emit the LEGACY fail-open Rust codec — today's pre-v0.8.0 "
                        "output byte-for-byte (from_cbor -> Self; panics on malformed input; default cbor.rs). "
                        "Warns on use and stamps a deprecation banner into the generated header. Sunset: "
                        "removed at taut v0.10.0 (D1 two-minor rule). No-op for non-rust targets.")
    g.set_defaults(func=_cmd_gen)

    c = sub.add_parser("corpus", help="derive a golden conformance corpus (+ parity harness) from an IR")
    c.add_argument("ir", help="path to a taut IR (.taut.py DSL module or .ir.json)")
    c.add_argument("-o", "--out", required=True, help="output directory (writes golden.json [+ <lang>/ harness])")
    c.add_argument("-l", "--lang", help="comma-separated parity harnesses to emit (currently: rust)")
    c.add_argument("--check", action="store_true", help="don't write; exit 2 if committed output is stale (CI drift gate)")
    c.set_defaults(func=_cmd_corpus)

    j = sub.add_parser("json", help="convert between deterministic-CBOR and JSON via the IR")
    j.add_argument("ir", help="path to a taut IR (.taut.py DSL module or .ir.json)")
    j.add_argument("-m", "--message", required=True, help="message name the bytes/JSON conform to")
    j.add_argument("--from-json", action="store_true", help="reverse direction: JSON -> CBOR (default is CBOR -> JSON)")
    j.add_argument("-i", "--input", help="input file (default: stdin; CBOR is binary, JSON is text)")
    j.add_argument("-o", "--output", help="output file (default: stdout)")
    j.add_argument("--indent", type=int, help="pretty-print JSON with this indent (CBOR -> JSON only)")
    j.set_defaults(func=_cmd_json)

    pr = sub.add_parser(
        "parity",
        help="run the leading cross-language codec-parity gate (Wave-1 replay + allowlist governance). "
             "SUPPLEMENTS `tautc corpus` — never replaces the message golden corpora.")
    pr.add_argument("-t", "--target", choices=parity.TARGETS,
                    help="replay only this target's harness (default: all Wave-1 — rust,python,typescript,js)")
    pr.add_argument("--no-compile", action="store_true",
                    help="skip the compiled/subprocess targets; run only the direct Python harness")
    pr.set_defaults(func=_cmd_parity)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
