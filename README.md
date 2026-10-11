# ATM10

All the Mods 10, version 8.0, for Minecraft 1.21.1 on NeoForge 21.1.247, laid
out as a portable pack the LANMinecraft launcher can install and update.

The tree is built from the two archives CurseForge publishes for release 8.0:
the server files supply the 455 jars that both sides share, and the client
manifest names the 31 that only a client needs. `portable-pack.json` is what
the launcher reads; a push to `main` regenerates `pack-manifest.json` and
refreshes the rolling `pack-latest` release the launcher syncs from.

This portable edition also includes [Starfall Bow 1.0.0](https://www.curseforge.com/minecraft/mc-mods/starfall-bow/files/9019718)
for NeoForge 1.21.1. The mod is shipped to both clients and servers.

Credit for the pack itself belongs to the All the Mods team, and to the author
of every mod in `mods/`.
