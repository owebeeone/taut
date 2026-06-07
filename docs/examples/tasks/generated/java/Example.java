// Tasks example — build a Task, round-trip it through the generated codec.
// Run: javac *.java -d out && java -cp out taut.Example
package taut;

import java.util.List;

public class Example {
    public static void main(String[] args) {
        User ann = new User(); ann.id = 7; ann.name = "ann";
        User bob = new User(); bob.id = 2; bob.name = "bob";
        Comment c = new Comment(); c.author = bob; c.text = "lgtm";
        Task t = new Task();
        t.id = 1; t.title = "ship taut"; t.state = TaskState.DONE; t.assignee = ann; t.comments = List.of(c);
        byte[] bytes = Cbor.encode(t.toCbor());
        Task back = Task.fromCbor(Cbor.decode(bytes));
        boolean ok = java.util.Arrays.equals(Cbor.encode(back.toCbor()), bytes);
        System.out.println("java: Task round-tripped in " + bytes.length + " bytes (" + (ok ? "ok" : "MISMATCH") + ")");
    }
}
