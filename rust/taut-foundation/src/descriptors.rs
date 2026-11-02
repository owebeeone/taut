//! Canonical Taut Rust descriptor and typed-access foundation (contract 1).
//! Generated schemas publish static values; no instance is stored in metadata.
use alloc::{string::String, vec::Vec};

pub const DESCRIPTOR_CONTRACT: u32 = 1;
pub const CODEC_CONTRACT: u32 = 1;
pub const RUNTIME_OWNER: &str = "taut.rust.foundation";
pub const GENERATOR_BUILD: &str = "rust-oneof-reference.1";
pub const ONEOF_RULE: &str = "taut.oneof.v1";
pub const CAPABILITIES: &[&str] = &["descriptors.v1", "codec.v1", "oneof.v1"];

/// Check a generated artifact against the actual built runtime at publication.
/// Generator/release labels are provenance, not exact compatibility requirements.
pub fn require_contract(
    artifact: &str,
    owner: &str,
    descriptor: u32,
    codec: u32,
    capabilities: &[&str],
) {
    assert!(owner == RUNTIME_OWNER && descriptor == DESCRIPTOR_CONTRACT && codec == CODEC_CONTRACT
        && capabilities.iter().all(|capability| CAPABILITIES.contains(capability))
        && (!capabilities.contains(&"oneof.v1") || ONEOF_RULE == "taut.oneof.v1"),
        "Taut artifact {artifact} requires owner={owner}, descriptor={descriptor}, codec={codec}, capabilities={capabilities:?}; found owner={RUNTIME_OWNER}, descriptor={DESCRIPTOR_CONTRACT}, codec={CODEC_CONTRACT}, capabilities={CAPABILITIES:?}; regenerate artifact or rebind compatible runtime");
}

/// Nominal foundation owner. The optional engine attaches its identity here;
/// Rust rejects compiling that engine in a foreign crate or twice for one owner.
pub struct FoundationOwner {
    _private: (),
}

