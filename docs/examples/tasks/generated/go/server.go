// GENERATED server handler interface stub.
package taut

type TasksHandlers interface {
	Create(title string) Task
	Comment(task_id int64, author User, text string) Comment
	SetState(id int64, state TaskState) bool
	// Tasks.subscribe: subscription (atom)
	// Activity.subscribe: subscription (log)
}
