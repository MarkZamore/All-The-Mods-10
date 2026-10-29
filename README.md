# ATM10

All the Mods 10, version 8.3, for Minecraft 1.21.1 on NeoForge 21.1.259, laid
out as a portable pack the LANMinecraft launcher can install and update.

The tree is built from the two archives CurseForge publishes for release 8.3:
the server files supply the shared mods, and the client manifest supplies the
client mods and shader packs. `portable-pack.json` is what
the launcher reads; a push to `main` regenerates `pack-manifest.json` and
refreshes the rolling `pack-latest` release the launcher syncs from.

The launcher controls preset, Russian starting language and local presentation
settings are retained. Quest definitions are replaced on update; completed
tasks and rewards remain in each world's own data. Back up complete worlds
before their first launch on a new pack version, and restore that backup along
with the old pack if a rollback is needed.

The upstream 8.3 release includes Trash Cans 1.1.1, retaining the fix for the
confirmed crash when an accelerated export bus inserts a stack larger than 99
items. Crash Assistant, NeoAuth, CrashUtilities, Observable and Spark remain
excluded from this portable build.

Credit for the pack itself belongs to the All the Mods team, and to the author
of every mod in `mods/`.

## Pack-owned compatibility and logging

AdvancedAE remains version `1.6.12-1.21.1`, carrying ae2addonlib
`1.0.3-1.21.1`. The shipped outer JAR is a documented derivative of that exact
author release: SHA256 `a01d9718667ac13899013e91c5b0b7708b9b9db1da9b8e380772dde54bbe8f41`
becomes `e6de8c00a914106d5b343fafdcc14666cc0647c41bf571d8bea8ad3714455281`.
It changes one guarded call inside the nested `MenuRegistry` from
`MenuTypeBuilder.build` to `buildUnregistered`, preserving its existing deferred
registration. This is the same class byte sequence that launcher417 already
produced at runtime. The compatibility rule now belongs to the pack and does
not require a global content transformer in the launcher.

All other outer/nested JAR entries, resources, mod versions and registry IDs
are unchanged. No helper or new content mod is added. The change only selects
the existing menu-registration API; it introduces no new chunk, block,
inventory or delayed world-mutation path and needs no new Safety interception.
Exact source/result hashes, caller/opcode/count guards, upstream ASM licence
and reproducible preparation live in `tools/menu-compatibility/`.

The offline proof compares the prepared class with the actual immutable417
transformer output byte-for-byte and checks every unaffected ZIP entry. It
does not claim a new full ATM10 client/world or native event-order run. This
pack has no actual loaded-mod inventory to rebind: its existing manifest count
remains the declared top-level and nested JAR count.

`config/log4j2.xml` and the pack-owned `launcher/jvm-args.txt` now supply the
existing logging policy. The native Log4j/loader parser was checked separately;
the launcher no longer needs to recreate this configuration on launch.


## Launcher library

`library/content.json` owns the player-facing description, stable identity, additional library IDs and curated addon relationships; `library/preview.jpg` is the original menu background resized for cards and the detail banner. `tools/pack_library.py` reads the actual shipped jars and builds a deterministic, content-addressed library bundle. The optional `library` field of `pack-manifest.json` names its size, SHA-256 and revision. It is published before the manifest, separately from installed game files, and ignored by older launchers.

`library/mod-pages.json` preserves the reviewed official project page for every
declared library entry, including the unchanged author/project identity of the
AdvancedAE derivative. Missing links fail generation. Explicitly unavailable
author URLs retain their provenance and remain non-clickable in the launcher.
