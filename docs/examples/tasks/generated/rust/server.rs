// GENERATED server handler trait + registration sketch.
use crate::api::*;

pub trait TasksHandlers {
    fn create(&self, title: String) -> Task;
    fn comment(&self, task_id: i64, author: User, text: String) -> Comment;
    fn set_state(&self, id: i64, state: TaskState) -> bool;
    // tasks.subscribe: returns a subscription (atom)
    // activity.subscribe: returns a subscription (log)
}
// register(): for m in schema.services["Tasks"].methods { transport.register_method(m, ..) }
