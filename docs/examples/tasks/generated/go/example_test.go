// Tasks example — build a Task, round-trip it through the generated codec.
// Run: go test -v
package taut

import "testing"

func TestRoundtrip(t *testing.T) {
	task := Task{
		Id: 1, Title: "ship taut", State: TaskStateDone,
		Assignee: &User{Id: 7, Name: "ann"},
		Comments: []Comment{{Author: User{Id: 2, Name: "bob"}, Text: "lgtm"}},
	}
	b := Encode(task.ToCbor())
	back := TaskFromCbor(Decode(b))
	if string(Encode(back.ToCbor())) != string(b) {
		t.Fatal("round-trip mismatch")
	}
	t.Logf("go: Task round-tripped in %d bytes (ok)", len(b))
}
