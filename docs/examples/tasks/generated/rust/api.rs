// GENERATED native Rust types + codec — do not edit.
#![allow(dead_code)]
use crate::cbor::{Cbor, DecodeError};

// The file's bounds, for a decode rooted at a type that is not a message:
// `cbor::try_decode_with(bytes, MAX_DEPTH, MAX_ENCODED_LEN)`.
pub const MAX_DEPTH: usize = 32;
pub const MAX_ENCODED_LEN: Option<usize> = None;

#[derive(Clone, Copy, Debug, PartialEq, Default)]
pub enum TaskState {
    #[default] Open,
    Doing,
    Done,
}
impl TaskState {
    pub fn wire(self) -> i64 { match self {
        Self::Open => 0,
        Self::Doing => 1,
        Self::Done => 2,
    } }
    pub fn from_wire(v: i64) -> Result<Self, DecodeError> { Ok(match v {
        0 => Self::Open,
        1 => Self::Doing,
        2 => Self::Done,
        _ => return Err(DecodeError::UnknownEnum { enum_name: "TaskState", value: v }),
    }) }
}

#[derive(Clone, Debug, PartialEq, Default)]
pub struct User {
    pub id: i64,
    pub name: String,
}
impl User {
    pub const MAX_DEPTH: usize = 32;
    pub const MAX_ENCODED_LEN: Option<usize> = None;
    pub fn to_cbor(&self) -> Cbor {
        Cbor::Map(vec![
            (1, Cbor::Int(self.id)),
            (2, Cbor::Text(self.name.clone())),
        ])
    }
    pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError> {
        Ok(Self {
            id: c.try_get(1)?.try_int()?,
            name: c.try_get(2)?.try_text()?,
        })
    }
    pub fn decode(bytes: &[u8]) -> Result<Self, DecodeError> {
        Self::from_cbor(&crate::cbor::try_decode_with(bytes, Self::MAX_DEPTH, Self::MAX_ENCODED_LEN)?)
    }
}

#[derive(Clone, Debug, PartialEq, Default)]
pub struct Comment {
    pub author: User,
    pub text: String,
}
impl Comment {
    pub const MAX_DEPTH: usize = 32;
    pub const MAX_ENCODED_LEN: Option<usize> = None;
    pub fn to_cbor(&self) -> Cbor {
        Cbor::Map(vec![
            (1, self.author.to_cbor()),
            (2, Cbor::Text(self.text.clone())),
        ])
    }
    pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError> {
        Ok(Self {
            author: User::from_cbor(c.try_get(1)?)?,
            text: c.try_get(2)?.try_text()?,
        })
    }
    pub fn decode(bytes: &[u8]) -> Result<Self, DecodeError> {
        Self::from_cbor(&crate::cbor::try_decode_with(bytes, Self::MAX_DEPTH, Self::MAX_ENCODED_LEN)?)
    }
}

#[derive(Clone, Debug, PartialEq, Default)]
pub struct Task {
    pub id: i64,
    pub title: String,
    pub state: TaskState,
    pub assignee: Option<User>,
    pub comments: Vec<Comment>,
    pub labels: std::collections::BTreeMap<String, String>,
}
impl Task {
    pub const MAX_DEPTH: usize = 32;
    pub const MAX_ENCODED_LEN: Option<usize> = None;
    pub fn to_cbor(&self) -> Cbor {
        Cbor::Map(vec![
            (1, Cbor::Int(self.id)),
            (2, Cbor::Text(self.title.clone())),
            (3, Cbor::Int(self.state.wire())),
            (4, match &self.assignee { Some(v) => v.to_cbor(), None => Cbor::Null }),
            (5, Cbor::Array(self.comments.iter().map(|x| x.to_cbor()).collect())),
            (7, Cbor::Array(self.labels.iter().map(|(k, v)| Cbor::Map(vec![(1, Cbor::Text(k.clone())), (2, Cbor::Text(v.clone()))])).collect())),
        ])
    }
    pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError> {
        Ok(Self {
            id: c.try_get(1)?.try_int()?,
            title: c.try_get(2)?.try_text()?,
            state: TaskState::from_wire(c.try_get(3)?.try_int()?)?,
            assignee: { let v = c.try_get(4)?; if v.is_null() { None } else { Some(User::from_cbor(v)?) } },
            comments: c.try_get(5)?.try_array()?.iter().map(|x| Comment::from_cbor(x)).collect::<Result<Vec<_>, DecodeError>>()?,
            labels: { let mut m = std::collections::BTreeMap::new(); for e in c.try_get(7)?.try_array()? { let ek = e.try_get(1)?; let ev = e.try_get(2)?; let k = ek.try_text()?; if m.contains_key(&k) { return Err(DecodeError::DuplicateMapKey(k.into())); } m.insert(k, ev.try_text()?); } m },
        })
    }
    pub fn decode(bytes: &[u8]) -> Result<Self, DecodeError> {
        Self::from_cbor(&crate::cbor::try_decode_with(bytes, Self::MAX_DEPTH, Self::MAX_ENCODED_LEN)?)
    }
}

#[derive(Clone, Debug, PartialEq, Default)]
pub struct Event {
    pub ts: i64,
    pub text: String,
}
impl Event {
    pub const MAX_DEPTH: usize = 32;
    pub const MAX_ENCODED_LEN: Option<usize> = None;
    pub fn to_cbor(&self) -> Cbor {
        Cbor::Map(vec![
            (1, Cbor::Int(self.ts)),
            (2, Cbor::Text(self.text.clone())),
        ])
    }
    pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError> {
        Ok(Self {
            ts: c.try_get(1)?.try_int()?,
            text: c.try_get(2)?.try_text()?,
        })
    }
    pub fn decode(bytes: &[u8]) -> Result<Self, DecodeError> {
        Self::from_cbor(&crate::cbor::try_decode_with(bytes, Self::MAX_DEPTH, Self::MAX_ENCODED_LEN)?)
    }
}
