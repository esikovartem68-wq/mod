#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка общего мода ArcanaForge из содержимого папки `мод/` + bbmodels.
Builds ONE jar containing:
  1. ForgottenArcana 1.1.0 (full mod: code + assets + data)
  2. WeaponForge 1.0.0 (full mod: code + assets + data)
  3. Bonus content in the `arcanaforge` namespace:
     - magic_wand, ghost_knight_hat, ancient_golem_figurine (converted BBModels)
     - CustomModelData overrides on existing ForgottenArcana items
     - 3 advancements + lang (ru/en)
Forge loads several [[mods]] sections from one jar as separate mod containers,
so a single file delivers both mods. No code changes: pure merge + resources.

Usage:  python3 tools/build_bundle.py
Output: ArcanaForge-1.20.1-v1.0.0.jar  (in repo root)
"""
import base64
import io
import json
import os
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_FA = os.path.join(REPO, "ForgottenArcana-1.20.1-v1.1.0.jar")
SRC_WF = os.path.join(REPO, "мод", "weaponforge-1.0.0 (1).jar")
BB_DIR = os.path.join(REPO, "мод")
OUT_JAR = os.path.join(REPO, "ArcanaForge-1.20.1-v1.0.0.jar")

BUNDLE_VERSION = "1.0.0"
BUILD_STAMP = "2026-09-18T00:00:00+0000"
ZIP_DATE = (2026, 9, 18, 0, 0, 0)

SKIP_META = {"META-INF/MANIFEST.MF", "META-INF/mods.toml", "pack.mcmeta"}

# bbmodel file -> (model name, texture file, normalize_to_height or None)
BONUS = [
    ("magic_wand (1).bbmodel", "magic_wand", None),
    ("ghost_knight_mage_hat.bbmodel", "ghost_knight_hat", None),
    ("Ancient_Golem.bbmodel", "ancient_golem_figurine", 14.0),
]

# (FA item model to patch, custom_model_data, bonus model)
OVERRIDES = [
    ("assets/forgottenarcana/models/item/staff_sparks.json", 101, "arcanaforge:item/magic_wand"),
    ("assets/forgottenarcana/models/item/boss_seal.json", 102, "arcanaforge:item/ghost_knight_hat"),
    ("assets/forgottenarcana/models/item/rune_golem_spawn_egg.json", 103, "arcanaforge:item/ancient_golem_figurine"),
]

DISPLAY_SLOTS = (
    "thirdperson_righthand", "thirdperson_lefthand",
    "firstperson_righthand", "firstperson_lefthand",
    "gui", "head", "ground", "fixed",
)


def load_bbmodel(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def extract_texture_png(bb):
    """Return raw PNG bytes of the (single) embedded texture."""
    assert len(bb.get("textures", [])) == 1, "expected exactly 1 embedded texture"
    src = bb["textures"][0]["source"]
    assert src.startswith("data:image/png;base64,"), "texture is not an embedded PNG"
    raw = base64.b64decode(src.split(",", 1)[1])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    return raw


def bb_to_vanilla(bb, texture_path, normalize_height=None, label=""):
    """Convert a Blockbench java_block/free model to a vanilla item model dict."""
    els = bb["elements"]
    norm = None
    if normalize_height is not None:
        mins = [1e9] * 3
        maxs = [-1e9] * 3
        for e in els:
            for i in range(3):
                mins[i] = min(mins[i], e["from"][i])
                maxs[i] = max(maxs[i], e["to"][i])
        size = [maxs[i] - mins[i] for i in range(3)]
        s = normalize_height / max(size)
        # center X/Z on 8, feet (min Y) on 0
        t = [
            8.0 - (mins[0] + maxs[0]) / 2.0 * s,
            -mins[1] * s,
            8.0 - (mins[2] + maxs[2]) / 2.0 * s,
        ]
        norm = (s, t)
        print(f"  [{label}] normalize: scale={s:.5f} translate={[round(v, 3) for v in t]}")

    def xform(p):
        if norm is None:
            return [round(v, 4) for v in p]
        s, t = norm
        return [round(p[i] * s + t[i], 4) for i in range(3)]

    out_elements = []
    for e in els:
        el = {"from": xform(e["from"]), "to": xform(e["to"])}
        rot = e.get("rotation") or [0, 0, 0]
        nz = [(i, v) for i, v in enumerate(rot) if abs(v) > 1e-9]
        assert len(nz) <= 1, f"multi-axis rotation in {label}/{e.get('name')}: {rot}"
        if nz:
            i, v = nz[0]
            snapped = round(v / 22.5) * 22.5
            snapped = max(-45.0, min(45.0, snapped))
            if abs(snapped - v) > 1e-9:
                print(f"  [{label}] snap rotation {e.get('name')}: {v} -> {snapped}")
            if abs(snapped) > 1e-9:
                el["rotation"] = {
                    "angle": snapped,
                    "axis": ("x", "y", "z")[i],
                    "origin": xform(e["origin"]),
                }
        faces = {}
        for direction, fc in e["faces"].items():
            if fc.get("enabled") is False:
                continue
            if fc.get("texture") is None:
                continue
            f = {"uv": [float(v) for v in fc["uv"]], "texture": "#0"}
            if fc.get("rotation"):
                f["rotation"] = fc["rotation"]
            faces[direction] = f
        assert faces, f"element without faces: {label}/{e.get('name')}"
        el["faces"] = faces
        out_elements.append(el)

    model = {
        "credit": "Made with Blockbench, bundled by ArcanaForge",
        "textures": {"0": texture_path, "particle": texture_path},
        "elements": out_elements,
    }
    disp_src = bb.get("display") or {}
    disp = {k: disp_src[k] for k in DISPLAY_SLOTS if k in disp_src}
    if disp:
        model["display"] = disp
    return model


def validate_model(model, png_bytes, label):
    """Validate vanilla model constraints (1.20.1): coords, rotations, UVs."""
    from PIL import Image
    tex = Image.open(io.BytesIO(png_bytes))
    tw, th = tex.size
    n_el = 0
    for e in model["elements"]:
        n_el += 1
        for v in e["from"] + e["to"]:
            assert -16.0 <= v <= 32.0, f"{label}: coord out of range: {v}"
        for a, b in zip(e["from"], e["to"]):
            assert b - a > 0, f"{label}: inverted box"
        if "rotation" in e:
            r = e["rotation"]
            assert r["axis"] in ("x", "y", "z")
            assert abs(r["angle"]) <= 45.0 and abs(r["angle"] / 22.5 - round(r["angle"] / 22.5)) < 1e-6
        for d, fc in e["faces"].items():
            uv = fc["uv"]
            assert 0.0 <= min(uv) and max(uv) <= max(tw, th), f"{label}: uv out of bounds: {uv}"
            assert fc["texture"] == "#0"
    assert n_el > 0
    print(f"  [{label}] OK: {n_el} elements, texture {tw}x{th}")


LANG = {
    "en_us": {
        "advancement.arcanaforge.magic_wand.title": "Wand of the Archmage",
        "advancement.arcanaforge.magic_wand.desc": "Get the crystal wand look for the Staff of Sparks (CustomModelData 101)",
        "advancement.arcanaforge.ghost_hat.title": "Helm of the Ghost Knight",
        "advancement.arcanaforge.ghost_hat.desc": "Get the ghost knight hat look for the King's Seal (CustomModelData 102)",
        "advancement.arcanaforge.golem_figurine.title": "Pocket Golem",
        "advancement.arcanaforge.golem_figurine.desc": "Get the Ancient Golem figurine look for the golem spawn egg (CustomModelData 103)",
    },
    "ru_ru": {
        "advancement.arcanaforge.magic_wand.title": "Жезл архимага",
        "advancement.arcanaforge.magic_wand.desc": "Получить кристальный жезл — облик Посоха искр (CustomModelData 101)",
        "advancement.arcanaforge.ghost_hat.title": "Шлем Рыцаря-Призрака",
        "advancement.arcanaforge.ghost_hat.desc": "Получить шляпу рыцаря-призрака — облик Печати Короля (CustomModelData 102)",
        "advancement.arcanaforge.golem_figurine.title": "Карманный голем",
        "advancement.arcanaforge.golem_figurine.desc": "Получить статуэтку Древнего Голема — облик яйца голема (CustomModelData 103)",
    },
}

ADVANCEMENTS = [
    ("magic_wand", "forgottenarcana:staff_sparks", 101),
    ("ghost_hat", "forgottenarcana:boss_seal", 102),
    ("golem_figurine", "forgottenarcana:rune_golem_spawn_egg", 103),
]


def advancement_json(name, item, cmd):
    return {
        "parent": "forgottenarcana:root",
        "display": {
            "icon": {"item": item, "nbt": "{CustomModelData:%d}" % cmd},
            "title": {"translate": "advancement.arcanaforge.%s.title" % name},
            "description": {"translate": "advancement.arcanaforge.%s.desc" % name},
            "frame": "task",
            "show_toast": True,
            "announce_to_chat": True,
            "hidden": False,
        },
        "criteria": {
            "has_it": {
                "trigger": "minecraft:inventory_changed",
                "conditions": {
                    "items": [{"items": [item], "nbt": "{CustomModelData:%d}" % cmd}]
                },
            }
        },
    }


MODS_TOML = """\
modLoader="javafml"
loaderVersion="[47,)"
license="Apache-2.0 AND MIT"

