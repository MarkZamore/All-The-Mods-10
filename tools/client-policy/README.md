# Pack-owned native client policies

The two runtime scripts are ordinary KubeJS client scripts. They run before the
initial game menu, independently of LANMinecraft's launch code. They use mutable
public configuration fields from the exact shipped native mods; no JAR is patched.

- `lanmc_draconic_hud_compat.js` sets only ImmediatelyFast `hud_batching=false` in
  its loaded configuration and runtime configuration. This is the official ATM10
  8.4 known-issue workaround. Draconic's 3D HUD and visual effects remain enabled;
  ordinary HUD submission may use more draw calls than batching.
- `lanmc_memory_warning_policy.js` sets only Memory Settings' loaded
  `disableWarnings=true` before its initial game-menu panel check. This prevents
  the upper-memory panel for a heap above the author's 32000 MB recommendation.
  It does not impose a heap limit. Its earlier low-heap Swing dialog and constructor
  warning log are outside this client-stage policy.

Neither script writes a personal JSON file or resets unrelated options. Both
original author config files remain unchanged; runtime policy can therefore differ
from the literal JSON value. A future game launch reapplies the pack's policy.

After importing a later author pack, keep this directory and run:

```text
python tools/client-policy/prepare.py --pack . --apply
```

The tool validates the actual JAR public fields/method used by these scripts,
restores a missing owned script from its hash-pinned template and refuses a
conflicting source file. It never writes a player config, downloads a mod or edits
an author JAR. Updated author JARs with the same native API remain supported;
changed or missing APIs need review. CI runs this before manifest generation.

The source tests check current native APIs, rejection of a missing member, missing
owned-script restoration, idempotence and preservation of foreign source/config
bytes. `native-proof.json` separately records actual Rhino evaluation against the
native current configs and reviewed loader ordering. The user waived a new game
run for this update, so no new in-game or visual result is claimed.

## Reproduce the standalone native check

`NativePolicyProbe.java` is source-only and takes the prepared pack root as its
single argument. Run Java 21+ with a classpath from the exact pack's native client
runtime plus its mod JARs, in a fresh separate empty working directory. For long
Windows classpaths use Java's standard `@arguments.txt` file. Include the current
Memory Settings/Cupboard, ImmediatelyFast and Rhino JARs, NeoForge's named client
and loader/libraries. Do not substitute mock configuration classes.

```text
java --class-path <EXACT_NATIVE_RUNTIME_AND_MOD_JARS> <PACK>/tools/client-policy/NativePolicyProbe.java <PACK>
```

The probe refuses a working directory containing a pack or existing fixture
config files. It copies only the author's memory-settings JSON into that fresh
fixture, initializes native FML config paths there, evaluates the two actual pack
scripts with real Rhino NativeJavaClass handling, and checks changed fields,
idempotence, native runtime recreation and both JSON files' byte preservation.
Its small `Java.loadClass` fixture binding delegates to actual native Rhino/Java
classes; it is not a substitute KubeJS lifecycle or renderer. Actual load order is
reviewed separately in `native-proof.json`. No private classpath, logs or paths
are committed.
