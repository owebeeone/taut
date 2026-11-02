import taut.*

fun main() {
    val draft = Content(ContentKind.number, text = "extra")
    val before = draft.validate()
    check(before.issues.map { it.code } == listOf("oneof.payload_unexpected", "oneof.payload_missing"))
    println(before.issues.joinToString { it.code + ":" + it.path.joinToString(".") { p -> p.fieldName ?: "?" } })
    val wire = encode(draft.toCbor())
    check(Content.decode(wire).text == "extra")
    draft.text = null
    draft.number = 0
    check(draft.isValid() && before.issues.size == 2)
    val virtual = VirtualEnvelope(draft)
    check(virtual.validate().isValid() && !virtual.validate().isComplete())
    check(!virtual.isValid())
    println("repaired=true; snapshotIssues=${before.issues.size}; virtualComplete=${virtual.validate().isComplete()}")
    println("descriptor=${Content.descriptor().qualifiedName}; fields=${Content.descriptor().fields.size}")
}
