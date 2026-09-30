// GENERATED native Go types + codec — do not edit.
// Pairs with the vendored cbor.go runtime (same package).
package taut

import "sort"

type TaskState int64

const (
	TaskStateOpen  TaskState = 0
	TaskStateDoing TaskState = 1
	TaskStateDone  TaskState = 2
)

func TryTaskStateFromWire(v int64) (TaskState, error) {
	switch v {
	case 0:
		return TaskStateOpen, nil
	case 1:
		return TaskStateDoing, nil
	case 2:
		return TaskStateDone, nil
	default:
		return 0, UnknownEnumError("TaskState", v)
	}
}

func TryTaskStateFromCbor(c Cbor) (TaskState, error) {
	v, err := c.TryInt()
	if err != nil {
		return 0, err
	}
	return TryTaskStateFromWire(v)
}

type User struct {
	Id   int64
	Name string
}

func (x User) ToCbor() Cbor {
	m := make([]KV, 0, 2)
	m = append(m, KV{K: 1, V: CInt(x.Id)})
	m = append(m, KV{K: 2, V: CText(x.Name)})
	return CMap(m)
}

func TryUserFromCbor(c Cbor) (User, error) {
	var v User
	if _, err := c.TryMap(); err != nil {
		return v, err
	}
	{
		fv, err := c.Require(1)
		if err != nil {
			return v, err
		}
		x, err := fv.TryInt()
		if err != nil {
			return v, err
		}
		v.Id = x
	}
	{
		fv, err := c.Require(2)
		if err != nil {
			return v, err
		}
		x, err := fv.TryText()
		if err != nil {
			return v, err
		}
		v.Name = x
	}
	return v, nil
}

// User's bounds: its effective max_depth and max_encoded_len (-1: none).
const (
	UserMaxDepth      = 32
	UserMaxEncodedLen = -1
)

// TryUserFromBytes decodes data rooted at User, under its bounds.
func TryUserFromBytes(data []byte) (User, error) {
	c, err := TryDecodeWith(data, UserMaxDepth, UserMaxEncodedLen)
	if err != nil {
		return User{}, err
	}
	return TryUserFromCbor(c)
}

type Comment struct {
	Author User
	Text   string
}

func (x Comment) ToCbor() Cbor {
	m := make([]KV, 0, 2)
	m = append(m, KV{K: 1, V: x.Author.ToCbor()})
	m = append(m, KV{K: 2, V: CText(x.Text)})
	return CMap(m)
}

func TryCommentFromCbor(c Cbor) (Comment, error) {
	var v Comment
	if _, err := c.TryMap(); err != nil {
		return v, err
	}
	{
		fv, err := c.Require(1)
		if err != nil {
			return v, err
		}
		x, err := TryUserFromCbor(fv)
		if err != nil {
			return v, err
		}
		v.Author = x
	}
	{
		fv, err := c.Require(2)
		if err != nil {
			return v, err
		}
		x, err := fv.TryText()
		if err != nil {
			return v, err
		}
		v.Text = x
	}
	return v, nil
}

// Comment's bounds: its effective max_depth and max_encoded_len (-1: none).
const (
	CommentMaxDepth      = 32
	CommentMaxEncodedLen = -1
)

// TryCommentFromBytes decodes data rooted at Comment, under its bounds.
func TryCommentFromBytes(data []byte) (Comment, error) {
	c, err := TryDecodeWith(data, CommentMaxDepth, CommentMaxEncodedLen)
	if err != nil {
		return Comment{}, err
	}
	return TryCommentFromCbor(c)
}

type Task struct {
	Id       int64
	Title    string
	State    TaskState
	Assignee *User
	Comments []Comment
	Labels   map[string]string
}

func (x Task) ToCbor() Cbor {
	m := make([]KV, 0, 6)
	m = append(m, KV{K: 1, V: CInt(x.Id)})
	m = append(m, KV{K: 2, V: CText(x.Title)})
	m = append(m, KV{K: 3, V: CInt(int64(x.State))})
	if x.Assignee == nil {
		m = append(m, KV{K: 4, V: CNull()})
	} else {
		m = append(m, KV{K: 4, V: (*x.Assignee).ToCbor()})
	}
	{
		a := make([]Cbor, 0, len(x.Comments))
		for _, e := range x.Comments {
			a = append(a, e.ToCbor())
		}
		m = append(m, KV{K: 5, V: CArr(a)})
	}
	{
		ks := make([]string, 0, len(x.Labels))
		for k := range x.Labels {
			ks = append(ks, k)
		}
		sort.Slice(ks, func(i, j int) bool { return ks[i] < ks[j] })
		a := make([]Cbor, 0, len(ks))
		for _, k := range ks {
			a = append(a, CMap([]KV{{K: 1, V: CText(k)}, {K: 2, V: CText(x.Labels[k])}}))
		}
		m = append(m, KV{K: 7, V: CArr(a)})
	}
	return CMap(m)
}

