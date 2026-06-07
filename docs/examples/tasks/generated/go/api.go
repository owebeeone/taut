// GENERATED native Go types + codec — do not edit.
// Pairs with the vendored cbor.go runtime (same package).
package taut

import "sort"

type TaskState int64

const (
	TaskStateOpen TaskState = 0
	TaskStateDoing TaskState = 1
	TaskStateDone TaskState = 2
)

type User struct {
	Id int64
	Name string
}

func (x User) ToCbor() Cbor {
	m := []KV{
		{K: 1, V: CInt(x.Id)},
		{K: 2, V: CText(x.Name)},
	}
	return CMap(m)
}

func UserFromCbor(c Cbor) User {
	var v User
	v.Id = c.Get(1).Int()
	v.Name = c.Get(2).Text()
	return v
}

type Comment struct {
	Author User
	Text string
}

func (x Comment) ToCbor() Cbor {
	m := []KV{
		{K: 1, V: x.Author.ToCbor()},
		{K: 2, V: CText(x.Text)},
	}
	return CMap(m)
}

func CommentFromCbor(c Cbor) Comment {
	var v Comment
	v.Author = UserFromCbor(c.Get(1))
	v.Text = c.Get(2).Text()
	return v
}

type Task struct {
	Id int64
	Title string
	State TaskState
	Assignee *User
	Comments []Comment
	Labels map[string]string
}

func (x Task) ToCbor() Cbor {
	m := []KV{
		{K: 1, V: CInt(x.Id)},
		{K: 2, V: CText(x.Title)},
		{K: 3, V: CInt(int64(x.State))},
		{K: 4, V: func() Cbor { if x.Assignee != nil { return (*x.Assignee).ToCbor() }; return CNull() }()},
		{K: 5, V: func() Cbor { a := []Cbor{}; for _, e := range x.Comments { a = append(a, e.ToCbor()) }; return CArr(a) }()},
		{K: 7, V: func() Cbor { ks := make([]string, 0, len(x.Labels)); for k := range x.Labels { ks = append(ks, k) }; sort.Slice(ks, func(i, j int) bool { return ks[i] < ks[j] }); a := []Cbor{}; for _, k := range ks { a = append(a, CMap([]KV{{K: 1, V: CText(k)}, {K: 2, V: CText(x.Labels[k])}})) }; return CArr(a) }()},
	}
	return CMap(m)
}

func TaskFromCbor(c Cbor) Task {
	var v Task
	v.Id = c.Get(1).Int()
	v.Title = c.Get(2).Text()
	v.State = TaskState(c.Get(3).Int())
	if fv := c.Get(4); !fv.IsNull() { t := UserFromCbor(fv); v.Assignee = &t }
	for _, e := range c.Get(5).Array() { v.Comments = append(v.Comments, CommentFromCbor(e)) }
	v.Labels = map[string]string{}
	for _, e := range c.Get(7).Array() { v.Labels[e.Get(1).Text()] = e.Get(2).Text() }
	return v
}

type Event struct {
	Ts int64
	Text string
}

func (x Event) ToCbor() Cbor {
	m := []KV{
		{K: 1, V: CInt(x.Ts)},
		{K: 2, V: CText(x.Text)},
	}
	return CMap(m)
}

func EventFromCbor(c Cbor) Event {
	var v Event
	v.Ts = c.Get(1).Int()
	v.Text = c.Get(2).Text()
	return v
}

