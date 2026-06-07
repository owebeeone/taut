// Tasks example — build a Task, round-trip it through the generated codec.
// Run: kotlinc *.kt -include-runtime -d example.jar && java -cp example.jar taut.ExampleKt
package taut

fun main() {
    val task = Task(
        id = 1, title = "ship taut", state = TaskState.done,
        assignee = User(id = 7, name = "ann"),
        comments = listOf(Comment(author = User(id = 2, name = "bob"), text = "lgtm")),
        labels = mapOf("team" to "infra", "area" to "wire"),
    )
    val bytes = encode(task.toCbor())
    val back = Task.fromCbor(decode(bytes))
    val ok = encode(back.toCbor()).contentEquals(bytes)
    println("kotlin: Task round-tripped in ${bytes.size} bytes (${if (ok) "ok" else "MISMATCH"})")
}
