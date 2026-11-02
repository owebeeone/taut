// One predicate stream drives both full reports and the short-circuit Boolean.
package taut

type validationWalk struct {
	recursive, fast bool
	issues          []ValidationIssue
	deferred        []DeferredCheck
	ancestors       map[any]bool
}

func (w *validationWalk) Enter(identity any, path []PathSegment) (bool, bool) {
	if identity == nil {
		return false, true
	}
	if w.ancestors[identity] {
		return false, w.Issue("validation.ownership_cycle", "validation.shape.v1", path, "active ancestor encountered")
	}
	w.ancestors[identity] = true
	return true, true
}
func (w *validationWalk) Leave(identity any) { delete(w.ancestors, identity) }

func (w *validationWalk) Issue(code, rule string, path []PathSegment, message string) bool {
	if w.fast {
		return false
	}
	w.issues = append(w.issues, NewValidationIssue(code, rule, path, message))
	return true
}
func (w *validationWalk) deferCheck(rule string, path []PathSegment, reason string) bool {
	if w.fast {
		return false
	}
	w.deferred = append(w.deferred, NewDeferredCheck(rule, path, reason, "virtual selection is not implemented"))
	return true
}
func (w *validationWalk) group(value any, b *messageBinding, g *oneOfDescriptor, index int, path []PathSegment) bool {
	if g.virtual {
		return w.deferCheck(OneOfRule, ChildPath(path, FieldPath(g.controlling)), "oneof.virtual_deferred")
	}
	tag, ok := b.enum(value, index)
	selected := ""
	found := false
	if ok {
		for member, n := range g.enum.rawEnumDescriptor().members {
			if tag == n {
				selected = g.members[member]
				found = true
				break
			}
		}
	}
	if !found {
		return w.Issue("oneof.invalid_discriminator", OneOfRule, ChildPath(path, FieldPath(g.controlling)), "expected a member of controlling enum")
	}
	for i, f := range b.descriptor.rawMessageDescriptor().fields {
		payload := false
		for _, p := range g.members {
			if p == f.rawFieldDescriptor().name {
				payload = true
				break
			}
		}
		if !payload {
			continue
		}
		present := b.present(value, i)
		code := ""
		if f.rawFieldDescriptor().name == selected && !present {
			code = "oneof.payload_missing"
		} else if f.rawFieldDescriptor().name != selected && present {
			code = "oneof.payload_unexpected"
		}
		if code != "" && !w.Issue(code, OneOfRule, ChildPath(path, FieldPath(f.rawFieldDescriptor().name)), "oneof payload presence") {
			return false
		}
	}
	return true
}
func (w *validationWalk) Record(value any, binding MessageBinding, path []PathSegment) bool {
	if binding == nil || binding.Descriptor() == nil {
		panic("missing Go mandatory typed descriptor; regenerate/rebind")
	}
	b := binding.rawMessageBinding()
	if !descriptorPublished(b.descriptor) {
		panic("unpublished Go descriptor links; publish complete schema before validation")
	}
	if !b.accepts(value) {
		return w.Issue("validation.type_mismatch", "validation.shape.v1", path, "expected non-nil generated message pointer")
	}
	entered, keepGoing := w.Enter(value, path)
	if !entered {
		return keepGoing
	}
	defer w.Leave(value)
	for i, f := range b.descriptor.rawMessageDescriptor().fields {
		g := b.descriptor.rawMessageDescriptor().groupAt[i]
		if g != nil && !w.group(value, b, g.rawOneOfDescriptor(), i, path) {
			return false
		}
		if w.recursive && !f.rawFieldDescriptor().virtual && g == nil && b.present(value, i) {
			if !b.walk(value, i, w, ChildPath(path, FieldPath(f.rawFieldDescriptor().name))) {
				return false
			}
		}
	}
	return true
}
func ValidateRecord(value any, binding MessageBinding, recursive bool) ValidationReport {
	w := &validationWalk{recursive: recursive, ancestors: map[any]bool{}}
	w.Record(value, binding, nil)
	scope := "local"
	if recursive {
		scope = "recursive"
	}
	return NewValidationReport(w.issues, w.deferred, scope)
}
func IsRecordValid(value any, binding MessageBinding, recursive bool) bool {
	w := &validationWalk{recursive: recursive, fast: true, ancestors: map[any]bool{}}
	return w.Record(value, binding, nil)
}