# ============================================================
# ArcanaForge bundle: ONE jar, TWO mods + bonus models.
# forgottenarcana (Apache-2.0) + weaponforge (MIT).
# See README.md and arcanaforge_bundle.json for details.
# ============================================================

[[mods]]
modId="forgottenarcana"
version="1.1.0"
displayName="Забытые Арканы | Forgotten Arcana"
authors="esikovartem, Arena Agent"
logoFile="logo.png"
description='''[ArcanaForge bundle] v1.1.0: 3D-модели (Blockbench / BBModel), новые текстуры, усиленная генерация мана-руды, рецепты для всех магических стрел и Скипетра Пустоты, новые достижения. Сердце Бездны теперь падает и с Рунного голема — путь к Забытому Королю больше не тупиковый.

[ArcanaForge bundle] v1.1.0: 3D BBModel models (Blockbench), new textures, stronger arcane ore generation, recipes for all magic bolts and the Void Scepter, new advancements. Heart of the Void now also drops from Rune Golems - the road to the Forgotten King is no longer a dead end.'''

[[mods]]
modId="weaponforge"
version="1.0.0"
displayName="Weapon Forge - Кузница стихий"
authors="Arena.ai Agent"
description='''[ArcanaForge bundle] 84 elemental weapons (14 types x 6 elements) with animated Blockbench models, unique key-combo abilities, rage ultimates and a top-left ability HUD.'''

