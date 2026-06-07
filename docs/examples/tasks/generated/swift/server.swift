// GENERATED server handler protocol stub.
public protocol TasksHandlers {
    func create(title: String) -> Task
    func comment(task_id: Int64, author: User, text: String) -> Comment
    func set_state(id: Int64, state: TaskState) -> Bool
    // tasks_subscribe: subscription (atom)
    // activity_subscribe: subscription (log)
}
