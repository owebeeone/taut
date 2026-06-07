// GENERATED native Rust types + codec — do not edit.
#![allow(dead_code)]
use crate::cbor::Cbor;

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
    pub fn from_wire(v: i64) -> Self { match v {
        0 => Self::Open,
        1 => Self::Doing,
        2 => Self::Done,
        _ => panic!("bad TaskState wire value {}", v),
    } }
}

#[derive(Clone, Debug, PartialEq, Default)]
pub struct User {
    pub id: i64,
    pub name: String,
}
impl User {
    pub fn to_cbor(&self) -> Cbor {
        Cbor::Map(vec![
            (1, Cbor::Int(self.id)),
            (2, Cbor::Text(self.name.clone())),
        ])
    }
    pub fn from_cbor(c: &Cbor) -> Self {
        Self {
            id: c.get(1).int(),
            name: c.get(2).text(),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Default)]
pub struct Comment {
    pub author: User,
    pub text: String,
}
impl Comment {
    pub fn to_cbor(&self) -> Cbor {
        Cbor::Map(vec![
            (1, self.author.to_cbor()),
            (2, Cbor::Text(self.text.clone())),
        ])
    }
    pub fn from_cbor(c: &Cbor) -> Self {
        Self {
            author: User::from_cbor(c.get(1)),
            text: c.get(2).text(),
        }
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
    pub fn from_cbor(c: &Cbor) -> Self {
        Self {
            id: c.get(1).int(),
            title: c.get(2).text(),
            state: TaskState::from_wire(c.get(3).int()),
            assignee: { let v = c.get(4); if v.is_null() { None } else { Some(User::from_cbor(v)) } },
            comments: c.get(5).array().iter().map(|x| Comment::from_cbor(x)).collect(),
            labels: c.get(7).array().iter().map(|e| (e.get(1).text(), e.get(2).text())).collect(),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Default)]
pub struct Event {
    pub ts: i64,
    pub text: String,
}
impl Event {
    pub fn to_cbor(&self) -> Cbor {
        Cbor::Map(vec![
            (1, Cbor::Int(self.ts)),
            (2, Cbor::Text(self.text.clone())),
        ])
    }
    pub fn from_cbor(c: &Cbor) -> Self {
        Self {
            ts: c.get(1).int(),
            text: c.get(2).text(),
        }
    }
}