func TryTaskFromCbor(c Cbor) (Task, error) {
	var v Task
	if _, err := c.TryMap(); err != nil {
		return v, err
	}
	{
		fv, err := c.Require(1)
		if err != nil {
			return v, err
		}
		x, err := fv.TryInt()
		if err != nil {
			return v, err
		}
		v.Id = x
	}
	{
		fv, err := c.Require(2)
		if err != nil {
			return v, err
		}
		x, err := fv.TryText()
		if err != nil {
			return v, err
		}
		v.Title = x
	}
	{
		fv, err := c.Require(3)
		if err != nil {
			return v, err
		}
		x, err := TryTaskStateFromCbor(fv)
		if err != nil {
			return v, err
		}
		v.State = x
	}
	{
		fv, err := c.Require(4)
		if err != nil {
			return v, err
		}
		if !fv.IsNull() {
			x, err := TryUserFromCbor(fv)
			if err != nil {
				return v, err
			}
			v.Assignee = &x
		}
	}
	{
		fv, err := c.Require(5)
		if err != nil {
			return v, err
		}
		arr, err := fv.TryArray()
		if err != nil {
			return v, err
		}
		var x []Comment
		for _, e := range arr {
			x1, err := TryCommentFromCbor(e)
			if err != nil {
				return v, err
			}
			x = append(x, x1)
		}
		v.Comments = x
	}
	{
		fv, err := c.Require(7)
		if err != nil {
			return v, err
		}
		arr, err := fv.TryArray()
		if err != nil {
			return v, err
		}
		x := map[string]string{}
		for _, e := range arr {
			kc, err := e.Require(1)
			if err != nil {
				return v, err
			}
			vc, err := e.Require(2)
			if err != nil {
				return v, err
			}
			k, err := kc.TryText()
			if err != nil {
				return v, err
			}
			if _, dup := x[k]; dup {
				return v, DuplicateMapKeyError(k)
			}
			x1, err := vc.TryText()
			if err != nil {
				return v, err
			}
			x[k] = x1
		}
		v.Labels = x
	}
	return v, nil
}

// Task's bounds: its effective max_depth and max_encoded_len (-1: none).
const (
	TaskMaxDepth      = 32
	TaskMaxEncodedLen = -1
)

// TryTaskFromBytes decodes data rooted at Task, under its bounds.
func TryTaskFromBytes(data []byte) (Task, error) {
	c, err := TryDecodeWith(data, TaskMaxDepth, TaskMaxEncodedLen)
	if err != nil {
		return Task{}, err
	}
	return TryTaskFromCbor(c)
}

type Event struct {
	Ts   int64
	Text string
}

func (x Event) ToCbor() Cbor {
	m := make([]KV, 0, 2)
	m = append(m, KV{K: 1, V: CInt(x.Ts)})
	m = append(m, KV{K: 2, V: CText(x.Text)})
	return CMap(m)
}

func TryEventFromCbor(c Cbor) (Event, error) {
	var v Event
	if _, err := c.TryMap(); err != nil {
		return v, err
	}
	{
		fv, err := c.Require(1)
		if err != nil {
			return v, err
		}
		x, err := fv.TryInt()
		if err != nil {
			return v, err
		}
		v.Ts = x
	}
	{
		fv, err := c.Require(2)
		if err != nil {
			return v, err
		}
		x, err := fv.TryText()
		if err != nil {
			return v, err
		}
		v.Text = x
	}
	return v, nil
}

// Event's bounds: its effective max_depth and max_encoded_len (-1: none).
const (
	EventMaxDepth      = 32
	EventMaxEncodedLen = -1
)

// TryEventFromBytes decodes data rooted at Event, under its bounds.
func TryEventFromBytes(data []byte) (Event, error) {
	c, err := TryDecodeWith(data, EventMaxDepth, EventMaxEncodedLen)
	if err != nil {
		return Event{}, err
	}
	return TryEventFromCbor(c)
}
