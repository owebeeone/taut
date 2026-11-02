// Canonical Kotlin foundation, internal build kotlin-oneof-reference.1.
package taut.validation.descriptors

import java.util.Collections
import java.util.IdentityHashMap
import taut.Cbor

class ConfigurationError(message: String) : IllegalArgumentException(message)
const val ONEOF_RULE = "taut.oneof.v1"

fun <T> snapshot(values: Collection<T>): List<T> = Collections.unmodifiableList(ArrayList(values))
private fun freeze(value: Any?): Any? = when (value) {
    is Map<*, *> -> {
        if (value.keys.any { it !is String }) throw ConfigurationError("metadata option keys must be strings")
        Collections.unmodifiableMap(value.entries.associate { it.key to freeze(it.value) })
    }
    is Collection<*> -> snapshot(value.map { freeze(it) })
    is ByteArray -> ImmutableBytes(value)
    null, is String, is Long, is Int, is Double, is Boolean -> value
    else -> throw ConfigurationError("unsupported immutable metadata value")
}
class ImmutableBytes(bytes: ByteArray) {
    private val storage = bytes.copyOf()
    val bytes: ByteArray get() = storage.copyOf()
}
@Suppress("UNCHECKED_CAST")
fun options(values: Map<String, Any?>): Map<String, Any?> = freeze(values) as Map<String, Any?>

object Foundation {
    val owner = "taut.kotlin.foundation"
    const val build = "kotlin-oneof-reference.1"
    val descriptorContract = 1
    val codecContract = 1
    val capabilities: List<String> = snapshot(listOf("descriptors.v1", "codec.v1", "oneof.v1"))
    // This typed attachment makes the actual codec owner a build dependency.
    fun codecIdentity(value: Cbor): Cbor = taut.KotlinCodecContract.identity(value)
    fun require(artifact: String, owner: String, descriptor: Int, codec: Int, required: List<String>) {
        if (taut.KotlinCodecContract.owner != this.owner || taut.KotlinCodecContract.codecContract != codecContract)
            throw ConfigurationError("$artifact: Kotlin codec requires owner=${this.owner} codec=$codecContract; found ${taut.KotlinCodecContract.owner}/${taut.KotlinCodecContract.codecContract}; regenerate/rebind codec")
        if (owner != this.owner || descriptor != descriptorContract || codec != codecContract ||
            !capabilities.containsAll(required))
            throw ConfigurationError("$artifact: required Kotlin owner=$owner descriptor=$descriptor codec=$codec capabilities=$required; found ${this.owner}/$descriptorContract/$codecContract; regenerate/rebind")
    }
}

