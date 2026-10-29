# Frozen ATM10 menu preparation

This preparation transfers the existing launcher417 menu-registration rewrite
into the exact AdvancedAE1.6.12 content JAR. It is a documented derivative, not
an official author update. No new runtime classes, helper JARs, assets, item IDs,
entity IDs or world-editing abilities are added.

`prepare.py` requires Python3 and JDK17+ and uses the included exact-hash ASM9.8
preparation dependencies. These dependencies stay under `tools/`, outside the
game's `mods/` classpath. `lib/LICENSE.asm.txt` is the upstream licence.

Run from this directory with an unmodified author JAR and a separate output:

```powershell
python ./prepare.py --source <originalAdvancedAEJAR> --jdk <JDK> --output <privateOutputDirectory>
```

The tool refuses to overwrite its source JAR. It requires these exact SHA256:

| Layer | Original | Prepared |
| --- | --- | --- |
| AdvancedAE1.6.12 outer JAR | `a01d9718667ac13899013e91c5b0b7708b9b9db1da9b8e380772dde54bbe8f41` | `e6de8c00a914106d5b343fafdcc14666cc0647c41bf571d8bea8ad3714455281` |
| nested ae2addonlib1.0.3 | `1d065b46db71addeb7e04aff4981b424531d40123fe2b0c1d2a2cc9af81319fe` | `2a625a378400ca553e353bf322aa99bbac59786eb4eae858a70d5c5e3e2b47b6` |
| MenuRegistry | `87e082cdc0e7738213f2ce26f6656e1655a479dcd546b58d40f368d51109b0a5` | `ed983f7bb0881933783b37aa1877b53631e6b960fe873f23437ea08610ea178f` |

The only guarded caller is `MenuRegistry.lambda$create$0`, descriptor
`(MenuTypeBuilder$MenuFactory, Class, String, String) -> MenuType`.
Exactly one `INVOKEVIRTUAL MenuTypeBuilder.build(ResourceLocation) -> MenuType`
becomes `buildUnregistered` with the same descriptor. The original deferred
registration, registry IDs and every other instruction remain unchanged.
Other ZIP contents, original compressed local records and metadata survive;
only replacement-entry CRC/sizes and directory offsets change.

`reference-proof.json` records the original one-time comparison against the
actual transformer embedded in published launcher417. The prepared class was
byte-identical to that transformer's output, and the old transformer left the
prepared class unchanged. Current preparation enforces that approved class hash
and the approved entire outer JAR hash without loading a launcher agent.

The output includes per-entry SHA256 provenance and call-site proof. It never
updates a source lock, library, release or active pack automatically. The owner
must integrate the prepared outer JAR with its new exact hash before removing
the old launcher runtime path. A native event-order or full client run is a
separate validation; these offline proofs do not claim it.

The publication workflow runs `verify_shipped.py --pack .` to verify the exact
outer, nested and class hashes before asset generation. A restored original or
another author version needs a reviewed preparation update and cannot silently
inherit this compatibility approval.
