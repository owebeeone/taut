package taut.validation.descriptors;
/** Immutable portable metadata byte value, distinct from live message storage. */
public final class ImmutableBytes {
    private final byte[] storage;
    public ImmutableBytes(byte[] value) { storage=value.clone(); }
    public byte[] bytes() { return storage.clone(); }
}
