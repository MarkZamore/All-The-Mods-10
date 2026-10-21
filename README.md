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


## Launcher library

`library/content.json` owns the player-facing description, stable identity, additional library IDs and curated addon relationships; `library/preview.jpg` is the original menu background resized for cards and the detail banner. `tools/pack_library.py` reads the actual shipped jars and builds a deterministic, content-addressed library bundle. The optional `library` field of `pack-manifest.json` names its size, SHA-256 and revision. It is published before the manifest, separately from installed game files, and ignored by older launchers.
