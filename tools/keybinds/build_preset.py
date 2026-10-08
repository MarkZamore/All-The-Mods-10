#!/usr/bin/env python3
"""Writes launcher/controls-preset.txt from the layout below and the key registry.

Every mapping registered.tsv knows gets a line: the key the layout gives it, or
key.keyboard.unknown with the key it used to sit on remembered in a comment.
"""
from __future__ import annotations
import csv, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
K = "key.keyboard."
M = "key.mouse."

# Vanilla stays where Minecraft puts it, except these four.
VANILLA_FREED = {
    "key.saveToolbarActivator": "creative only, and it frees C",
    "key.loadToolbarActivator": "creative only, and it frees X",
    "key.socialInteractions": "frees P; the same screen opens from the pause menu",
    "options.narrator": "Ctrl+B turning the narrator on by accident is the whole complaint",
}

LAYOUT = {
    # --- letters: the hand is on WASD, so the nearest ones do the most ---
    "key.sophisticatedbackpacks.open_backpack": K + "b",
    "key.ars_nouveau.open_book": K + "c",
    "key.enderio.travel_staff": K + "g",
    "pneumaticcraft.helmet.hack": K + "h",
    "key.aether.open_accessories.desc": K + "i",
    "key.irons_spellbooks.spell_wheel": K + "j",
    "iris.keybind.toggleShaders": K + "k",
    "key.journeymap.map_toggle_alt": K + "m",
    "key.occultism.storage_remote": K + "n",
    "iris.keybind.shaderPackSelection": K + "o",
    "keybind.ironjetpacks.hover": K + "p",
    "key.jei.showRecipe": K + "r",
    "key.jei.showUses": K + "u",
    "key.irons_spellbooks.spellbook_cast": K + "v",
    "key.dragon_fireAttack": K + "x",
    "key.jei.bookmark": K + "y",
    "key.dragon_down": K + "z",

    # --- current player layout, imported from the launcher instance ---
    "key.crystalix.wand_config": K + "v",
    "key.draconicevolution.tool_modules": K + "c:SHIFT",
    "key.relics.research_relic": K + "left.shift",

    # --- punctuation ---
    "key.ftbultimine": K + "grave.accent",
    "key.mekanism.module_tweaker": K + "backslash",
    "key.sophisticatedcore.transfer_to_storage": K + "left.bracket",
    "key.sophisticatedcore.transfer_to_inventory": K + "right.bracket",
    "key.dragon_strike": K + "semicolon",
    "keybind.ironjetpacks.decrement_throttle": K + "comma",
    "keybind.ironjetpacks.increment_throttle": K + "period",
    "key.journeymap.zoom_out": K + "minus",
    "key.journeymap.zoom_in": K + "equal",
    "key.deeperdarker.boost": K + "0",

    # --- function row ---
    "key.draconicevolution.tool_config": K + "f4",
    "key.buildinggadgets2.settings_menu": K + "f6",
    "key.moreoverlays.lightoverlay.desc": K + "f7",
    "keybind.ironjetpacks.engine": K + "f8",
    "key.moreoverlays.chunkbounds.desc": K + "f9",
    "key.railcraft.loco.mode": K + "f10",
    "key.utilityvest.radial": K + "f12",

    # --- navigation cluster ---
    "key.apotheosis.toggle_radial_mining": K + "insert",
    "key.modern_industrialization.toggle_flight": K + "home",
    "key.mekanism.mode": K + "end",
    "key.jei.previousRecipePage": K + "page.up",
    "key.jei.nextRecipePage": K + "page.down",
    "key.buildinggadgets2.undo": K + "backspace",
    "key.structurize.place": K + "enter",
    "key.cataclysm.ability": K + "scroll.lock",
    "key.evilcraft.exaltedCrafting": K + "pause",

    # --- arrows ---
    "ftbultimine.change_shape.next": K + "up",
    "key.railcraft.loco.slower": K + "left",
    "key.railcraft.loco.faster": K + "right",
    "key.dragon_change_view": K + "down",

    # --- keys the hand already holds ---
    "create.keyinfo.shift_modifier": K + "right.shift",
    "create.keyinfo.ctrl_modifier": K + "right.control",
    "create.keyinfo.alt_modifier": K + "right.alt",
    "create.keyinfo.toolbelt": K + "caps.lock",
    "create.keyinfo.toolmenu": K + "menu",
    "key.relics.active_abilities_list": M + "4",
    "key.neovitae.blood_shield": M + "5",

    # --- held in screens, and on keys Minecraft itself never uses ---
    #
    # The scanner reads a mapping's conflict context out of the bytecode where
    # the class gives it away, and calls the rest UNIVERSAL, which is the
    # strictest thing it can assume. All four of these are built under a name
    # the bytecode never spells - assembled at runtime - so nothing can be read
    # about them at all, and none of them may sit on a key vanilla owns.
    # Left Alt, the apostrophe and F1 are keys the game itself has no use for,
    # so UNIVERSAL there costs nothing; Delete is TrashSlot's own default.
    "key.jade.show_details": K + "left.alt",
    "key.apotheosis.compare_equipment": K + "apostrophe",
    "key.trashslot.delete": K + "delete",
    "key.ftbquests.gui.extended_info": K + "f1",
}

def main() -> int:
    rows = list(csv.DictReader((HERE / "registered-keys.tsv").open(encoding="utf-8"), delimiter="\t"))
    known = {r["name"]: r for r in rows}
    for name in LAYOUT:
        if name not in known:
            print(f"layout names a mapping the registry does not know: {name}")
            return 1

    by_mod = collections.defaultdict(list)
    for r in rows:
        by_mod[r["mod"] or "minecraft"].append(r)

    out = [
        "# All The Mods 10 controls preset - the current player layout.",
        "#",
        "# Applied by the launcher's \"Пресет настроек управления\" button into the",
        "# instance's options.txt (one line per mapping, options.txt syntax). Blank",
        "# lines and # comments are ours; the game never sees this file. Every mapping",
        "# the pack registers is listed, bound or not, so tools/keybinds/check_preset.py",
        "# checks the complete layout and its explicitly documented conflict exceptions.",
        "# Read tools/keybinds/design.md before changing a key.",
    ]
    for mod in sorted(by_mod, key=lambda m: (m != "minecraft", m)):
        out.append("")
        out.append(f"# --- {'Minecraft' if mod == 'minecraft' else mod} ---")
        for r in sorted(by_mod[mod], key=lambda r: r["name"]):
            name, live = r["name"], r["live"]
            if name in LAYOUT:
                value = LAYOUT[name]
                note = ""
                if live and live != value and live != "key.keyboard.unknown":
                    note = f"  # was {live.replace(K, '').replace(M, 'mouse ')}"
            elif name in VANILLA_FREED:
                value, note = "key.keyboard.unknown", f"  # unbound: {VANILLA_FREED[name]}"
            elif name.startswith("key.") and mod == "minecraft":
                value, note = live or "key.keyboard.unknown", ""
            else:
                value = "key.keyboard.unknown"
                note = f"  # unbound: was {live.replace(K, '').replace(M, 'mouse ')}" \
                    if live and live != "key.keyboard.unknown" else "  # unbound"
            out.append(f"key_{name}:{value}{note}")

    (REPO / "launcher" / "controls-preset.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} mappings, {len(LAYOUT)} of them bound by the layout")
    return 0

raise SystemExit(main())
