// Canonical immutable Go diagnostics; optional validation layer.
package taut

type ValidationIssue struct {
	code, rule string
	path       []PathSegment
	message    string
}

func NewValidationIssue(code, rule string, path []PathSegment, message string) ValidationIssue {
	return ValidationIssue{code, rule, ownPath(path), message}
}
func (i ValidationIssue) Code() string        { return i.code }
func (i ValidationIssue) Rule() string        { return i.rule }
func (i ValidationIssue) Path() []PathSegment { return ownPath(i.path) }
func (i ValidationIssue) Message() string     { return i.message }

type DeferredCheck struct {
	rule            string
	path            []PathSegment
	reason, message string
}

func NewDeferredCheck(rule string, path []PathSegment, reason, message string) DeferredCheck {
	return DeferredCheck{rule, ownPath(path), reason, message}
}
func (d DeferredCheck) Rule() string        { return d.rule }
func (d DeferredCheck) Path() []PathSegment { return ownPath(d.path) }
func (d DeferredCheck) ReasonCode() string  { return d.reason }
func (d DeferredCheck) Message() string     { return d.message }

type ValidationReport struct {
	issues   []ValidationIssue
	deferred []DeferredCheck
	scope    string
}

func NewValidationReport(issues []ValidationIssue, deferred []DeferredCheck, scope string) ValidationReport {
	if scope == "" {
		scope = "recursive"
	}
	if scope != "recursive" && scope != "local" {
		panic("invalid validation scope")
	}
	r := ValidationReport{scope: scope}
	for _, i := range issues {
		r.issues = append(r.issues, NewValidationIssue(i.code, i.rule, i.path, i.message))
	}
	for _, d := range deferred {
		r.deferred = append(r.deferred, NewDeferredCheck(d.rule, d.path, d.reason, d.message))
	}
	return r
}
func (r ValidationReport) Issues() []ValidationIssue {
	return append([]ValidationIssue(nil), r.issues...)
}
func (r ValidationReport) DeferredChecks() []DeferredCheck {
	return append([]DeferredCheck(nil), r.deferred...)
}
func (r ValidationReport) Scope() string {
	if r.scope == "" {
		return "recursive"
	}
	return r.scope
}
func (r ValidationReport) IsValid() bool    { return len(r.issues) == 0 }
func (r ValidationReport) IsComplete() bool { return len(r.deferred) == 0 }

type ValidationOptions struct{ Recursive bool }