class TypeDescriptor(val kind: String, message: (() -> MessageDescriptor)? = null,
                     enum: (() -> EnumDescriptor)? = null, val element: TypeDescriptor? = null,
                     val key: TypeDescriptor? = null, val value: TypeDescriptor? = null) {
    private val messageLink: MessageDescriptor? by lazy { message?.invoke() }
    private val enumLink: EnumDescriptor? by lazy { enum?.invoke() }
    val message: (() -> MessageDescriptor)? = if (message == null) null else ({ messageLink!! })
    val enum: (() -> EnumDescriptor)? = if (enum == null) null else ({ enumLink!! })
    init {
        val mask = listOf(message != null, enum != null, element != null, key != null, value != null)
        val expected = when(kind) {
            "int", "str", "bool", "bytes", "float" -> listOf(false,false,false,false,false)
            "message" -> listOf(true,false,false,false,false)
            "enum" -> listOf(false,true,false,false,false)
            "list" -> listOf(false,false,true,false,false)
            "map" -> listOf(false,false,false,true,true)
            else -> throw ConfigurationError("unsupported descriptor kind $kind")
        }
        if (mask != expected) throw ConfigurationError("inconsistent $kind descriptor")
        if (kind == "map" && key!!.kind !in listOf("int", "str", "bool"))
            throw ConfigurationError("map requires int/str/bool key")
    }
}
class FieldDescriptor(val name: String, val attribute: String?, val number: Int,
                      val type: TypeDescriptor, val presence: String, val transient: Boolean,
                      val virtual: Boolean, options: Map<String, Any?> = emptyMap()) {
    val options = options(options)
    init {
        if (number <= 0 || presence !in listOf("required", "nullable", "missing_ok") || virtual != (attribute == null))
            throw ConfigurationError("$name: invalid field descriptor")
    }
}
class EnumMemberDescriptor(val name: String, val number: Long, options: Map<String, Any?> = emptyMap()) {
    val options = options(options)
}
class EnumDescriptor(val name: String, val qualifiedName: String, members: List<EnumMemberDescriptor>,
                     options: Map<String, Any?> = emptyMap()) {
    val members = snapshot(members)
    val options = options(options)
    init {
        if (members.isEmpty() || members.map { it.name }.distinct().size != members.size ||
            members.map { it.number }.distinct().size != members.size) throw ConfigurationError("$name: invalid enum members")
    }
}
class OneOfMemberDescriptor(val name: String, val number: Long, val payload: String?)
class OneOfDescriptor(val controllingField: String, enum: () -> EnumDescriptor,
                      val virtual: Boolean, val exhaustive: Boolean, members: List<OneOfMemberDescriptor>) {
    private val enumLink by lazy(enum)
    val enum: () -> EnumDescriptor = { enumLink }
    val members = snapshot(members)
}
class ConstraintDescriptor(val rule: String, parameters: Map<String, Any?> = emptyMap()) {
    val parameters = options(parameters)
}
class MessageDescriptor(val name: String, val qualifiedName: String, val descriptorContractVersion: Int,
                        fields: List<FieldDescriptor>, oneofs: List<OneOfDescriptor>,
                        constraints: List<ConstraintDescriptor>, reservedNumbers: List<Int>,
                        reservedNames: List<String>, val nextId: Int?, options: Map<String, Any?>,
                        effectiveOptions: Map<String, Any?>) {
    val fields = snapshot(fields)
    val oneofs = snapshot(oneofs)
    val constraints = snapshot(constraints)
    val reservedNumbers = snapshot(reservedNumbers)
    val reservedNames = snapshot(reservedNames)
    val options = options(options)
    val effectiveOptions = options(effectiveOptions)
    val fieldsByName: Map<String, FieldDescriptor> = Collections.unmodifiableMap(this.fields.associateBy { it.name })
    val groupsByField: Map<String, OneOfDescriptor> = Collections.unmodifiableMap(this.oneofs.associateBy { it.controllingField })
    private val indices = this.fields.mapIndexed { index, field -> field.name to index }.toMap()
    fun fieldIndex(name: String): Int = indices[name] ?: throw ConfigurationError("$qualifiedName: missing field $name")
    fun check() = check(IdentityHashMap<MessageDescriptor, Boolean>())
    private fun check(seen: IdentityHashMap<MessageDescriptor, Boolean>) {
        if (seen.put(this, true) != null) return
        Foundation.require(qualifiedName, Foundation.owner, descriptorContractVersion, 1, listOf("descriptors.v1"))
        if (fieldsByName.size != fields.size || fields.map { it.number }.distinct().size != fields.size ||
            fields.map { it.number } != fields.map { it.number }.sorted()) throw ConfigurationError("$qualifiedName: duplicate/unordered fields")
        if (reservedNumbers.distinct().size != reservedNumbers.size || reservedNames.distinct().size != reservedNames.size ||
            reservedNumbers.any { n -> n <= 0 || fields.any { it.number == n } } || reservedNames.any { it in fieldsByName } ||
            (nextId != null && nextId <= (fields.map { it.number } + reservedNumbers).maxOrNull().let { it ?: 0 }))
            throw ConfigurationError("$qualifiedName: invalid reservations/nextId")
        fun checkType(t: TypeDescriptor) {
            t.message?.invoke()?.check(seen)
            t.enum?.invoke() // stable, validated enum constructor
            t.element?.let { checkType(it) }; t.key?.let { checkType(it) }; t.value?.let { checkType(it) }
        }
        fields.forEach { checkType(it.type) }
        if (groupsByField.size != oneofs.size) throw ConfigurationError("$qualifiedName: duplicate oneof controller")
        val payloads = HashSet<String>()
        for (group in oneofs) {
            val field = fieldsByName[group.controllingField]
            val enum = group.enum()
            if (field == null || field.type.kind != "enum" || field.type.enum!!.invoke() !== enum ||
                field.virtual != group.virtual || field.presence != "required" ||
                group.members.size != enum.members.size ||
                group.members.associate { it.name to it.number } != enum.members.associate { it.name to it.number } ||
                (group.exhaustive && group.members.any { it.payload == null }))
                throw ConfigurationError("$qualifiedName: inconsistent oneof ${group.controllingField}")
            for (payload in group.members.mapNotNull { it.payload }.distinct()) {
                if (!payloads.add(payload) || fieldsByName[payload]?.presence !in listOf("nullable", "missing_ok"))
                    throw ConfigurationError("$qualifiedName: invalid/shared oneof payload $payload")
            }
        }
        val controls = constraints.map {
            if (it.rule != ONEOF_RULE || it.parameters.keys != setOf("controlling_field"))
                throw ConfigurationError("$qualifiedName: unsupported constraint ${it.rule}; regenerate/rebind")
            it.parameters["controlling_field"]
        }
        if (controls.distinct().size != controls.size || controls.toSet() != groupsByField.keys)
            throw ConfigurationError("$qualifiedName: inconsistent constraint/group links")
    }
}
class SchemaDescriptor(val descriptorContractVersion: Int, val irVersion: Int, val identity: String,
                       messages: Map<String, MessageDescriptor>, enums: Map<String, EnumDescriptor>,
                       options: Map<String, Any?>, effectiveOptions: Map<String, Any?>) {
    val messages: Map<String, MessageDescriptor> = Collections.unmodifiableMap(LinkedHashMap(messages))
    val enums: Map<String, EnumDescriptor> = Collections.unmodifiableMap(LinkedHashMap(enums))
    val options = options(options)
    val effectiveOptions = options(effectiveOptions)
    init {
        Foundation.require(identity, Foundation.owner, descriptorContractVersion, 1, listOf("descriptors.v1"))
        if (irVersion !in 1..3) throw ConfigurationError("$identity: unsupported IR $irVersion")
        this.messages.values.forEach { it.check() }
        if (this.messages.any { it.key != it.value.name } || this.enums.any { it.key != it.value.name })
            throw ConfigurationError("$identity: inconsistent registry keys")
        fun checkLink(t: TypeDescriptor) {
            t.message?.invoke()?.let { if (this.messages[it.name] !== it) throw ConfigurationError("$identity: dangling/wrong message registry link ${it.name}") }
            t.enum?.invoke()?.let { if (this.enums[it.name] !== it) throw ConfigurationError("$identity: dangling/wrong enum registry link ${it.name}") }
            t.element?.let { checkLink(it) }; t.key?.let { checkLink(it) }; t.value?.let { checkLink(it) }
        }
        this.messages.values.forEach { message -> message.fields.forEach { checkLink(it.type) } }
    }
}

