// Tasks example — build a Task, round-trip it through the generated codec.
// Run: go test -v
package taut

import (
	"bytes"
	"errors"
	"testing"
)

func TestRoundtrip(t *testing.T) {
	task := Task{
		Id: 1, Title: "ship taut", State: TaskStateDone,
		Assignee: &User{Id: 7, Name: "ann"},
		Comments: []Comment{{Author: User{Id: 2, Name: "bob"}, Text: "lgtm"}},
		Labels:   map[string]string{"team": "infra", "area": "wire"},
	}
	b := Encode(task.ToCbor())
	// The typed decode from bytes, under Task's bounds (TaskMaxDepth, TaskMaxEncodedLen).
	back, err := TryTaskFromBytes(b)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	if !bytes.Equal(Encode(back.ToCbor()), b) {
		t.Fatal("round-trip mismatch")
	}
	// Decode is fail-closed: bytes cut short are a *DecodeError, never a panic.
	_, err = TryTaskFromBytes(b[:len(b)-1])
	var de *DecodeError
	if !errors.As(err, &de) || de.Tag != DecodeErrTruncated {
		t.Fatalf("bytes cut short: got %v, want Truncated", err)
	}
	t.Logf("go: Task round-tripped in %d bytes (ok)", len(b))
}
