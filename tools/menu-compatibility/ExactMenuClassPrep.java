import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Arrays;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;

/** Preparation-time only. Nothing from this tool is added to a content JAR. */
public final class ExactMenuClassPrep {
    private static final String CLASS = "net/pedroksl/ae2addonlib/registry/MenuRegistry";
    private static final String ORIGINAL_SHA = "87e082cdc0e7738213f2ce26f6656e1655a479dcd546b58d40f368d51109b0a5";
    private static final String OWNER = "appeng/menu/implementations/MenuTypeBuilder";
    private static final String CALLER = "lambda$create$0";
    private static final String CALLER_DESC = "(Lappeng/menu/implementations/MenuTypeBuilder$MenuFactory;Ljava/lang/Class;Ljava/lang/String;Ljava/lang/String;)Lnet/minecraft/world/inventory/MenuType;";
    private static final String CALL_DESC = "(Lnet/minecraft/resources/ResourceLocation;)Lnet/minecraft/world/inventory/MenuType;";

    private static String sha(byte[] bytes) throws Exception {
        return java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }
    private static ClassNode parse(byte[] bytes) {
        ClassNode node = new ClassNode(Opcodes.ASM9); new ClassReader(bytes).accept(node, 0); return node;
    }
    private static byte[] write(ClassNode node) {
        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS); node.accept(writer); return writer.toByteArray();
    }
    private static int renameExact(ClassNode node, String oldName, String newName) {
        if (!CLASS.equals(node.name)) throw new IllegalStateException("Unexpected internal class name.");
        int count = 0;
        for (MethodNode method : node.methods) for (AbstractInsnNode instruction : method.instructions) {
            if (!(instruction instanceof MethodInsnNode call) || !OWNER.equals(call.owner) || !oldName.equals(call.name) || !CALL_DESC.equals(call.desc)) continue;
            if (!CALLER.equals(method.name) || !CALLER_DESC.equals(method.desc) || call.getOpcode() != Opcodes.INVOKEVIRTUAL || call.itf)
                throw new IllegalStateException("Unexpected caller or invoke opcode.");
            call.name = newName; count++;
        }
        if (count != 1) throw new IllegalStateException("Expected exactly one guarded call site, found " + count);
        return count;
    }
    private static byte[] prepare(byte[] original) throws Exception {
        if (!ORIGINAL_SHA.equals(sha(original))) throw new IllegalStateException("Original MenuRegistry class SHA256 differs.");
        ClassNode node = parse(original); renameExact(node, "build", "buildUnregistered"); return write(node);
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("Usage: <exact original class> <output directory>");
        byte[] original = Files.readAllBytes(Path.of(args[0]));
        Path output = Path.of(args[1]); Files.createDirectories(output);
        byte[] prepared = prepare(original);
        byte[] tampered = original.clone(); tampered[tampered.length - 1] ^= 1;
        boolean refused = false;
        try { prepare(tampered); } catch (IllegalStateException expected) { refused = expected.getMessage().contains("SHA256"); }
        if (!refused) throw new IllegalStateException("Tampered input was not refused before parsing.");

        if (!"ed983f7bb0881933783b37aa1877b53631e6b960fe873f23437ea08610ea178f".equals(sha(prepared))) throw new IllegalStateException("Prepared class differs from the approved reference output.");
        ClassNode reversed = parse(prepared); renameExact(reversed, "buildUnregistered", "build");
        if (!Arrays.equals(write(parse(original)), write(reversed)))
            throw new IllegalStateException("Class semantic structure differs beyond the one invoked method name.");
        Files.write(output.resolve("MenuRegistry.prepared.class"), prepared);
        String report = "{\n  \"originalClassSha256\":\"" + sha(original) + "\",\n  \"preparedClassSha256\":\"" + sha(prepared) + "\",\n  \"exactCallSites\":1,\n  \"matchesApproved417OutputHash\":true,\n  \"reverseOnlyInvokeRenameCanonicalByteIdentical\":true,\n  \"noRuntimeTransformerRequired\":true,\n  \"tamperedInputRejectedBeforeParse\":true,\n  \"nativeEventOrFullClientRun\":false\n}\n";
        Files.writeString(output.resolve("class-preparation-proof.json"), report);
        System.out.println("EXACT_MENU_PREP original=" + sha(original) + " prepared=" + sha(prepared) + " approvedReferenceHash=true sites=1");
    }
}
