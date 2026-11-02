package taut.validation;
/** Incompatible artifact or invalid runtime configuration, never a data diagnostic. */
public final class ConfigurationException extends IllegalArgumentException {
    public ConfigurationException(String message) { super(message + "; regenerate/rebind the compatible foundation and schema artifacts"); }
}
