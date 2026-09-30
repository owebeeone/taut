// Tasks example — build a Task, round-trip it through the generated codec.
// Run: kotlinc *.kt -include-runtime -d example.jar && java -cp example.jar taut.ExampleKt
package taut

import kotlin.system.exitProcess

fun main() {
    val task = Task(
        id = 1, title = "ship taut", state = TaskState.done,
        assignee = User(id = 7, name = "ann"),
        comments = listOf(Comment(author = User(id = 2, name = "bob"), text = "lgtm")),
        labels = mapOf("team" to "infra", "area" to "wire"),
    )
    val bytes = encode(task.toCbor())
    // The typed decode from bytes, under Task's bounds (Task.MAX_DEPTH, Task.MAX_ENCODED_LEN).
    val back = Task.decode(bytes)
    // Decode is fail-closed: bytes cut short throw DecodeError, nothing else.
    val cut = try {
        Task.decode(bytes.copyOf(bytes.size - 1))
        null
    } catch (e: DecodeError) {
        e
    }
    val ok = back == task && encode(back.toCbor()).contentEquals(bytes) && cut is DecodeError.Truncated
    println("kotlin: Task round-tripped in ${bytes.size} bytes (${if (ok) "ok" else "MISMATCH"})")
    if (!ok) {
        exitProcess(1)
    }
}
