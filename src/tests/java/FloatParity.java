package taut;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class FloatParity {
    private static final Pattern ROW = Pattern.compile(
            "\\{\\s*\"note\"\\s*:\\s*\"([^\"]+)\"\\s*,\\s*\"f64\"\\s*:\\s*\"([0-9a-fA-F]{16})\"\\s*,\\s*\"cbor\"\\s*:\\s*\"([0-9a-fA-F]+)\"\\s*\\}");

    public static void main(String[] args) throws Exception {
        Path vectors = Path.of(args.length == 0 ? "corpus/float_vectors.json" : args[0]);
        String json = Files.readString(vectors);
        Matcher rows = ROW.matcher(json);
        int count = 0;
        while (rows.find()) {
            String note = rows.group(1);
            long bits = Long.parseUnsignedLong(rows.group(2), 16);
            byte[] expected = fromHex(rows.group(3));
            double value = Double.longBitsToDouble(bits);

            byte[] encoded = Cbor.encode(Cbor.float_(value));
            check(Arrays.equals(encoded, expected), note + " encode got " + toHex(encoded));

            Cbor decoded = Cbor.decode(expected);
            check(decoded.kind == Cbor.FLOAT, note + " decoded kind " + decoded.kind);

            byte[] reencoded = Cbor.encode(decoded);
            check(Arrays.equals(reencoded, expected), note + " re-encode got " + toHex(reencoded));

            if (!note.startsWith("nan")) {
                long decodedBits = Double.doubleToRawLongBits(decoded.d);
                check(decodedBits == bits, note + " decode bits got " + Long.toHexString(decodedBits));
            }
            count++;
        }
        check(count == 22, "expected 22 rows, got " + count);
        System.out.println("ok " + count + " float vectors");
    }

    private static void check(boolean ok, String msg) {
        if (!ok) throw new AssertionError(msg);
    }

    private static byte[] fromHex(String hex) {
        byte[] out = new byte[hex.length() / 2];
        for (int i = 0; i < out.length; i++) {
            out[i] = (byte) Integer.parseInt(hex.substring(i * 2, i * 2 + 2), 16);
        }
        return out;
    }

    private static String toHex(byte[] bytes) {
        StringBuilder out = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) out.append(String.format("%02x", b & 0xff));
        return out.toString();
    }
}
