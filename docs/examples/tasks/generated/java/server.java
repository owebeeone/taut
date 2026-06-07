// GENERATED server handler interface stub.
package taut;

interface TasksHandlers {
    Task create(String title);
    Comment comment(long task_id, User author, String text);
    boolean set_state(long id, TaskState state);
    // tasks_subscribe: subscription (atom)
    // activity_subscribe: subscription (log)
}
