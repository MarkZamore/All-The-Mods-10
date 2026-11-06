# Official Minecraft client delivery QA

This runner uses the launcher's normal pack sync, instance preparation and
runtime preparation APIs. Pack HTTP requests use staged local release assets.
Runtime preparation uses the real upstream servers and an empty installation.
The game and personal worlds are not opened.

Prepare one owned run directory with `RUN.json` under
`artifacts/agent-runs/`. Generate and verify `dist` using
`tools/generate_manifest.py` from the candidate source. An existing verified
installation can supply the payload files for staging. Check the SHA256 and
size of each file against the original manifest before copying it. Use the
candidate descriptor and the source repository's library and policy inputs.
The expected payload change is the new descriptor and the removal of the old
client JAR.

For `legacy.json`, use the previous release manifest and the candidate's
asset rows for unchanged files. Replace the candidate descriptor asset row
with the previous descriptor and client asset rows. In `dist/assets`, add
those two verified files from the previous local installation under their
original asset names. This reconstructs the previous managed file set without
downloading another full pack or publishing a copy of Mojang's JAR.

From the pack repository, with absolute paths to the launcher source and run
directory:

```powershell
dotnet build tools/qa/official-client/OfficialClientQa.csproj --artifacts-path "$run/dotnet" "-p:LauncherProject=$launcher/Program/Minecraft.csproj" -p:SkipPortableIdentityAdapter=true
dotnet "$run/dotnet/bin/OfficialClientQa/debug_win-x64/OfficialClientQa.dll" $run
```

The runner verifies the official Minecraft 1.21.1 client SHA-1, the NeoForge
profile, removal of the managed root JAR after the upgrade, retention of
synthetic options/world markers, and reuse of the shared client. It interrupts
the descriptor transfer after one byte and checks that the old installation
survives before retrying. `--migration-only` repeats just the upgrade checks
using the same completed clean runtime fixture. It requires the clean-runtime
PASS in the existing report.

Keep the compact report and delete the restored payload, staging assets,
runtime and build intermediates after verification.

## Acceptance on 2026-11-06

Launcher APIs at `34e2a0b` prepared a clean Windows runtime for Minecraft
1.21.1 / NeoForge 21.1.265. The installer downloaded the Mojang client into
the empty shared cache. SHA-1 was `30c73b1c5da787909b2f73340419fdf13b9def88`
and SHA256 was `499f6897d1837516680f3114072d8106e11c9adcd933fe5cf051b551089b0c99`.
The published launcher revision `af18e8e` retains that NeoForge installer path.

The staged candidate verified all 230 payload assets and matched all 4,286
unchanged paths from the previous release `70c6cf0` by size and SHA256.
The clean install, managed update, interrupted descriptor transfer, retry,
synthetic data preservation and shared client reuse passed. All 27 pack-tool
tests passed. This is installation QA, without a game-menu or world run.
