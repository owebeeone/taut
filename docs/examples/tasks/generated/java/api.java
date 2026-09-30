// GENERATED native Java types + codec — do not edit. Pairs with Cbor.java.
// Each message's codec is its own class, <Message>$Codec, where no field hides a name.
package taut;

enum TaskState {
    OPEN(0), DOING(1), DONE(2);
    final long wire;
    TaskState(long $w) { this.wire = $w; }
    static TaskState fromWire(long $v) {
        for (var $e : values()) {
            if ($e.wire == $v) {
                return $e;
            }
        }
        throw Cbor.DecodeError.unknownEnum("TaskState", $v);
    }
}

class User {
    public long id;
    public String name;
    static final int MAX_DEPTH = 32;
    static final Integer MAX_ENCODED_LEN = null;
    Cbor toCbor() { return User$Codec.toCbor(this); }
    static User fromCbor(Cbor $c) { return User$Codec.fromCbor($c); }
    static User decode(byte[] $bytes) { return User$Codec.decode($bytes); }
}

final class User$Codec {
    private User$Codec() {}
    static Cbor toCbor(User $self) {
        var $m = new java.util.ArrayList<KV>();
        $m.add(new KV(1, Cbor.int_($self.id)));
        $m.add(new KV(2, Cbor.text($self.name)));
        return Cbor.map($m);
    }
    static User fromCbor(Cbor $c) {
        if ($c.kind != Cbor.MAP) {
            throw Cbor.DecodeError.wrongType("map");
        }
        User $v = new User();
        $v.id = $c.get(1).asInt();
        $v.name = $c.get(2).asText();
        return $v;
    }
    static User decode(byte[] $bytes) {
        return fromCbor(Cbor.decode($bytes, User.MAX_DEPTH, User.MAX_ENCODED_LEN));
    }
}

class Comment {
    public User author;
    public String text;
    static final int MAX_DEPTH = 32;
    static final Integer MAX_ENCODED_LEN = null;
    Cbor toCbor() { return Comment$Codec.toCbor(this); }
    static Comment fromCbor(Cbor $c) { return Comment$Codec.fromCbor($c); }
    static Comment decode(byte[] $bytes) { return Comment$Codec.decode($bytes); }
}

final class Comment$Codec {
    private Comment$Codec() {}
    static Cbor toCbor(Comment $self) {
        var $m = new java.util.ArrayList<KV>();
        $m.add(new KV(1, $self.author.toCbor()));
        $m.add(new KV(2, Cbor.text($self.text)));
        return Cbor.map($m);
    }
    static Comment fromCbor(Cbor $c) {
        if ($c.kind != Cbor.MAP) {
            throw Cbor.DecodeError.wrongType("map");
        }
        Comment $v = new Comment();
        $v.author = User.fromCbor($c.get(1));
        $v.text = $c.get(2).asText();
        return $v;
    }
    static Comment decode(byte[] $bytes) {
        return fromCbor(Cbor.decode($bytes, Comment.MAX_DEPTH, Comment.MAX_ENCODED_LEN));
    }
}

class Task {
    public long id;
    public String title;
    public TaskState state;
    public User assignee;
    public java.util.List<Comment> comments;
    public java.util.Map<String, String> labels;
    static final int MAX_DEPTH = 32;
    static final Integer MAX_ENCODED_LEN = null;
    Cbor toCbor() { return Task$Codec.toCbor(this); }
    static Task fromCbor(Cbor $c) { return Task$Codec.fromCbor($c); }
    static Task decode(byte[] $bytes) { return Task$Codec.decode($bytes); }
}

final class Task$Codec {
    private Task$Codec() {}
    static Cbor toCbor(Task $self) {
        var $m = new java.util.ArrayList<KV>();
        $m.add(new KV(1, Cbor.int_($self.id)));
        $m.add(new KV(2, Cbor.text($self.title)));
        $m.add(new KV(3, Cbor.int_($self.state.wire)));
        $m.add(new KV(4, $self.assignee != null ? $self.assignee.toCbor() : Cbor.NUL));
        $m.add(new KV(5, Cbor.arr($self.comments.stream().map($e -> $e.toCbor()).toList())));
        $m.add(new KV(7, Cbor.arr(Cbor.sortedByCodePoint($self.labels).entrySet().stream().map($e -> Cbor.map(java.util.List.of(new KV(1, Cbor.text($e.getKey())), new KV(2, Cbor.text($e.getValue()))))).toList())));
        return Cbor.map($m);
    }
    static Task fromCbor(Cbor $c) {
        if ($c.kind != Cbor.MAP) {
            throw Cbor.DecodeError.wrongType("map");
        }
        Task $v = new Task();
        $v.id = $c.get(1).asInt();
        $v.title = $c.get(2).asText();
        $v.state = TaskState.fromWire($c.get(3).asInt());
        { Cbor $f = $c.get(4); $v.assignee = $f.isNull() ? null : User.fromCbor($f); }
        $v.comments = $c.get(5).asArray().stream().map($e -> Comment.fromCbor($e)).toList();
        $v.labels = Cbor.decodeMap($c.get(7), $e -> $e.get(1).asText(), $e -> $e.get(2).asText());
        return $v;
    }
    static Task decode(byte[] $bytes) {
        return fromCbor(Cbor.decode($bytes, Task.MAX_DEPTH, Task.MAX_ENCODED_LEN));
    }
}

class Event {
    public long ts;
    public String text;
    static final int MAX_DEPTH = 32;
    static final Integer MAX_ENCODED_LEN = null;
    Cbor toCbor() { return Event$Codec.toCbor(this); }
    static Event fromCbor(Cbor $c) { return Event$Codec.fromCbor($c); }
    static Event decode(byte[] $bytes) { return Event$Codec.decode($bytes); }
}

final class Event$Codec {
    private Event$Codec() {}
    static Cbor toCbor(Event $self) {
        var $m = new java.util.ArrayList<KV>();
        $m.add(new KV(1, Cbor.int_($self.ts)));
        $m.add(new KV(2, Cbor.text($self.text)));
        return Cbor.map($m);
    }
    static Event fromCbor(Cbor $c) {
        if ($c.kind != Cbor.MAP) {
            throw Cbor.DecodeError.wrongType("map");
        }
        Event $v = new Event();
        $v.ts = $c.get(1).asInt();
        $v.text = $c.get(2).asText();
        return $v;
    }
    static Event decode(byte[] $bytes) {
        return fromCbor(Cbor.decode($bytes, Event.MAX_DEPTH, Event.MAX_ENCODED_LEN));
    }
}

