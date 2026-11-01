import com.google.gson.*;
import com.memorysettings.config.CommonConfiguration;
import dev.latvian.mods.rhino.*;
import net.neoforged.fml.loading.FMLPaths;
import net.raphimc.immediatelyfast.ImmediatelyFast;
import net.raphimc.immediatelyfast.feature.core.ImmediatelyFastConfig;
import net.raphimc.immediatelyfast.feature.core.ImmediatelyFastRuntimeConfig;
import java.nio.file.*;
import java.util.*;

// Source-only standalone native API/Rhino probe. Never loaded by a game.
public class NativePolicyProbe {
  static Context cx;
  static Scriptable scope;
  static final Gson GSON = new Gson();
  public static class JavaBinding {
    public Object loadClass(String name) throws Exception {
      if (!Set.of("net.raphimc.immediatelyfast.ImmediatelyFast", "com.memorysettings.config.CommonConfiguration").contains(name)) throw new AssertionError(name);
      return new NativeJavaClass(cx, scope, Class.forName(name));
    }
  }
  static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
  static JsonObject snapshot(Object value) { return GSON.toJsonTree(value).getAsJsonObject(); }
  static Set<String> changed(JsonObject before, JsonObject after) {
    check(before.keySet().equals(after.keySet()), "Native field set changed");
    var out = new TreeSet<String>();
    for (var key : before.keySet()) if (!before.get(key).equals(after.get(key))) out.add(key);
    return out;
  }
  static void eval(Path path) throws Exception { cx.evaluateString(scope, Files.readString(path), path.getFileName().toString(), 1, null); }
  public static void main(String[] args) throws Exception {
    Path here = Path.of(args[0]).toAbsolutePath();
    Path fixture = Path.of("").toAbsolutePath();
    check(!Files.exists(fixture.resolve("mods")) && !Files.exists(fixture.resolve("portable-pack.json")), "Use a fresh separate fixture directory");
    Files.createDirectories(fixture.resolve("config"));
    check(!Files.exists(fixture.resolve("config/memorysettings.json")) && !Files.exists(fixture.resolve("config/immediatelyfast.json")), "Fixture already has config files");
    Files.copy(here.resolve("config/memorysettings.json"), fixture.resolve("config/memorysettings.json"));
    Files.writeString(fixture.resolve("config/immediatelyfast.json"), "{\"hud_batching\":true,\"synthetic_personal\":17}\n");
    FMLPaths.loadAbsolutePaths(Path.of("").toAbsolutePath());
    var memory = CommonConfiguration.config.getCommonConfig();
    memory.maximumClient = 98765; memory.minimumClient = 7654; memory.warningTolerance = 57;
    memory.howtolink = "https://example.invalid/synthetic-personal-choice";
    memory.disableWarnings = false;
    var config = new ImmediatelyFastConfig();
    config.hud_batching = true; config.font_atlas_resizing = false; config.fast_buffer_upload = false;
    config.experimental_screen_batching = true;
    ImmediatelyFast.config = config;
    ImmediatelyFast.runtimeConfig = new ImmediatelyFastRuntimeConfig(config);
    Path file = Path.of("config/memorysettings.json");
    byte[] originalBytes = Files.readAllBytes(file);
    byte[] personalIf = Files.readAllBytes(Path.of("config/immediatelyfast.json"));
    var beforeMemory = memory.serialize(); var beforeIf = snapshot(config); var beforeRuntime = snapshot(ImmediatelyFast.runtimeConfig);
    cx = new ContextFactory().enter(); scope = cx.initStandardObjects();
    ScriptableObject.putProperty(scope, "Java", cx.javaToJS(new JavaBinding(), scope), cx);
    eval(here.resolve("kubejs/client_scripts/lanmc_draconic_hud_compat.js"));
    eval(here.resolve("kubejs/client_scripts/lanmc_memory_warning_policy.js"));
    check(changed(beforeMemory, memory.serialize()).equals(Set.of("disableWarnings")), "Memory policy changed unrelated fields");
    check(changed(beforeIf, snapshot(config)).equals(Set.of("hud_batching")), "IF source policy changed unrelated fields");
    check(changed(beforeRuntime, snapshot(ImmediatelyFast.runtimeConfig)).equals(Set.of("hud_batching")), "IF runtime policy changed unrelated fields");
    check(!ImmediatelyFast.config.hud_batching && !ImmediatelyFast.runtimeConfig.hud_batching && memory.disableWarnings, "Native values incorrect");
    check(Arrays.equals(originalBytes, Files.readAllBytes(file)), "Personal memory JSON was rewritten");
    var once = snapshot(config); var memoryOnce = memory.serialize();
    ImmediatelyFast.createRuntimeConfig();
    check(!ImmediatelyFast.runtimeConfig.hud_batching, "Native runtime recreation lost policy");
    eval(here.resolve("kubejs/client_scripts/lanmc_draconic_hud_compat.js"));
    eval(here.resolve("kubejs/client_scripts/lanmc_memory_warning_policy.js"));
    check(once.equals(snapshot(config)) && memoryOnce.equals(memory.serialize()), "Repeated script execution changed values");
    check(Arrays.equals(originalBytes, Files.readAllBytes(file)), "Repeated script wrote personal file");
    check(Arrays.equals(personalIf, Files.readAllBytes(Path.of("config/immediatelyfast.json"))), "Personal IF file was rewritten");
    System.out.println("{\"status\":\"PASS\",\"actualNativeRhino\":true,\"nativeImmediatelyFastConfigAndRuntimeChangedOnlyHudBatching\":true,\"nativeMemoryConfigChangedOnlyDisableWarnings\":true,\"personalMemoryFileBytesUnchanged\":true,\"runtimeRecreationRetainsPolicy\":true,\"idempotent\":true,\"limit\":\"Standalone actual API and Rhino; lifecycle bytecode separately reviewed; no game/visual test\"}");
  }
}
