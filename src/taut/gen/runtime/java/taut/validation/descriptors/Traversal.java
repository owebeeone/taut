package taut.validation.descriptors;
import java.util.List;
import taut.validation.PathSegment;
/** Runtime traversal SPI; generated typed adapters never depend on the optional engine. */
public interface Traversal {
    <T> boolean message(T value, MessageAdapter<T> adapter, List<PathSegment> path);
    boolean issue(String code, String rule, List<PathSegment> path, String message);
    boolean enter(Object value, List<PathSegment> path);
    void leave(Object value);
    boolean continueAfterCycle();
}
