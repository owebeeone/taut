from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_proto_api_surface_extensions_doc_exists_and_covers_contract():
    doc = ROOT / "dev-docs" / "TautProtoApiSurfaceExtensions.md"
    text = doc.read_text()

    required_sections = [
        "# taut API Surface Extensions",
        "## Design Goals",
        "## Extension Contract",
        "## tautc Interface",
        "## Discovery",
        "## Testing Regime",
        "## Protoc API Parity Harness",
        "## Recommended Decisions",
        "## Roll-Build Plan",
        "## Language Build Plan",
    ]
    for section in required_sections:
        assert section in text

    for term in [
        "proto2",
        "proto3",
        "capnproto",
        "TAUT_EXTENSION_PATH",
        "taut-extension-",
        "taut_extensions.<surface>.<language>",
        "implicit namespace package",
        "MUST NOT ship `__init__.py`",
        "python -m",
        "direct Python provider API",
        "taut_ir_json",
        "file-like",
        "write(",
        "options[\"layout\"]",
        "paths",
        "java_path",
        "python_path",
        "default_package",
        "packages",
        "package_id",
        "multi-package",
        "file location",
        "java_package",
        "python_package",
        "src/main/java/com/acme/common",
        "src/acme/common",
        "src/main/java",
        "src/",
        "golden corpus",
        "protoc",
        "v35.0",
        "protobuf-java",
        "protoc-gen-go",
        "artifact source",
        "dependency resolver",
        "javac",
        "provider_id",
        "api_version",
        "layout_version",
        "source_kind",
        "source_path",
        "test_context",
        "same API behavior tests",
        "State.md",
        "Workstreams.md",
        "Registry.md",
        "ActiveWork.md",
        "Reviews/",
        "Support/",
        "Handoff.md",
        "P01a",
        "P01b",
        "P01c",
        "P01d",
        "Checkpoints.md",
        "Rollback",
        "taut-ext-p00-start",
    ]:
        assert term in text

    assert "namespace_path" not in text
    assert "Maven Central" not in text