interface ChildVisitor {
    fun record(value: RecordAccess): Boolean
    fun pushIndex(index: Long)
    fun pushKey(type: String, bytes: ByteArray)
    fun pop()
}
// Only this foundation can manufacture an erased pair. Generated message types
// do not inherit this class; the one bound record wraps a typed traversal root.
sealed class RecordAccess protected constructor() {
    abstract val descriptor: MessageDescriptor
    abstract val identity: Any
    abstract fun read(index: Int): Any?
    abstract fun children(index: Int, visitor: ChildVisitor): Boolean
    internal class Bound<T : Any>(private val value: T, private val binding: SchemaBinding<T>,
                                 override val descriptor: MessageDescriptor) : RecordAccess() {
        override val identity: Any get() = value
        override fun read(index: Int): Any? {
            if (descriptor.fields.getOrNull(index)?.virtual != false)
                throw ConfigurationError("${descriptor.qualifiedName}: no value accessor for virtual/unknown field $index")
            return binding.readTyped(value, index)
        }
        override fun children(index: Int, visitor: ChildVisitor): Boolean = binding.visitTyped(value, index, visitor)
    }
}
class SchemaBinding<T : Any>(val rawDescriptor: MessageDescriptor,
                            private val checkCompatibility: () -> Unit,
                            private val read: (T, Int) -> Any?,
                            private val visit: (T, Int, ChildVisitor) -> Boolean) {
    fun descriptor(): MessageDescriptor {
        checkCompatibility(); rawDescriptor.check(); return rawDescriptor
    }
    // T is invariant: a mismatched descriptor/value pair cannot be bound by generated callers.
    fun bind(value: T): RecordAccess {
        return RecordAccess.Bound(value, this, descriptor())
    }
    internal fun readTyped(value: T, index: Int): Any? = read(value, index)
    internal fun visitTyped(value: T, index: Int, visitor: ChildVisitor): Boolean = visit(value, index, visitor)
}

fun compareCanonical(a: ByteArray, b: ByteArray): Int {
    for (i in 0 until minOf(a.size, b.size)) {
        val cmp = (a[i].toInt() and 255).compareTo(b[i].toInt() and 255)
        if (cmp != 0) return cmp
    }
    return a.size.compareTo(b.size)
}
