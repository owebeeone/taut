"""Generate inspectable examples via the production emit route."""
from pathlib import Path

from taut.gen.scaffold import emit
from taut.ir.load import load_schema
from taut.ir.validate import validate_or_raise

HERE = Path(__file__).resolve().parent


def main():
    schema = load_schema(HERE / "content.taut.py")
    validate_or_raise(schema)
    for name, mode, enabled in (("source", "source", True), ("package", "package", True),
                                 ("disabled", "source", False)):
        written = emit(schema, HERE / "generated" / name, langs=["python"], services=[],
                       runtime_mode=mode, validation=enabled)
        print(f"{name}: {len(written)} files; validation={enabled}")


if __name__ == "__main__":
    main()
