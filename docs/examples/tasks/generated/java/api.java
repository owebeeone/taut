// GENERATED native Java types + codec — do not edit. Pairs with Cbor.java.
package taut;

enum TaskState {
    OPEN(0), DOING(1), DONE(2);
    final long wire;
    TaskState(long w) { this.wire = w; }
    static TaskState fromWire(long v) { for (var e : values()) if (e.wire == v) return e; throw new RuntimeException("bad wire " + v); }
}

class User {
    public long id;
    public String name;
    Cbor toCbor() {
        java.util.List<KV> m = new java.util.ArrayList<>();
        m.add(new KV(1, Cbor.int_(id)));
        m.add(new KV(2, Cbor.text(name)));
        return Cbor.map(m);
    }
    static User fromCbor(Cbor c) {
        User v = new User();
        v.id = c.get(1).i;
        v.name = c.get(2).s;
        return v;
    }
}

class Comment {
    public User author;
    public String text;
    Cbor toCbor() {
        java.util.List<KV> m = new java.util.ArrayList<>();
        m.add(new KV(1, author.toCbor()));
        m.add(new KV(2, Cbor.text(text)));
        return Cbor.map(m);
    }
    static Comment fromCbor(Cbor c) {
        Comment v = new Comment();
        v.author = User.fromCbor(c.get(1));
        v.text = c.get(2).s;
        return v;
    }
}

class Task {
    public long id;
    public String title;
    public TaskState state;
    public User assignee;
    public java.util.List<Comment> comments;
    Cbor toCbor() {
        java.util.List<KV> m = new java.util.ArrayList<>();
        m.add(new KV(1, Cbor.int_(id)));
        m.add(new KV(2, Cbor.text(title)));
        m.add(new KV(3, Cbor.int_(state.wire)));
        m.add(new KV(4, assignee != null ? assignee.toCbor() : Cbor.NUL));
        m.add(new KV(5, Cbor.arr(comments.stream().map(e -> e.toCbor()).toList())));
        return Cbor.map(m);
    }
    static Task fromCbor(Cbor c) {
        Task v = new Task();
        v.id = c.get(1).i;
        v.title = c.get(2).s;
        v.state = TaskState.fromWire(c.get(3).i);
        { Cbor f = c.get(4); v.assignee = f.isNull() ? null : User.fromCbor(f); }
        v.comments = c.get(5).arr.stream().map(e -> Comment.fromCbor(e)).toList();
        return v;
    }
}

class Event {
    public long ts;
    public String text;
    Cbor toCbor() {
        java.util.List<KV> m = new java.util.ArrayList<>();
        m.add(new KV(1, Cbor.int_(ts)));
        m.add(new KV(2, Cbor.text(text)));
        return Cbor.map(m);
    }
    static Event fromCbor(Cbor c) {
        Event v = new Event();
        v.ts = c.get(1).i;
        v.text = c.get(2).s;
        return v;
    }
}

