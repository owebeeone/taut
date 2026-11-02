package probe
import java.util.Collections
class Descriptor(fields: List<String>) { val fields: List<String> = Collections.unmodifiableList(ArrayList(fields)) }
interface Record { val identity: Any; fun read(index: Int): Any? }
class Binding<T : Any>(val descriptor: Descriptor, val read: (T, Int) -> Any?) {
    fun bind(value: T): Record = object : Record {
        override val identity: Any get() = value
        override fun read(index: Int): Any? = this@Binding.read(value, index)
    }
}
enum class Tag(val wire: Long) { text(0), empty(1) }
class Message(var tag: Tag, var text: String?, var child: Message?)
fun main() {
    val fields = mutableListOf("tag", "text", "child")
    val d = Descriptor(fields)
    val b = Binding<Message>(d) { value, index -> when(index) { 0 -> value.tag.wire; 1 -> value.text; 2 -> value.child; else -> error("index") } }
    val child = Message(Tag.empty, "", null)
    val value = Message(Tag.text, "borrowed", child)
    val r = b.bind(value)
    check(r.identity === value && r.read(0) == 0L && r.read(1) === value.text)
    check(b.bind(r.read(2) as Message).identity === child)
    fields.clear(); check(d.fields.size == 3)
    try { (d.fields as MutableList<String>).clear(); error("mutable") } catch (_: UnsupportedOperationException) {}
    println("Kotlin typed adapter ABI probe PASS: direct enum/primitive reads, presence, child pairing, immutable snapshot")
}
