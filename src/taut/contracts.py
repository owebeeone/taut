"""Unreleased Python reference contracts; independent of distribution versions."""
RUNTIME_OWNER = "taut.python.foundation"
GENERATOR_BUILD = "python-oneof-reference.1"
DESCRIPTOR_CONTRACT = 1
CODEC_CONTRACT = 1
CONSTRAINT_IR_VERSION = 3
CAPABILITIES = frozenset({"descriptors.v1", "codec.v1", "oneof.v1"})


class ConfigurationError(ValueError):
    """Incompatible artifact/runtime binding; regenerate or rebind it."""


def require_contract(*, artifact: str, owner=RUNTIME_OWNER, descriptor=1, codec=1,
                     capabilities=(), generator=None):
    if (owner != RUNTIME_OWNER or type(descriptor) is not int or descriptor != DESCRIPTOR_CONTRACT
            or type(codec) is not int or codec != CODEC_CONTRACT
            or not set(capabilities) <= CAPABILITIES):
        raise ConfigurationError(
            f"{artifact}: required owner={owner}, descriptor={descriptor}, codec={codec}, "
            f"capabilities={tuple(capabilities)}; found {RUNTIME_OWNER}, descriptor="
            f"{DESCRIPTOR_CONTRACT}, codec={CODEC_CONTRACT}, capabilities={sorted(CAPABILITIES)}; "
            "regenerate artifact or rebind a compatible shared runtime")


if __name__ != "taut.contracts":
    raise ConfigurationError("split runtime owner: load foundation once as taut; rebind imports")