[[dependencies.forgottenarcana]]
    modId="forge"
    mandatory=true
    versionRange="[47,)"
    ordering="NONE"
    side="BOTH"

[[dependencies.forgottenarcana]]
    modId="minecraft"
    mandatory=true
    versionRange="[1.20.1,1.21)"
    ordering="NONE"
    side="BOTH"

[[dependencies.weaponforge]]
    modId="forge"
    mandatory=true
    versionRange="[47,)"
    ordering="NONE"
    side="BOTH"

[[dependencies.weaponforge]]
    modId="minecraft"
    mandatory=true
    versionRange="[1.20.1,1.21)"
    ordering="NONE"
    side="BOTH"
"""

MANIFEST = (
    "Manifest-Version: 1.0\r\n"
    "Specification-Title: arcanaforge-bundle\r\n"
    "Specification-Vendor: Arena Agent\r\n"
    "Specification-Version: 1\r\n"
    "Implementation-Title: arcanaforge-bundle\r\n"
    "Implementation-Version: %s\r\n" % BUNDLE_VERSION
    + "Implementation-Vendor: Arena Agent\r\n"
    "Implementation-Timestamp: %s\r\n" % BUILD_STAMP
    + "\r\n"
)

PACK_MCMETA = {
    "pack": {
        "description": "ArcanaForge bundle: Forgotten Arcana + Weapon Forge",
        "pack_format": 15,
    }
}


def main():
    for p in (SRC_FA, SRC_WF):
        if not os.path.isfile(p):
            print(f"missing source: {p}")
            sys.exit(1)

    print("== 1. convert BBModels ==")
    bonus_files = {}  # arc path -> bytes
    for bb_file, name, norm_h in BONUS:
        print(f"converting {bb_file} -> {name} ...")
        bb = load_bbmodel(os.path.join(BB_DIR, bb_file))
        png = extract_texture_png(bb)
        model = bb_to_vanilla(bb, f"arcanaforge:item/{name}", norm_h, label=name)
        validate_model(model, png, name)
        bonus_files[f"assets/arcanaforge/models/item/{name}.json"] = (
            json.dumps(model, ensure_ascii=False, indent=2).encode("utf-8")
        )
        bonus_files[f"assets/arcanaforge/textures/item/{name}.png"] = png

    for lang, entries in LANG.items():
        bonus_files[f"assets/arcanaforge/lang/{lang}.json"] = (
            json.dumps(entries, ensure_ascii=False, indent=2).encode("utf-8")
        )
    for adv_name, item, cmd in ADVANCEMENTS:
        bonus_files[f"data/arcanaforge/advancements/{adv_name}.json"] = (
            json.dumps(advancement_json(adv_name, item, cmd), ensure_ascii=False, indent=2).encode("utf-8")
        )

    print("== 2. merge jars ==")
    merged = {}  # arc path -> (bytes, ZipInfo)
    for src, tag in ((SRC_FA, "FA"), (SRC_WF, "WF")):
        with zipfile.ZipFile(src, "r") as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                if info.filename in SKIP_META:
                    continue
                if info.filename in merged:
                    print(f"COLLISION on {info.filename} (from {tag}) — abort")
                    sys.exit(1)
                merged[info.filename] = z.read(info.filename)
        print(f"  {tag}: {src} merged")

    print("== 3. patch FA item models (overrides) ==")
    for arc_path, cmd, model_ref in OVERRIDES:
        if arc_path not in merged:
            print(f"missing {arc_path} — abort")
            sys.exit(1)
        data = json.loads(merged[arc_path].decode("utf-8"))
        data.setdefault("overrides", []).append(
            {"predicate": {"custom_model_data": cmd}, "model": model_ref}
        )
        merged[arc_path] = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        print(f"  {arc_path} + CustomModelData {cmd} -> {model_ref}")

    for arc_path, blob in bonus_files.items():
        assert arc_path not in merged, arc_path
        merged[arc_path] = blob

    merged["META-INF/mods.toml"] = MODS_TOML.encode("utf-8")
    merged["META-INF/MANIFEST.MF"] = MANIFEST.encode("utf-8")
    merged["pack.mcmeta"] = (json.dumps(PACK_MCMETA, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    bundle_info = {
        "bundle": "ArcanaForge",
        "bundle_version": BUNDLE_VERSION,
        "minecraft": "1.20.1",
        "forge": "47+",
        "mods": [
            {"modId": "forgottenarcana", "version": "1.1.0", "license": "Apache-2.0"},
            {"modId": "weaponforge", "version": "1.0.0", "license": "MIT"},
        ],
        "bonus_models": [
            {"name": n, "via": f"CustomModelData {c}", "on_item": m}
            for (m, c, _), (__, n, ___) in zip(OVERRIDES, BONUS)
        ],
        "built": BUILD_STAMP,
    }
    merged["arcanaforge_bundle.json"] = (
        json.dumps(bundle_info, ensure_ascii=False, indent=2).encode("utf-8")
    )

    print("== 4. write jar ==")
    with zipfile.ZipFile(OUT_JAR, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arc_path in sorted(merged):
            info = zipfile.ZipInfo(arc_path, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, merged[arc_path])
    size = os.path.getsize(OUT_JAR)
    print(f"wrote {OUT_JAR} ({size} bytes, {len(merged)} files)")

    print("== 5. verify ==")
    with zipfile.ZipFile(OUT_JAR, "r") as z:
        assert z.testzip() is None, "corrupt zip"
        names = set(z.namelist())
        # both mods' code present
        assert "ru/arena/forgottenarcana/ForgottenArcanaMod.class" in names
        assert "com/weaponforge/WeaponForge.class" in names
        # @Mod annotation targets intact (constant-pool markers)
        fa_cls = z.read("ru/arena/forgottenarcana/ForgottenArcanaMod.class")
        wf_cls = z.read("com/weaponforge/WeaponForge.class")
        assert b"forgottenarcana" in fa_cls, "FA mod id missing from mod class"
        assert b"weaponforge" in wf_cls, "WF mod id missing from mod class"
        assert b"Mod" in fa_cls and b"Mod" in wf_cls
        # mods.toml declares both mods
        toml = z.read("META-INF/mods.toml").decode("utf-8")
        assert toml.count("[[mods]]") == 2
        assert 'modId="forgottenarcana"' in toml and 'modId="weaponforge"' in toml
        # bonus content present
        for arc_path, blob in bonus_files.items():
            assert arc_path in names, arc_path
            if arc_path.endswith(".json"):
                json.loads(z.read(arc_path).decode("utf-8"))
        print("  all checks passed ✔")


if __name__ == "__main__":
    main()
