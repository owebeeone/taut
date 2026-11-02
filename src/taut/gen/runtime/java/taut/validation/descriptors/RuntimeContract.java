package taut.validation.descriptors;
import taut.validation.ConfigurationException;
public final class RuntimeContract {
    public static final String OWNER="taut.java.foundation", BUILD="java-oneof-reference.1";
    private RuntimeContract() {}
    public static void require(String artifact, String owner, int descriptor, int codec, String... capabilities) {
        if (!OWNER.equals(owner) || descriptor!=1 || codec!=1) throw new ConfigurationException(artifact + ": required owner=" + OWNER + ", descriptor=1, codec=1; found " + owner + "/" + descriptor + "/" + codec);
        taut.Cbor.requireContract(artifact, owner, codec);
        for(String capability:capabilities) if(!capability.equals("descriptors.v1") && !capability.equals("codec.v1") && !capability.equals("oneof.v1")) throw new ConfigurationException(artifact + ": unsupported capability " + capability);
    }
}
