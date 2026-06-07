// GENERATED typed client over the generic prism Client.
use crate::api::*;
use crate::client::Client;
use crate::cbor::Cbor;

pub struct TasksClient<'a> { c: &'a Client }

impl<'a> TasksClient<'a> {
    pub fn new(c: &'a Client) -> Self { Self { c } }
    // create(title) -> Task
    // self.c.call("create", &[..encode args..]).await -> Task::from_cbor(..)
    // comment(task_id, author, text) -> Comment
    // self.c.call("comment", &[..encode args..]).await -> Comment::from_cbor(..)
    // set_state(id, state) -> bool
    // self.c.call("set_state", &[..encode args..]).await -> bool::from_cbor(..)
    // tasks.subscribe: subscribe ("atom") -> stream of ['replace']
    // activity.subscribe: subscribe ("log") -> stream of ['append']
}