macro_rules! static_record {
    ($name:ident { $($field:ident : $ty:ty),* $(,)? }) => {
        #[derive(Debug)]
        pub struct $name { $($field: $ty),* }
        impl $name {
            #[allow(clippy::too_many_arguments)]
            pub const fn new($($field: $ty),*) -> Self { Self { $($field),* } }
            $(pub fn $field(&self) -> $ty { self.$field })*
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum OptionValue {
    Null,
    Bool(bool),
    Int(i64),
    Float(f64),
    String(&'static str),
    Bytes(&'static [u8]),
    List(&'static [OptionValue]),
    Map(&'static [(&'static str, OptionValue)]),
}
pub type Options = &'static [(&'static str, OptionValue)];

#[derive(Clone, Copy, Debug)]
pub enum TypeDescriptor {
    Int,
    String,
    Bool,
    Bytes,
    Float,
    Message(fn() -> &'static MessageDescriptor),
    Enum(fn() -> &'static EnumDescriptor),
    List(&'static TypeDescriptor),
    Map(&'static TypeDescriptor, &'static TypeDescriptor),
}
impl TypeDescriptor {
    pub fn kind(&self) -> &'static str {
        match self {
            Self::Int => "int",
            Self::String => "str",
            Self::Bool => "bool",
            Self::Bytes => "bytes",
            Self::Float => "float",
            Self::Message(_) => "message",
            Self::Enum(_) => "enum",
            Self::List(_) => "list",
            Self::Map(_, _) => "map",
        }
    }
}
static_record!(FieldDescriptor {
    name: &'static str, access_identity: Option<&'static str>, number: u32,
    field_type: TypeDescriptor, presence: &'static str, transient: bool,
    virtual_field: bool, options: Options,
});
static_record!(EnumMemberDescriptor { name: &'static str, number: i64, options: Options });
static_record!(EnumDescriptor {
    name: &'static str, qualified_name: &'static str,
    members: &'static [EnumMemberDescriptor], options: Options,
});
static_record!(OneOfMemberDescriptor {
    member: &'static str, number: i64, payload: Option<&'static str>,
});
static_record!(OneOfDescriptor {
    controlling_field: &'static str, enumeration: fn() -> &'static EnumDescriptor,
    virtual_group: bool, exhaustive: bool, members: &'static [OneOfMemberDescriptor],
});
static_record!(ConstraintDescriptor { rule: &'static str, parameters: Options });
static_record!(MessageDescriptor {
    name: &'static str, qualified_name: &'static str, descriptor_contract_version: u32,
    fields: &'static [FieldDescriptor], oneofs: &'static [OneOfDescriptor],
    constraints: &'static [ConstraintDescriptor], reserved_numbers: &'static [u32],
    reserved_names: &'static [&'static str], next_id: Option<u32>,
    options: Options, effective_options: Options,
});
static_record!(SchemaDescriptor {
    descriptor_contract_version: u32, ir_version: u32, identity: &'static str,
    messages: &'static [fn() -> &'static MessageDescriptor],
    enums: &'static [fn() -> &'static EnumDescriptor], options: Options, effective_options: Options,
});

impl EnumDescriptor {
    pub fn check(&self) {
        assert!(
            !self.members.is_empty(),
            "Taut enum has no members: regenerate artifact"
        );
        for (index, member) in self.members.iter().enumerate() {
            assert!(
                !self.members[..index]
                    .iter()
                    .any(|old| old.name == member.name || old.number == member.number),
                "Taut duplicate enum metadata: regenerate artifact"
            );
        }
    }
}

impl MessageDescriptor {
    /// Validate finite local facts only; reference accessors are never expanded.
    /// Generation verifies native facts; foreign artifacts fail at build/publication.
    pub fn check(&self) {
        assert_eq!(
            self.descriptor_contract_version, DESCRIPTOR_CONTRACT,
            "Taut descriptor contract mismatch: regenerate artifact or rebind runtime owner"
        );
        let mut previous = 0;
        for field in self.fields {
            assert!(
                field.number > previous,
                "Taut descriptor fields must be in number order"
            );
            previous = field.number;
            assert!(
                matches!(field.presence, "required" | "nullable" | "missing_ok"),
                "Taut unsupported field presence: regenerate artifact"
            );
            assert_eq!(
                field.virtual_field,
                field.access_identity.is_none(),
                "Taut descriptor accessor mismatch: regenerate artifact"
            );
        }
        for constraint in self.constraints {
            assert_eq!(
                constraint.rule, ONEOF_RULE,
                "unsupported Taut rule: regenerate/rebind runtime"
            );
            assert_eq!(
                constraint.parameters.len(),
                1,
                "unsupported Taut oneof parameters"
            );
            let (name, value) = constraint.parameters[0];
            assert_eq!(
                name, "controlling_field",
                "unsupported Taut oneof parameter"
            );
            assert!(
                self.oneofs
                    .iter()
                    .any(|g| value == OptionValue::String(g.controlling_field)),
                "Taut oneof constraint does not match a group"
            );
        }
        for group in self.oneofs {
            let control = self
                .fields
                .iter()
                .find(|f| f.name == group.controlling_field)
                .expect("Taut oneof control missing: regenerate artifact");
            assert_eq!(
                control.virtual_field, group.virtual_group,
                "Taut virtual control mismatch"
            );
            assert!(
                control.presence == "required" && !control.transient,
                "Taut discriminator must be required and nontransient"
            );
            let enumeration = (group.enumeration)();
            enumeration.check();
            match control.field_type {
                TypeDescriptor::Enum(get) => assert!(
                    core::ptr::eq(get(), enumeration),
                    "Taut oneof enum owner mismatch: regenerate/rebind artifact"
                ),
                _ => panic!("Taut oneof descriptor category mismatch: control must be enum"),
            }
            assert_eq!(
                group.members.len(),
                enumeration.members.len(),
                "Taut incomplete oneof mapping"
            );
            for member in enumeration.members {
                let nominated = group
                    .members
                    .iter()
                    .find(|m| m.member == member.name)
                    .expect("Taut oneof member missing");
                assert_eq!(
                    nominated.number, member.number,
                    "Taut oneof enum contract mismatch"
                );
                if let Some(payload) = nominated.payload {
                    let field = self
                        .fields
                        .iter()
                        .find(|f| f.name == payload)
                        .expect("Taut oneof payload missing");
                    assert_ne!(field.presence, "required", "Taut payload must be nullable");
                } else {
                    assert!(!group.exhaustive, "Taut exhaustive mapping incomplete");
                }
            }
        }
        assert_eq!(
            self.constraints.len(),
            self.oneofs.len(),
            "Taut constraint/group inventory mismatch"
        );
        for group in self.oneofs {
            assert_eq!(
                self.constraints
                    .iter()
                    .filter(|c| c.parameters
                        == [(
                            "controlling_field",
                            OptionValue::String(group.controlling_field)
                        )])
                    .count(),
                1,
                "Taut oneof constraint/group link mismatch"
            );
        }
    }
}

/// Borrowed typed scalar access. Rust values enforce the corresponding native
/// field types; borrowed text/bytes cannot outlive the bound input visit.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum PrimitiveValue<'a> {
    Int(i64),
    String(&'a str),
    Bool(bool),
    Bytes(&'a [u8]),
    Float(f64),
    Enum(i64),
}

#[derive(Clone, Copy, Debug)]
pub struct FieldState<'a> {
    present: bool,
    enum_number: Option<i64>,
    primitive: Option<PrimitiveValue<'a>>,
}
impl<'a> FieldState<'a> {
    pub const fn new(present: bool, enum_number: Option<i64>) -> Self {
        Self {
            present,
            enum_number,
            primitive: match enum_number {
                Some(number) => Some(PrimitiveValue::Enum(number)),
                None => None,
            },
        }
    }
    pub fn is_present(self) -> bool {
        self.present
    }
    pub fn enum_number(self) -> Option<i64> {
        self.enum_number
    }
    pub const fn from_primitive(value: PrimitiveValue<'a>) -> Self {
        Self {
            present: true,
            enum_number: match value {
                PrimitiveValue::Enum(n) => Some(n),
                _ => None,
            },
            primitive: Some(value),
        }
    }
    pub fn primitive(self) -> Option<PrimitiveValue<'a>> {
        self.primitive
    }
}

/// Borrowed canonical key input; map traversal and diagnostics share the encoder.
#[derive(Clone, Copy, Debug)]
pub enum KeyRef<'a> {
    Int(i64),
    String(&'a str),
    Bool(bool),
}
impl KeyRef<'_> {
    pub fn kind(self) -> &'static str {
        match self {
            Self::Int(_) => "int",
            Self::String(_) => "str",
            Self::Bool(_) => "bool",
        }
    }
    pub fn canonical_bytes(self) -> Vec<u8> {
        use super::{encode, Cbor};
        encode(&match self {
            Self::Int(n) => Cbor::Int(n),
            Self::String(s) => Cbor::Text(String::from(s)),
            Self::Bool(b) => Cbor::Bool(b),
        })
    }
}

/// Synchronous visitor: temporary child bindings never escape a call.
pub trait ChildVisitor {
    fn record(&mut self, record: &dyn RecordAccess) -> bool;
    fn push_index(&mut self, index: usize);
    fn push_key(&mut self, key: KeyRef<'_>);
    fn pop(&mut self);
}
mod private {
    pub trait Sealed {}
}
/// Internal adapter protocol, implemented by Bound only, never by messages.
pub trait RecordAccess: private::Sealed {
    fn descriptor(&self) -> &'static MessageDescriptor;
    fn field_state(&self, index: usize) -> FieldState<'_>;
    fn children(&self, index: usize, visitor: &mut dyn ChildVisitor) -> bool;
}
pub struct SchemaBinding<T: 'static> {
    descriptor: MessageDescriptor,
    check_dependencies: fn(),
    state: for<'a> fn(&'a T, usize) -> FieldState<'a>,
    children: fn(&T, usize, &mut dyn ChildVisitor) -> bool,
}
impl<T> SchemaBinding<T> {
    pub const fn new(
        descriptor: MessageDescriptor,
        check_dependencies: fn(),
        state: for<'a> fn(&'a T, usize) -> FieldState<'a>,
        children: fn(&T, usize, &mut dyn ChildVisitor) -> bool,
    ) -> Self {
        Self {
            descriptor,
            check_dependencies,
            state,
            children,
        }
    }
    /// The binding owns its descriptor facts; callers never supply a separate
    /// erased value/descriptor pair or an unrelated published descriptor.
    pub fn descriptor(&'static self) -> &'static MessageDescriptor {
        (self.check_dependencies)();
        self.descriptor.check();
        &self.descriptor
    }
    pub fn bind<'a>(&'static self, value: &'a T) -> Bound<'a, T> {
        Bound {
            value,
            binding: self,
        }
    }
}
pub struct Bound<'a, T: 'static> {
    value: &'a T,
    binding: &'static SchemaBinding<T>,
}
impl<T> private::Sealed for Bound<'_, T> {}
impl<T> RecordAccess for Bound<'_, T> {
    fn descriptor(&self) -> &'static MessageDescriptor {
        self.binding.descriptor()
    }
    fn field_state(&self, index: usize) -> FieldState<'_> {
        (self.binding.state)(self.value, index)
    }
    fn children(&self, index: usize, visitor: &mut dyn ChildVisitor) -> bool {
        (self.binding.children)(self.value, index, visitor)
    }
}
