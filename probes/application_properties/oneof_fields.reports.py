"""Generated opt-in oneof validation. Does not alter construction or codecs."""
from dataclasses import dataclass
from . import api as r

@dataclass(frozen=True)
class PathSegment:
    kind: str
    value: str | int

@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: tuple[PathSegment, ...]
    message: str

@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    def is_valid(self):
        return not self.issues


def _issue(issues, path, field, code, message):
    issues.append(ValidationIssue(code, (*path, PathSegment("field", field)), message))

def _collect_content(value, path, issues):
    if not isinstance(value, r.Content):
        issues.append(ValidationIssue('validation.type_mismatch', tuple(path), 'Expected record Content'))
        return
    discriminator = getattr(value, 'kind', None)
    if not isinstance(discriminator, r.ContentKind):
        _issue(issues, path, 'kind', 'oneof.discriminator_invalid', 'Invalid oneof discriminator')
        return
    if discriminator == r.ContentKind.empty:
        if getattr(value, 'text', None) is not None:
            _issue(issues, path, 'text', 'oneof.payload_unexpected', 'Payload is not selected by the discriminator')
        if getattr(value, 'number', None) is not None:
            _issue(issues, path, 'number', 'oneof.payload_unexpected', 'Payload is not selected by the discriminator')
    elif discriminator == r.ContentKind.number:
        if getattr(value, 'text', None) is not None:
            _issue(issues, path, 'text', 'oneof.payload_unexpected', 'Payload is not selected by the discriminator')
        if getattr(value, 'number', None) is None:
            _issue(issues, path, 'number', 'oneof.payload_missing', 'Selected oneof payload is missing')
    elif discriminator == r.ContentKind.text:
        if getattr(value, 'text', None) is None:
            _issue(issues, path, 'text', 'oneof.payload_missing', 'Selected oneof payload is missing')
        if getattr(value, 'number', None) is not None:
            _issue(issues, path, 'number', 'oneof.payload_unexpected', 'Payload is not selected by the discriminator')
    else:
        _issue(issues, path, 'kind', 'oneof.discriminator_invalid', 'Invalid oneof discriminator')

def validate_content(value):
    issues = []
    _collect_content(value, [], issues)
    return ValidationReport(tuple(issues))

