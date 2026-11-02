// GENERATED native Rust types + codec — do not edit.
#![allow(dead_code, clippy::redundant_closure, clippy::needless_question_mark, clippy::collapsible_if)]
extern crate alloc;
#[allow(unused_imports)]
use alloc::{boxed::Box, string::String, vec, vec::Vec};
use taut_foundation::cbor::{Cbor, DecodeError};
// The file's bounds, for a decode rooted at a type that is not a message:
// `cbor::try_decode_with(bytes, MAX_DEPTH, MAX_ENCODED_LEN)`.
pub const MAX_DEPTH: usize = 32;
pub const MAX_ENCODED_LEN: Option<usize> = None;
#[derive(Clone, Copy, Debug, PartialEq, Default)]
pub enum ContentKind {
    #[default] Text,
    Number,
    Flag,
    Items,
    Empty,
}
impl ContentKind {
    pub fn wire(self) -> i64 { match self {
        Self::Text => 0,
        Self::Number => 1,
        Self::Flag => 2,
        Self::Items => 3,
        Self::Empty => 4,
    } }
    pub fn from_wire(v: i64) -> Result<Self, DecodeError> { Ok(match v {
        0 => Self::Text,
        1 => Self::Number,
        2 => Self::Flag,
        3 => Self::Items,
        4 => Self::Empty,
        _ => return Err(DecodeError::UnknownEnum { enum_name: "ContentKind", value: v }),
    }) }
}
#[derive(Clone, Debug, PartialEq, Default)]
pub struct Content {
    pub kind: ContentKind,
    pub text: Option<String>,
    pub number: Option<i64>,
    pub flag: Option<bool>,
    pub items: Option<Vec<i64>>,
}
impl Content {
    pub const MAX_DEPTH: usize = 32;
    pub const MAX_ENCODED_LEN: Option<usize> = None;
    pub fn to_cbor(&self) -> Cbor {
        Cbor::Map(vec![
            (1, Cbor::Int(self.kind.wire())),
            (2, match &self.text { Some(v) => Cbor::Text(v.clone()), None => Cbor::Null }),
            (3, match &self.number { Some(v) => Cbor::Int(*v), None => Cbor::Null }),
            (4, match &self.flag { Some(v) => Cbor::Bool(*v), None => Cbor::Null }),
            (5, match &self.items { Some(v) => Cbor::Array(v.iter().map(|x| Cbor::Int(*x)).collect()), None => Cbor::Null }),
        ])
    }
    pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError> {
        Ok(Self {
            kind: ContentKind::from_wire(c.try_get(1)?.try_int()?)?,
            text: { let v = c.try_get(2)?; if v.is_null() { None } else { Some(v.try_text()?) } },
            number: { let v = c.try_get(3)?; if v.is_null() { None } else { Some(v.try_int()?) } },
            flag: { let v = c.try_get(4)?; if v.is_null() { None } else { Some(v.try_bool()?) } },
            items: { let v = c.try_get(5)?; if v.is_null() { None } else { Some(v.try_array()?.iter().map(|x| Ok(x.try_int()?)).collect::<Result<Vec<_>, DecodeError>>()?) } },
        })
    }
    pub fn decode(bytes: &[u8]) -> Result<Self, DecodeError> {
        Self::from_cbor(&taut_foundation::cbor::try_decode_with(bytes, Self::MAX_DEPTH, Self::MAX_ENCODED_LEN)?)
    }
}
#[derive(Clone, Debug, PartialEq, Default)]
pub struct Envelope {
    pub content: Content,
}
impl Envelope {
    pub const MAX_DEPTH: usize = 32;
    pub const MAX_ENCODED_LEN: Option<usize> = None;
    pub fn to_cbor(&self) -> Cbor {
        Cbor::Map(vec![
            (1, self.content.to_cbor()),
        ])
    }
    pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError> {
        Ok(Self {
            content: Content::from_cbor(c.try_get(1)?)?,
        })
    }
    pub fn decode(bytes: &[u8]) -> Result<Self, DecodeError> {
        Self::from_cbor(&taut_foundation::cbor::try_decode_with(bytes, Self::MAX_DEPTH, Self::MAX_ENCODED_LEN)?)
    }
}
#[derive(Clone, Debug, PartialEq, Default)]
pub struct VirtualEnvelope {
    pub content: Option<Content>,
}
impl VirtualEnvelope {
    pub const MAX_DEPTH: usize = 32;
    pub const MAX_ENCODED_LEN: Option<usize> = None;
    pub fn to_cbor(&self) -> Cbor {
        Cbor::Map(vec![
            (2, match &self.content { Some(v) => v.to_cbor(), None => Cbor::Null }),
        ])
    }
    pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError> {
        Ok(Self {
            content: { let v = c.try_get(2)?; if v.is_null() { None } else { Some(Content::from_cbor(v)?) } },
        })
    }
    pub fn decode(bytes: &[u8]) -> Result<Self, DecodeError> {
        Self::from_cbor(&taut_foundation::cbor::try_decode_with(bytes, Self::MAX_DEPTH, Self::MAX_ENCODED_LEN)?)
    }
}
#[derive(Clone, Debug, PartialEq, Default)]
pub struct Collection {
    pub entries: Vec<Content>,
    pub by_key: alloc::collections::BTreeMap<String, Content>,
}
impl Collection {
    pub const MAX_DEPTH: usize = 32;
    pub const MAX_ENCODED_LEN: Option<usize> = None;
    pub fn to_cbor(&self) -> Cbor {
        Cbor::Map(vec![
            (1, Cbor::Array(self.entries.iter().map(|x| x.to_cbor()).collect())),
            (2, Cbor::Array(self.by_key.iter().map(|(k, v)| Cbor::Map(vec![(1, Cbor::Text(k.clone())), (2, v.to_cbor())])).collect())),
        ])
    }
    pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError> {
        Ok(Self {
            entries: c.try_get(1)?.try_array()?.iter().map(|x| Content::from_cbor(x)).collect::<Result<Vec<_>, DecodeError>>()?,
            by_key: { let mut m = alloc::collections::BTreeMap::new(); for e in c.try_get(2)?.try_array()? { let ek = e.try_get(1)?; let ev = e.try_get(2)?; let k = ek.try_text()?; if m.contains_key(&k) { return Err(DecodeError::DuplicateMapKey(k.into())); } m.insert(k, Content::from_cbor(ev)?); } m },
        })
    }
    pub fn decode(bytes: &[u8]) -> Result<Self, DecodeError> {
        Self::from_cbor(&taut_foundation::cbor::try_decode_with(bytes, Self::MAX_DEPTH, Self::MAX_ENCODED_LEN)?)
    }
}
#[derive(Clone, Debug, PartialEq, Default)]
pub struct Tree {
    pub content: Option<Content>,
    pub children: Vec<Tree>,
}
impl Tree {
    pub const MAX_DEPTH: usize = 32;
    pub const MAX_ENCODED_LEN: Option<usize> = None;
    pub fn to_cbor(&self) -> Cbor {
        Cbor::Map(vec![
            (1, match &self.content { Some(v) => v.to_cbor(), None => Cbor::Null }),
            (2, Cbor::Array(self.children.iter().map(|x| x.to_cbor()).collect())),
        ])
    }
    pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError> {
        Ok(Self {
            content: { let v = c.try_get(1)?; if v.is_null() { None } else { Some(Content::from_cbor(v)?) } },
            children: c.try_get(2)?.try_array()?.iter().map(|x| Tree::from_cbor(x)).collect::<Result<Vec<_>, DecodeError>>()?,
        })
    }
    pub fn decode(bytes: &[u8]) -> Result<Self, DecodeError> {
        Self::from_cbor(&taut_foundation::cbor::try_decode_with(bytes, Self::MAX_DEPTH, Self::MAX_ENCODED_LEN)?)
    }
}
// Generator build rust-oneof-reference.1; descriptor=1; codec=1; owner=taut.rust.foundation
const _: () = assert!(taut_foundation::cbor::descriptors::DESCRIPTOR_CONTRACT == 1, "Taut descriptor contract mismatch: rebind runtime");
const _: () = assert!(taut_foundation::cbor::descriptors::CODEC_CONTRACT == 1, "Taut codec contract mismatch: rebind runtime");
impl ContentKind {
pub const TAUT_DESCRIPTOR_CONTRACT: u32 = 1;
pub const TAUT_CODEC_CONTRACT: u32 = 1;
pub const TAUT_FACTS_FINGERPRINT: &'static str = "26e337a0bd4495808c3dfde6e769f2e3fdf61455ddf4c3c2a7d8717201bb3d75";
pub fn descriptor() -> &'static taut_foundation::cbor::descriptors::EnumDescriptor { let descriptor = _taut_metadata::ENUM_ContentKind; descriptor.check(); descriptor }
}
impl Content {
pub const TAUT_DESCRIPTOR_CONTRACT: u32 = 1;
pub const TAUT_CODEC_CONTRACT: u32 = 1;
pub const TAUT_FACTS_FINGERPRINT: &'static str = "e80ba9dcc4db81069f63a9ab3234981991f543465beb0f95dec51be320a8df73";
pub fn descriptor() -> &'static taut_foundation::cbor::descriptors::MessageDescriptor {
_taut_metadata::BINDING_Content.descriptor()
}
pub fn taut_binding() -> &'static taut_foundation::cbor::descriptors::SchemaBinding<Self> { _taut_metadata::BINDING_Content }
}
impl Envelope {
pub const TAUT_DESCRIPTOR_CONTRACT: u32 = 1;
pub const TAUT_CODEC_CONTRACT: u32 = 1;
pub const TAUT_FACTS_FINGERPRINT: &'static str = "640286e8d08eabf5f60530411ddb9dd4bd30b8ec49cedda97f2952f23e0ee852";
pub fn descriptor() -> &'static taut_foundation::cbor::descriptors::MessageDescriptor {
_taut_metadata::BINDING_Envelope.descriptor()
}
pub fn taut_binding() -> &'static taut_foundation::cbor::descriptors::SchemaBinding<Self> { _taut_metadata::BINDING_Envelope }
}
impl VirtualEnvelope {
pub const TAUT_DESCRIPTOR_CONTRACT: u32 = 1;
pub const TAUT_CODEC_CONTRACT: u32 = 1;
pub const TAUT_FACTS_FINGERPRINT: &'static str = "8ed8eb4b21e4d6bc1512cf2387a87e8a68a4e06e9e6511128d99f4782dd0dda2";
pub fn descriptor() -> &'static taut_foundation::cbor::descriptors::MessageDescriptor {
_taut_metadata::BINDING_VirtualEnvelope.descriptor()
}
pub fn taut_binding() -> &'static taut_foundation::cbor::descriptors::SchemaBinding<Self> { _taut_metadata::BINDING_VirtualEnvelope }
}
impl Collection {
pub const TAUT_DESCRIPTOR_CONTRACT: u32 = 1;
pub const TAUT_CODEC_CONTRACT: u32 = 1;
pub const TAUT_FACTS_FINGERPRINT: &'static str = "3204288c02b509d63a880fb41b6d30760b94678351072ebda94d112c9452ffce";
pub fn descriptor() -> &'static taut_foundation::cbor::descriptors::MessageDescriptor {
_taut_metadata::BINDING_Collection.descriptor()
}
pub fn taut_binding() -> &'static taut_foundation::cbor::descriptors::SchemaBinding<Self> { _taut_metadata::BINDING_Collection }
}
impl Tree {
pub const TAUT_DESCRIPTOR_CONTRACT: u32 = 1;
pub const TAUT_CODEC_CONTRACT: u32 = 1;
pub const TAUT_FACTS_FINGERPRINT: &'static str = "53fc0cc00d467f711636a515daf35ae754e46473d80da9c549b6c4908bc423fa";
pub fn descriptor() -> &'static taut_foundation::cbor::descriptors::MessageDescriptor {
_taut_metadata::BINDING_Tree.descriptor()
}
pub fn taut_binding() -> &'static taut_foundation::cbor::descriptors::SchemaBinding<Self> { _taut_metadata::BINDING_Tree }
}
pub static SCHEMA_DESCRIPTOR: &taut_foundation::cbor::descriptors::SchemaDescriptor = &taut_foundation::cbor::descriptors::SchemaDescriptor::new(1, 3, "schema_9c886c43d8695c4e",
&[Content::descriptor, Envelope::descriptor, VirtualEnvelope::descriptor, Collection::descriptor, Tree::descriptor],
&[ContentKind::descriptor],
_taut_metadata::FILE_OPTIONS, _taut_metadata::FILE_EFFECTIVE);
#[allow(non_upper_case_globals, unused_variables, unused_imports)]
mod _taut_metadata {
use super::*;
use taut_foundation::cbor::descriptors::*;
pub const FILE_OPTIONS: Options = &[];
pub const FILE_EFFECTIVE: Options = &[("max_depth", OptionValue::Int(32)), ("max_encoded_len", OptionValue::Null)];
pub fn check_external() {
require_contract("schema_9c886c43d8695c4e", "taut.rust.foundation", 1, 1, &["descriptors.v1", "codec.v1", "oneof.v1"]);
}
pub static ENUM_ContentKind: &EnumDescriptor = &EnumDescriptor::new("ContentKind", "schema_9c886c43d8695c4e.ContentKind", &[EnumMemberDescriptor::new("text", 0, &[]), EnumMemberDescriptor::new("number", 1, &[]), EnumMemberDescriptor::new("flag", 2, &[]), EnumMemberDescriptor::new("items", 3, &[]), EnumMemberDescriptor::new("empty", 4, &[])], &[]);
pub static BINDING_Content: &SchemaBinding<Content> = &SchemaBinding::new(MessageDescriptor::new("Content", "schema_9c886c43d8695c4e.Content", 1, &[
FieldDescriptor::new("kind", Some("kind"), 1, TypeDescriptor::Enum(ContentKind::descriptor), "required", false, false, &[]),
FieldDescriptor::new("text", Some("text"), 2, TypeDescriptor::String, "nullable", false, false, &[]),
FieldDescriptor::new("number", Some("number"), 3, TypeDescriptor::Int, "nullable", false, false, &[]),
FieldDescriptor::new("flag", Some("flag"), 4, TypeDescriptor::Bool, "nullable", false, false, &[]),
FieldDescriptor::new("items", Some("items"), 5, TypeDescriptor::List(&TypeDescriptor::Int), "nullable", false, false, &[]),
], &[
OneOfDescriptor::new("kind", ContentKind::descriptor, false, false, &[OneOfMemberDescriptor::new("text", 0, Some("text")), OneOfMemberDescriptor::new("number", 1, Some("number")), OneOfMemberDescriptor::new("flag", 2, Some("flag")), OneOfMemberDescriptor::new("items", 3, Some("items")), OneOfMemberDescriptor::new("empty", 4, None)]),
], &[ConstraintDescriptor::new(ONEOF_RULE, &[("controlling_field", OptionValue::String("kind"))])], &[], &[], Some(6), &[], &[("max_depth", OptionValue::Int(32)), ("max_encoded_len", OptionValue::Null)]), check_external, |value, index| {
match index {
0 => FieldState::new(true, Some(value.kind.wire())),
1 => match &value.text { Some(v) => FieldState::from_primitive(PrimitiveValue::String(v)), None => FieldState::new(false, None) },
2 => match &value.number { Some(v) => FieldState::from_primitive(PrimitiveValue::Int(*v)), None => FieldState::new(false, None) },
3 => match &value.flag { Some(v) => FieldState::from_primitive(PrimitiveValue::Bool(*v)), None => FieldState::new(false, None) },
4 => FieldState::new(value.items.is_some(), None),
_ => panic!("Taut typed binding field mismatch: regenerate artifact"),
}
}, |value, index, visitor| {
true });
pub static BINDING_Envelope: &SchemaBinding<Envelope> = &SchemaBinding::new(MessageDescriptor::new("Envelope", "schema_9c886c43d8695c4e.Envelope", 1, &[
FieldDescriptor::new("content", Some("content"), 1, TypeDescriptor::Message(Content::descriptor), "required", false, false, &[]),
], &[
], &[], &[], &[], None, &[], &[("max_depth", OptionValue::Int(32)), ("max_encoded_len", OptionValue::Null)]), check_external, |value, index| {
match index {
0 => FieldState::new(true, None),
_ => panic!("Taut typed binding field mismatch: regenerate artifact"),
}
}, |value, index, visitor| {
if index == 0 {
if !visitor.record(&Content::taut_binding().bind(&value.content)) { return false; }
}
true });
pub static BINDING_VirtualEnvelope: &SchemaBinding<VirtualEnvelope> = &SchemaBinding::new(MessageDescriptor::new("VirtualEnvelope", "schema_9c886c43d8695c4e.VirtualEnvelope", 1, &[
FieldDescriptor::new("kind", None, 1, TypeDescriptor::Enum(ContentKind::descriptor), "required", false, true, &[]),
FieldDescriptor::new("content", Some("content"), 2, TypeDescriptor::Message(Content::descriptor), "nullable", false, false, &[]),
], &[
OneOfDescriptor::new("kind", ContentKind::descriptor, true, false, &[OneOfMemberDescriptor::new("text", 0, Some("content")), OneOfMemberDescriptor::new("number", 1, None), OneOfMemberDescriptor::new("flag", 2, None), OneOfMemberDescriptor::new("items", 3, None), OneOfMemberDescriptor::new("empty", 4, None)]),
], &[ConstraintDescriptor::new(ONEOF_RULE, &[("controlling_field", OptionValue::String("kind"))])], &[], &[], Some(3), &[], &[("max_depth", OptionValue::Int(32)), ("max_encoded_len", OptionValue::Null)]), check_external, |value, index| {
match index {
0 => FieldState::new(false, None),
1 => FieldState::new(value.content.is_some(), None),
_ => panic!("Taut typed binding field mismatch: regenerate artifact"),
}
}, |value, index, visitor| {
if index == 1 {
if let Some(child) = &value.content {
if !visitor.record(&Content::taut_binding().bind(child)) { return false; }
}
}
true });
pub static BINDING_Collection: &SchemaBinding<Collection> = &SchemaBinding::new(MessageDescriptor::new("Collection", "schema_9c886c43d8695c4e.Collection", 1, &[
FieldDescriptor::new("entries", Some("entries"), 1, TypeDescriptor::List(&TypeDescriptor::Message(Content::descriptor)), "required", false, false, &[]),
FieldDescriptor::new("by_key", Some("by_key"), 2, TypeDescriptor::Map(&TypeDescriptor::String, &TypeDescriptor::Message(Content::descriptor)), "required", false, false, &[]),
], &[
], &[], &[], &[], None, &[], &[("max_depth", OptionValue::Int(32)), ("max_encoded_len", OptionValue::Null)]), check_external, |value, index| {
match index {
0 => FieldState::new(true, None),
1 => FieldState::new(true, None),
_ => panic!("Taut typed binding field mismatch: regenerate artifact"),
}
}, |value, index, visitor| {
if index == 0 {
for (index0, item0) in value.entries.iter().enumerate() {
visitor.push_index(index0);
if !visitor.record(&Content::taut_binding().bind(item0)) { return false; }
visitor.pop();
}
}
if index == 1 {
let mut entries0: Vec<_> = value.by_key.iter().map(|(key0, item0)| (KeyRef::String(key0).canonical_bytes(), key0, item0)).collect();
entries0.sort_by(|a, b| a.0.cmp(&b.0));
for (_, key0, item0) in entries0 {
visitor.push_key(KeyRef::String(key0));
if !visitor.record(&Content::taut_binding().bind(item0)) { return false; }
visitor.pop();
}
}
true });
pub static BINDING_Tree: &SchemaBinding<Tree> = &SchemaBinding::new(MessageDescriptor::new("Tree", "schema_9c886c43d8695c4e.Tree", 1, &[
FieldDescriptor::new("content", Some("content"), 1, TypeDescriptor::Message(Content::descriptor), "nullable", false, false, &[]),
FieldDescriptor::new("children", Some("children"), 2, TypeDescriptor::List(&TypeDescriptor::Message(Tree::descriptor)), "required", false, false, &[]),
], &[
], &[], &[], &[], None, &[], &[("max_depth", OptionValue::Int(32)), ("max_encoded_len", OptionValue::Null)]), check_external, |value, index| {
match index {
0 => FieldState::new(value.content.is_some(), None),
1 => FieldState::new(true, None),
_ => panic!("Taut typed binding field mismatch: regenerate artifact"),
}
}, |value, index, visitor| {
if index == 0 {
if let Some(child) = &value.content {
if !visitor.record(&Content::taut_binding().bind(child)) { return false; }
}
}
if index == 1 {
for (index0, item0) in value.children.iter().enumerate() {
visitor.push_index(index0);
if !visitor.record(&Tree::taut_binding().bind(item0)) { return false; }
visitor.pop();
}
}
true });
}
