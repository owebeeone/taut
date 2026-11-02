// Canonical Kotlin explicit validation. No reflection or common message base.
package taut.validation

import java.util.IdentityHashMap
import taut.validation.descriptors.*

class PathSegment private constructor(val kind: String, val fieldName: String?, val index: Long?,
                                      val keyType: String?, val keyCborBase64: String?) {
    companion object {
        fun forField(name: String) = PathSegment("field", name, null, null, null)
        fun forIndex(index: Long): PathSegment {
            require(index >= 0) { "path index must be nonnegative" }
            return PathSegment("index", null, index, null, null)
        }
        fun forKey(type: String, bytes: ByteArray): PathSegment {
            val value = taut.decode(bytes)
            val expected = when(value.kind) { taut.Cbor.INT -> "int"; taut.Cbor.TEXT -> "str"; taut.Cbor.BOOL -> "bool"; else -> "" }
            require(type == expected && bytes.contentEquals(taut.encode(value))) { "invalid/noncanonical Taut map key" }
            return PathSegment("key", null, null, type, base64(bytes))
        }
    }
}
private fun base64(bytes: ByteArray): String {
    val alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    val out = StringBuilder()
    var i = 0
    while (i < bytes.size) {
        val n = ((bytes[i].toInt() and 255) shl 16) or
            ((if (i + 1 < bytes.size) bytes[i+1].toInt() and 255 else 0) shl 8) or
            (if (i + 2 < bytes.size) bytes[i+2].toInt() and 255 else 0)
        out.append(alphabet[(n ushr 18) and 63]); out.append(alphabet[(n ushr 12) and 63])
        out.append(if (i+1 < bytes.size) alphabet[(n ushr 6) and 63] else '=')
        out.append(if (i+2 < bytes.size) alphabet[n and 63] else '='); i += 3
    }
    return out.toString()
}
class ValidationIssue(val code: String, val rule: String, path: List<PathSegment>, val message: String) {
    val path = snapshot(path)
}
class DeferredCheck(val rule: String, path: List<PathSegment>, val reasonCode: String, val message: String) {
    val path = snapshot(path)
}
class ValidationReport(issues: List<ValidationIssue> = emptyList(), deferredChecks: List<DeferredCheck> = emptyList(),
                       val scope: String = "recursive") {
    val issues = snapshot(issues)
    val deferredChecks = snapshot(deferredChecks)
    init { require(scope == "local" || scope == "recursive") { "invalid validation scope $scope" } }
    fun isValid(): Boolean = issues.isEmpty()
    fun isComplete(): Boolean = deferredChecks.isEmpty()
}
private class Engine(private val recursive: Boolean, private val full: Boolean) : ChildVisitor {
    val issues = if (full) ArrayList<ValidationIssue>() else null
    val deferred = if (full) ArrayList<DeferredCheck>() else null
    private val path = ArrayList<PathSegment>()
    private val ancestors = IdentityHashMap<Any, Boolean>()
    private fun event(code: String, field: String?, deferredCheck: Boolean = false, rule: String = ONEOF_RULE): Boolean {
        if (!full) return false
        val location = ArrayList(path)
        if (field != null) location.add(PathSegment.forField(field))
        if (deferredCheck) deferred!!.add(DeferredCheck(rule, location, code, code))
        else issues!!.add(ValidationIssue(code, rule, location, code))
        return true
    }
    private fun group(value: RecordAccess, group: OneOfDescriptor, index: Int): Boolean {
        if (group.virtual) return event("oneof.virtual_deferred", group.controllingField, true)
        val tag = value.read(index)
        val selected = group.members.find { it.number == tag }
            ?: return event("oneof.invalid_discriminator", group.controllingField)
        for ((i, field) in value.descriptor.fields.withIndex()) {
            if (group.members.none { it.payload == field.name }) continue
            val present = value.read(i) != null
            val code = when {
                selected.payload == field.name && !present -> "oneof.payload_missing"
                selected.payload != field.name && present -> "oneof.payload_unexpected"
                else -> null
            }
            if (code != null && !event(code, field.name)) return false
        }
        return true
    }
    override fun record(value: RecordAccess): Boolean {
        if (ancestors.containsKey(value.identity)) return event("validation.ownership_cycle", null, rule="validation.shape.v1")
        ancestors[value.identity] = true
        try {
            for ((i, field) in value.descriptor.fields.withIndex()) {
                value.descriptor.groupsByField[field.name]?.let { if (!group(value, it, i)) return false }
                if (recursive && !field.virtual && value.read(i) != null) {
                    if (full) path.add(PathSegment.forField(field.name))
                    val result = value.children(i, this)
                    if (full) path.removeAt(path.lastIndex)
                    if (!result) return false
                }
            }
            return true
        } finally { ancestors.remove(value.identity) }
    }
    override fun pushIndex(index: Long) { if (full) path.add(PathSegment.forIndex(index)) }
    override fun pushKey(type: String, bytes: ByteArray) { if (full) path.add(PathSegment.forKey(type, bytes)) }
    override fun pop() { if (full) path.removeAt(path.lastIndex) }
}
object ValidationEngine {
    val contract = 1
    fun validate(value: RecordAccess, recursive: Boolean = true): ValidationReport {
        val engine = Engine(recursive, true)
        engine.record(value)
        return ValidationReport(engine.issues!!, engine.deferred!!, if (recursive) "recursive" else "local")
    }
    fun isValid(value: RecordAccess, recursive: Boolean = true): Boolean = Engine(recursive, false).record(value)
}
