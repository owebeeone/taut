//! Shared explicit validation: one traversal/predicate for full and fast sinks.
use super::cbor::descriptors::{
    ChildVisitor, KeyRef, MessageDescriptor, OneOfDescriptor, RecordAccess, ONEOF_RULE,
};

// This inherent attachment must be compiled by the codec/descriptor type owner.
// A compatibility facade must re-export validation too, not compile another copy.
impl super::cbor::descriptors::FoundationOwner {
    #[doc(hidden)]
    pub const TAUT_VALIDATION_ENGINE_OWNER: fn(ValidationReport) -> ValidationReport =
        |report| report;
}
use alloc::{string::String, vec::Vec};

pub const VALIDATION_CONTRACT: u32 = 1;

#[derive(Clone, Copy, Debug)]
pub struct ValidationOptions {
    pub recursive: bool,
}
impl Default for ValidationOptions {
    fn default() -> Self {
        Self { recursive: true }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PathSegment {
    kind: &'static str,
    field_name: Option<String>,
    index: Option<usize>,
    key_type: Option<String>,
    key_cbor_base64: Option<String>,
}
impl PathSegment {
    pub fn for_field(name: impl Into<String>) -> Self {
        Self {
            kind: "field",
            field_name: Some(name.into()),
            index: None,
            key_type: None,
            key_cbor_base64: None,
        }
    }
    pub fn for_index(index: usize) -> Self {
        Self {
            kind: "index",
            field_name: None,
            index: Some(index),
            key_type: None,
            key_cbor_base64: None,
        }
    }
    pub fn for_key(key_type: impl Into<String>, canonical_bytes: &[u8]) -> Self {
        let key_type = key_type.into();
        let value =
            super::cbor::try_decode(canonical_bytes).expect("invalid Taut canonical key bytes");
        let kind = match &value {
            super::cbor::Cbor::Int(_) => "int",
            super::cbor::Cbor::Text(_) => "str",
            super::cbor::Cbor::Bool(_) => "bool",
            _ => panic!("invalid Taut key kind"),
        };
        assert_eq!(key_type, kind, "Taut key kind mismatch");
        assert_eq!(
            super::cbor::encode(&value),
            canonical_bytes,
            "noncanonical Taut key bytes"
        );
        Self {
            kind: "key",
            field_name: None,
            index: None,
            key_type: Some(key_type),
            key_cbor_base64: Some(base64(canonical_bytes)),
        }
    }
    pub fn kind(&self) -> &str {
        self.kind
    }
    pub fn field_name(&self) -> Option<&str> {
        self.field_name.as_deref()
    }
    pub fn index(&self) -> Option<usize> {
        self.index
    }
    pub fn key_type(&self) -> Option<&str> {
        self.key_type.as_deref()
    }
    pub fn key_cbor_base64(&self) -> Option<&str> {
        self.key_cbor_base64.as_deref()
    }
}
fn base64(bytes: &[u8]) -> String {
    const TABLE: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::new();
    for chunk in bytes.chunks(3) {
        let n = ((chunk[0] as u32) << 16)
            | ((chunk.get(1).copied().unwrap_or(0) as u32) << 8)
            | chunk.get(2).copied().unwrap_or(0) as u32;
        out.push(TABLE[(n >> 18) as usize] as char);
        out.push(TABLE[((n >> 12) & 63) as usize] as char);
        out.push(if chunk.len() > 1 {
            TABLE[((n >> 6) & 63) as usize] as char
        } else {
            '='
        });
        out.push(if chunk.len() > 2 {
            TABLE[(n & 63) as usize] as char
        } else {
            '='
        });
    }
    out
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ValidationIssue {
    code: String,
    rule: String,
    path: Vec<PathSegment>,
    message: String,
}
impl ValidationIssue {
    pub fn new(
        code: impl Into<String>,
        rule: impl Into<String>,
        path: Vec<PathSegment>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            code: code.into(),
            rule: rule.into(),
            path,
            message: message.into(),
        }
    }
    pub fn code(&self) -> &str {
        &self.code
    }
    pub fn rule(&self) -> &str {
        &self.rule
    }
    pub fn path(&self) -> &[PathSegment] {
        &self.path
    }
    pub fn message(&self) -> &str {
        &self.message
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DeferredCheck {
    rule: String,
    path: Vec<PathSegment>,
    reason_code: String,
    message: String,
}
impl DeferredCheck {
    pub fn new(
        rule: impl Into<String>,
        path: Vec<PathSegment>,
        reason_code: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            rule: rule.into(),
            path,
            reason_code: reason_code.into(),
            message: message.into(),
        }
    }
    pub fn rule(&self) -> &str {
        &self.rule
    }
    pub fn path(&self) -> &[PathSegment] {
        &self.path
    }
    pub fn reason_code(&self) -> &str {
        &self.reason_code
    }
    pub fn message(&self) -> &str {
        &self.message
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ValidationReport {
    issues: Vec<ValidationIssue>,
    deferred_checks: Vec<DeferredCheck>,
    scope: String,
}
impl Default for ValidationReport {
    fn default() -> Self {
        Self::new(Vec::new(), Vec::new(), "recursive")
    }
}
impl ValidationReport {
    pub fn new(
        issues: Vec<ValidationIssue>,
        deferred_checks: Vec<DeferredCheck>,
        scope: impl Into<String>,
    ) -> Self {
        let scope = scope.into();
        assert!(
            scope == "local" || scope == "recursive",
            "invalid Taut validation scope"
        );
        Self {
            issues,
            deferred_checks,
            scope,
        }
    }
    pub fn issues(&self) -> &[ValidationIssue] {
        &self.issues
    }
    pub fn deferred_checks(&self) -> &[DeferredCheck] {
        &self.deferred_checks
    }
    pub fn scope(&self) -> &str {
        &self.scope
    }
    pub fn is_valid(&self) -> bool {
        self.issues.is_empty()
    }
    pub fn is_complete(&self) -> bool {
        self.deferred_checks.is_empty()
    }
}

/// Return the same event for both sinks; no diagnostic object is built here.
fn payload_error(selected: bool, present: bool) -> Option<(&'static str, &'static str)> {
    match (selected, present) {
        (true, false) => Some(("oneof.payload_missing", "selected payload is absent")),
        (false, true) => Some(("oneof.payload_unexpected", "nonselected payload is present")),
        _ => None,
    }
}
struct Engine {
    report: Option<ValidationReport>,
    path: Vec<PathSegment>,
    recursive: bool,
}
impl Engine {
    fn event(&mut self, deferred: bool, code: &str, field: &str, message: &str) -> bool {
        if let Some(report) = &mut self.report {
            let mut path = self.path.clone();
            path.push(PathSegment::for_field(field));
            if deferred {
                report
                    .deferred_checks
                    .push(DeferredCheck::new(ONEOF_RULE, path, code, message));
            } else {
                report
                    .issues
                    .push(ValidationIssue::new(code, ONEOF_RULE, path, message));
            }
            true
        } else {
            false
        }
    }
    fn group(
        &mut self,
        value: &dyn RecordAccess,
        desc: &MessageDescriptor,
        group: &OneOfDescriptor,
        control_index: usize,
    ) -> bool {
        if group.virtual_group() {
            return self.event(
                true,
                "oneof.virtual_deferred",
                group.controlling_field(),
                "virtual selection is deferred",
            );
        }
        let tag = value.field_state(control_index).enum_number();
        let selected = tag.and_then(|tag| group.members().iter().find(|m| m.number() == tag));
        let selected = match selected {
            Some(member) => member.payload(),
            None => {
                return self.event(
                    false,
                    "oneof.invalid_discriminator",
                    group.controlling_field(),
                    "expected controlling enum member",
                );
            }
        };
        for (index, field) in desc.fields().iter().enumerate() {
            if !group
                .members()
                .iter()
                .any(|m| m.payload() == Some(field.name()))
            {
                continue;
            }
            if let Some((code, message)) = payload_error(
                selected == Some(field.name()),
                value.field_state(index).is_present(),
            ) {
                if !self.event(false, code, field.name(), message) {
                    return false;
                }
            }
        }
        true
    }
    fn walk(&mut self, value: &dyn RecordAccess) -> bool {
        let desc = value.descriptor();
        for (index, field) in desc.fields().iter().enumerate() {
            for group in desc
                .oneofs()
                .iter()
                .filter(|g| g.controlling_field() == field.name())
            {
                if !self.group(value, desc, group, index) {
                    return false;
                }
            }
            if self.recursive && !field.virtual_field() && value.field_state(index).is_present() {
                if self.report.is_some() {
                    self.path.push(PathSegment::for_field(field.name()));
                }
                let result = value.children(index, self);
                if self.report.is_some() {
                    self.path.pop();
                }
                if !result {
                    return false;
                }
            }
        }
        true
    }
}
impl ChildVisitor for Engine {
    fn record(&mut self, value: &dyn RecordAccess) -> bool {
        self.walk(value)
    }
    fn push_index(&mut self, index: usize) {
        if self.report.is_some() {
            self.path.push(PathSegment::for_index(index));
        }
    }
    fn push_key(&mut self, key: KeyRef<'_>) {
        if self.report.is_some() {
            self.path
                .push(PathSegment::for_key(key.kind(), &key.canonical_bytes()));
        }
    }
    fn pop(&mut self) {
        if self.report.is_some() {
            self.path.pop();
        }
    }
}
pub fn validate_record(value: &dyn RecordAccess, options: ValidationOptions) -> ValidationReport {
    let mut engine = Engine {
        report: Some(ValidationReport::new(
            Vec::new(),
            Vec::new(),
            if options.recursive {
                "recursive"
            } else {
                "local"
            },
        )),
        path: Vec::new(),
        recursive: options.recursive,
    };
    engine.walk(value);
    engine.report.expect("report sink")
}
pub fn is_record_valid(value: &dyn RecordAccess, options: ValidationOptions) -> bool {
    Engine {
        report: None,
        path: Vec::new(),
        recursive: options.recursive,
    }
    .walk(value)
}
