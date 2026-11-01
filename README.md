# ATM10

All the Mods 10, version 8.4, for Minecraft 1.21.1 on NeoForge 21.1.265, laid
out as a portable pack the LANMinecraft launcher can install and update.

The tree is prepared from official CurseForge client file `9366926`,
`All-the-Mods-10-8.4.zip`, SHA256
`e6ac21055562b08cbad4ed65438e97954d28c2216dde7a084a7a2f9e5795aac4`.
All 499 exact project/file references were downloaded and checked; the bundled
CC: Tweaked JAR is taken unchanged from the archive's overrides. After retaining
the five existing service-mod exclusions below, this distribution contains
490 unchanged author JARs, four shader packs and the Neo Vitae Bloodborn
resource pack. Its resource ZIP belongs under `resourcepacks/`, not
`shaderpacks/`. The author's `datapacks/sawmill.zip` is included too.
`portable-pack.json` is what
the launcher reads; a push to `main` regenerates `pack-manifest.json` and
refreshes the rolling `pack-latest` release the launcher syncs from.

The launcher controls preset, Russian starting language and local presentation
settings are retained. The language seed applies only when the player has no
language setting yet. Quest definitions are replaced on update; completed
tasks and rewards remain in each world's own data. Existing-world conversion
has not been tested for this update.

The 8.4 preset covers 567 measured native Options mappings and four verified
language-dependent Ad Astra names. All 90 previous assignments are preserved;
25 newly measured actions are unbound, and four retired/unpersisted unbound
entries are removed. The six existing accepted overlaps remain documented.
Custom conflict contexts use a conservative model, not a complete native
pair-by-pair test. Applying the preset remains an explicit player action.

The upstream release includes Trash Cans 1.1.2. Crash Assistant, NeoAuth,
CrashUtilities, Observable and Spark remain
excluded from this portable build.

Credit for the pack itself belongs to the All the Mods team, and to the author
of every mod in `mods/`.

## Author JARs and pack-owned logging

AdvancedAE `1.6.12-1.21.1`, including its nested ae2addonlib, is the unchanged
author JAR with SHA256
`a01d9718667ac13899013e91c5b0b7708b9b9db1da9b8e380772dde54bbe8f41`.
The earlier one-call menu-registration derivative has been removed at the
user's request; its active preparation and publication hook have also been
removed. The launcher no longer applies that content rewrite. The need for
such a correction was checked on the complete 8.4 client: three stable native
title-menu observations passed with the original JAR. It remains removed;
individual AdvancedAE screens and existing worlds were not tested.

`tools/upstream/current.json` records exact selected author-file hashes and
keeps exclusions outside the active file list. `tools/upstream/verify.py`
rejects changed, missing or extra game JARs and checks the selected platform.
This static verification is separate from a complete client or world test.
The full client reported 534 loaded IDs, including Minecraft, NeoForge and the
shared Steam component. Library entries and the launcher's JAR-based memory
estimate count different sets; they are not presented as that native count.

Both official CC: Tweaked JARs (1.113.1 and 1.120.2) remain unchanged, as in the
author archive. NeoForge selected 1.120.2 in the native client. The exact-hash
`library/content.json:modSourceSelections` entry makes the library display that
selected version; it neither changes the loader's choice nor removes a file.

Exact old/new artifact provenance and the bounded native protection review are
recorded in [8.3-to-8.4-impact.md](tools/upstream/8.3-to-8.4-impact.md).
The [native runtime report](tools/upstream/runtime-8.4-report.md) records the
successful title/quit observations and all 248 remaining ERROR events, including
their exact author-resource origins and the offline/closed-Steam limitations.

`config/log4j2.xml` and the pack-owned `launcher/jvm-args.txt` now supply the
existing logging policy. The native Log4j/loader parser was checked separately;
the launcher no longer needs to recreate this configuration on launch.

## Native client compatibility policies

The official [ATM10 8.4 known issues](https://www.curseforge.com/minecraft/modpacks/all-the-mods-10/files/9366926)
recommend disabling ImmediatelyFast `hud_batching` for the Draconic Evolution HUD.
The pack-owned `kubejs/client_scripts/lanmc_draconic_hud_compat.js` sets only that
option in ImmediatelyFast's loaded configuration and runtime configuration.
The original 3D Draconic HUD, shaders and visual effects stay enabled. This uses
ordinary HUD submission; it can require more HUD draw calls than batching.
The player's `config/immediatelyfast.json` and its other options are preserved.

`lanmc_memory_warning_policy.js` sets only the loaded Memory Settings
`disableWarnings` option before its first game-menu check. It suppresses the
upper-memory panel when the launcher-selected heap exceeds the author's 32000 MB
recommendation, without imposing a heap limit or rewriting `memorysettings.json`.
The earlier native low-heap Swing warning and constructor log are outside this
client-stage policy. The author JSON deliberately retains its original `false`.

`tools/client-policy/prepare.py --pack . --apply` restores only these two missing
owned scripts after an author import. It refuses conflicting source scripts and
validates their native public mutable fields against the actual author JARs.
The CI workflow runs it before packing. Later author versions with the same
public API continue to work; an API change requires review instead of silently
shipping a broken script. Keep this source-only tool and its templates when
importing a later author version. See [client-policy/README.md](tools/client-policy/README.md).

The exact current native APIs, real Rhino script execution, preservation of
unrelated native options and unchanged personal JSON bytes were checked offline.
No new in-game or visual check was run for this update, as requested.

## Russian questbook and later author updates

FTB Quests selects Russian only when Minecraft uses `ru_ru`; other selected
languages retain their own text and native English fallback. For 8.4, all
9222 current English keys and 39 older image captions have been reviewed.
The single managed Russian table contains the author translations plus
2336 manually translated fallback entries. Mod and music-track proper names
have explicit preservation decisions.

`tools/quest-translations/` owns the source-only preparation, provenance and
update tests. Fresh author Russian takes precedence over manual fallback.
Fallback is applied only to the exact reviewed English value. Changed or new
English without a matching translation creates a review queue and keeps native
English; it does not block a later pack update. The publication workflow uses
no fixed version/key-count gate. The current complete-coverage check was run
separately for this prepared 8.4 release.

Eight chapter files change only 38 image-hover display fields, with exact
native AST preservation of every quest/task/reward/dependency and other field.
The corresponding English text and every other locale are preserved. Actual
FTB Quests 2101.1.37 and Library 2101.1.39 parsers verified the generated data;
standalone parser results are separate from client/world tests. See
`tools/quest-translations/README.md` for the fresh-author import command and
ownership/retry rules. These tools do not run in the game or launcher.


## Launcher library

`library/content.json` owns the player-facing description, stable identity, additional library IDs and curated addon relationships; `library/preview.jpg` is the original menu background resized for cards and the detail banner. `tools/pack_library.py` reads the actual shipped jars and builds a deterministic, content-addressed library bundle. The optional `library` field of `pack-manifest.json` names its size, SHA-256 and revision. It is published before the manifest, separately from installed game files, and ignored by older launchers.

`library/mod-pages.json` preserves the reviewed official project page for every
declared library entry, including the official AdvancedAE project. Missing links
fail generation. Explicitly unavailable
author URLs retain their provenance and remain non-clickable in the launcher.
