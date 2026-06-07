// GENERATED server handler interface stub.
package taut

interface TasksHandlers {
    fun create(title: String): Task
    fun comment(task_id: Long, author: User, text: String): Comment
    fun set_state(id: Long, state: TaskState): Boolean
    // tasks_subscribe: subscription (atom)
    // activity_subscribe: subscription (log)
}
