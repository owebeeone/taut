// GENERATED native Kotlin types + codec — do not edit.
// Pairs with the vendored cbor.kt runtime (same package).
package taut

enum class TaskState(val wire: Long) {
    `open`(0), doing(1), done(2);
    companion object { fun fromWire(v: Long) = values().first { it.wire == v } }
}

data class User(
    var id: Long,
    var name: String,
) {
    fun toCbor(): Cbor {
        return Cbor.map(listOf(1L to Cbor.int(id), 2L to Cbor.text(name)))
    }
    companion object {
        fun fromCbor(c: Cbor): User {
            return User(
                id = c.get(1).intVal,
                name = c.get(2).textVal,
            )
        }
    }
}

data class Comment(
    var author: User,
    var text: String,
) {
    fun toCbor(): Cbor {
        return Cbor.map(listOf(1L to author.toCbor(), 2L to Cbor.text(text)))
    }
    companion object {
        fun fromCbor(c: Cbor): Comment {
            return Comment(
                author = User.fromCbor(c.get(1)),
                text = c.get(2).textVal,
            )
        }
    }
}

data class Task(
    var id: Long,
    var title: String,
    var state: TaskState,
    var assignee: User? = null,
    var comments: List<Comment>,
    var labels: Map<String, String>,
) {
    fun toCbor(): Cbor {
        return Cbor.map(listOf(1L to Cbor.int(id), 2L to Cbor.text(title), 3L to Cbor.int(state.wire), 4L to (assignee?.let { it.toCbor() } ?: Cbor.nul), 5L to Cbor.arr(comments.map { it.toCbor() }), 7L to Cbor.arr(labels.toSortedMap().map { Cbor.map(listOf(1L to Cbor.text(it.key), 2L to Cbor.text(it.value))) })))
    }
    companion object {
        fun fromCbor(c: Cbor): Task {
            return Task(
                id = c.get(1).intVal,
                title = c.get(2).textVal,
                state = TaskState.fromWire(c.get(3).intVal),
                assignee = c.get(4).let { if (it.isNull) null else User.fromCbor(it) },
                comments = c.get(5).arrVal.map { Comment.fromCbor(it) },
                labels = c.get(7).arrVal.associate { it.get(1).textVal to it.get(2).textVal },
            )
        }
    }
}

data class Event(
    var ts: Long,
    var text: String,
) {
    fun toCbor(): Cbor {
        return Cbor.map(listOf(1L to Cbor.int(ts), 2L to Cbor.text(text)))
    }
    companion object {
        fun fromCbor(c: Cbor): Event {
            return Event(
                ts = c.get(1).intVal,
                text = c.get(2).textVal,
            )
        }
    }
}

