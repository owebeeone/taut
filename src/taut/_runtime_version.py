"""Runtime-only version marker. Distribution release versions are separate."""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("taut-proto")
except PackageNotFoundError:
    __version__ = "0.10.0+python.oneof.reference.1"
