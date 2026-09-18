#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the single-file ArcanaForge Nightwatch release for Forge 1.20.1.

This build deliberately has no Gradle/JDK requirement.  The repository contains
licensed, pre-built Forgotten Arcana and Weapon Forge artifacts, so the release
is made by reproducibly merging them and adding the supplied Blockbench pack.

What this build changes at runtime
----------------------------------
* Forgotten King / ``forgottenarcana:void_lich`` renders as Dark Ghost King.
  Its original combat, boss bar, altar summon and loot remain intact.
* Rune Golem renders as the Watcher.  A data-pack function calls one Watcher
  with three Eyebats on the second Minecraft night (37,000 ticks after a new
  world starts).  These particular summoned creatures are stationary, face the
  player and are persistent: they only watch.  Eyebats are the re-skinned
  Arcane Wisp and therefore keep the existing wisp mechanics when spawned
  normally.
* Every supplied BBModel, animation, texture and generator source is retained
  in the final JAR at ``assets/arcanaforge/blockbench/``.  All six staffs and
  ten creature models also receive static 3D catalogue/figurine item looks
  through CustomModelData; this makes every model accessible in-game even
  though Forge 1.20.1's vanilla entity renderer cannot play Bedrock animations
  directly.

Minecraft's entity renderer does not load .bbmodel files itself.  For the
three live creature replacements this script emits tiny, valid Java 17 class
files containing Minecraft ModelPart builder calls.  This is an intentional
no-toolchain compiler for the simple static geometry subset: the model's cube
shape and texture are used directly, while Blockbench animations remain stored
as source assets and are not falsely advertised as GeckoLib animation.

Usage: python3 tools/build_nightwatch_bundle.py
Output: ArcanaForge-1.20.1-v1.1.0.jar and a copy in новый мод/.
"""
from __future__ import annotations

import json
import os
import shutil
import struct
import sys
import zipfile
import zlib
from dataclasses import dataclass
from typing import Iterable

# Reuse the original bundle's safe BBModel-to-vanilla conversion for its three
# established item bonuses.  It does not execute a build when imported.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_bundle import (  # noqa: E402
    ADVANCEMENTS,
    BONUS,
    DISPLAY_SLOTS,
    OVERRIDES,
    SKIP_META,
    advancement_json,
    bb_to_vanilla,
    extract_texture_png,
    load_bbmodel,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_FA = os.path.join(REPO, "ForgottenArcana-1.20.1-v1.1.0.jar")
SRC_WF = os.path.join(REPO, "weaponforge-1.0.0.jar")
BB_DIR = os.path.join(REPO, "bbmodels")
MODEL_PACK = os.path.join(REPO, "новый мод", "blockbench_models_pack (1).zip")
OUT_JAR = os.path.join(REPO, "ArcanaForge-1.20.1-v1.1.0.jar")
OUT_COPY = os.path.join(REPO, "новый мод", "ArcanaForge-1.20.1-v1.1.0.jar")

BUNDLE_VERSION = "1.1.0"
BUILD_STAMP = "2026-09-18T00:00:00+0000"
ZIP_DATE = (2026, 9, 18, 0, 0, 0)
PACK_ROOT = "pack/"

# (source .bbmodel, existing model class to replace, entity class descriptor,
#  existing entity texture path, public display name).
# The existing Forgotten Arcana registrations give us real server-side entities
# and client renderer registrations without adding an untested runtime library.
LIVE_REPLACEMENTS = (
    (
        "ghost_king/dark_ghost_king.bbmodel",
        "ru/arena/forgottenarcana/client/model/VoidLichModel",
        "ru/arena/forgottenarcana/entity/VoidLichEntity",
        "assets/forgottenarcana/textures/entity/void_lich.png",
        "dark_ghost_king",
    ),
    (
        "watcher/watcher.bbmodel",
        "ru/arena/forgottenarcana/client/model/RuneGolemModel",
        "ru/arena/forgottenarcana/entity/RuneGolemEntity",
        "assets/forgottenarcana/textures/entity/rune_golem.png",
        "watcher",
    ),
    (
        "eyebat/eyebat.bbmodel",
        "ru/arena/forgottenarcana/client/model/ArcaneWispModel",
        "ru/arena/forgottenarcana/entity/ArcaneWispEntity",
        "assets/forgottenarcana/textures/entity/arcane_wisp.png",
        "eyebat",
    ),
)

# Model source paths exposed as static entity figurines.  They are actual
# vanilla JSON item models, not merely files bundled for later editing.
CREATURE_CATALOGUE = (
    ("ghost_king/dark_ghost_king.bbmodel", "dark_ghost_king", "assets/forgottenarcana/models/item/void_lich_spawn_egg.json", 331),
    ("stone_guardian/stone_guardian.bbmodel", "stone_guardian", "assets/forgottenarcana/models/item/rune_golem_spawn_egg.json", 321),
    ("watcher/watcher.bbmodel", "watcher", "assets/forgottenarcana/models/item/rune_golem_spawn_egg.json", 322),
    ("eyebat/eyebat.bbmodel", "eyebat", "assets/forgottenarcana/models/item/arcane_wisp_spawn_egg.json", 311),
    ("zombie/scary_zombie.bbmodel", "scary_zombie", "assets/forgottenarcana/models/item/arcane_wisp_spawn_egg.json", 312),
    ("well_monster/well_monster.bbmodel", "well_monster", "assets/forgottenarcana/models/item/arcane_wisp_spawn_egg.json", 313),
    ("gravedigger/gravedigger.bbmodel", "gravedigger", "assets/forgottenarcana/models/item/arcane_wisp_spawn_egg.json", 314),
    ("domovoi/domovoi.bbmodel", "domovoi", "assets/forgottenarcana/models/item/arcane_wisp_spawn_egg.json", 315),
    ("pale_one/pale_one.bbmodel", "pale_one", "assets/forgottenarcana/models/item/arcane_wisp_spawn_egg.json", 316),
    ("world_worm/world_worm.bbmodel", "world_worm", "assets/forgottenarcana/models/item/arcane_wisp_spawn_egg.json", 317),
)

STAFF_CATALOGUE = (
    ("staffs/dark_coral_staff.bbmodel", "dark_coral_staff", "assets/forgottenarcana/models/item/staff_sparks.json", 201),
    ("staffs/skeletal_staff.bbmodel", "skeletal_staff", "assets/forgottenarcana/models/item/staff_sparks.json", 202),
    ("staffs/ice_staff.bbmodel", "ice_staff", "assets/forgottenarcana/models/item/frost_wand.json", 203),
    ("staffs/wooden_staff.bbmodel", "wooden_staff", "assets/forgottenarcana/models/item/frost_wand.json", 204),
    ("staffs/loki_scepter.bbmodel", "loki_scepter", "assets/forgottenarcana/models/item/void_scepter.json", 205),
    ("staffs/scepter_of_darkness.bbmodel", "scepter_of_darkness", "assets/forgottenarcana/models/item/void_scepter.json", 206),
)

def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


# A valid 1×1 transparent RGBA PNG.  The existing renderers retain their glow
# layer, therefore this deliberately blank replacement stops an old glow map
# from being projected across the new Blockbench geometry.
TRANSPARENT_PNG = (
    b"\x89PNG\r\n\x1a\n"
    + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    + _png_chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00"))
    + _png_chunk(b"IEND", b"")
)


# ---------------------------------------------------------------------------
# Minimal class-file writer for vanilla ModelPart geometry
# ---------------------------------------------------------------------------

class ConstantPool:
    """Constant pool writer for precisely the entries needed in model classes."""

    def __init__(self) -> None:
        self.entries: list[bytes | None] = [None]  # JVM constant pools are 1-based
        self.indices: dict[tuple[object, ...], int] = {}

    def _add(self, key: tuple[object, ...], payload: bytes) -> int:
        if key in self.indices:
            return self.indices[key]
        index = len(self.entries)
        self.entries.append(payload)
        self.indices[key] = index
        return index

    def utf8(self, text: str) -> int:
        raw = text.encode("utf-8")
        return self._add(("utf8", text), b"\x01" + struct.pack(">H", len(raw)) + raw)

    def class_(self, name: str) -> int:
        return self._add(("class", name), b"\x07" + struct.pack(">H", self.utf8(name)))

    def string(self, value: str) -> int:
        return self._add(("string", value), b"\x08" + struct.pack(">H", self.utf8(value)))

    def float_(self, value: float) -> int:
        raw = struct.pack(">f", float(value))
        return self._add(("float", raw), b"\x04" + raw)

    def name_type(self, name: str, desc: str) -> int:
        return self._add(
            ("name_type", name, desc),
            b"\x0c" + struct.pack(">HH", self.utf8(name), self.utf8(desc)),
        )

    def methodref(self, owner: str, name: str, desc: str) -> int:
        return self._add(
            ("methodref", owner, name, desc),
            b"\x0a" + struct.pack(">HH", self.class_(owner), self.name_type(name, desc)),
        )

    def fieldref(self, owner: str, name: str, desc: str) -> int:
        return self._add(
            ("fieldref", owner, name, desc),
            b"\x09" + struct.pack(">HH", self.class_(owner), self.name_type(name, desc)),
        )

    def dump(self) -> bytes:
        return struct.pack(">H", len(self.entries)) + b"".join(x for x in self.entries[1:] if x is not None)


def u2(v: int) -> bytes:
    assert 0 <= v <= 0xFFFF, v
    return struct.pack(">H", v)


def ldc(cp: ConstantPool, index: int) -> bytes:
    return (b"\x12" + bytes([index])) if index <= 0xFF else (b"\x13" + u2(index))


def sipush(value: int) -> bytes:
    assert -32768 <= value <= 32767, value
    return b"\x11" + struct.pack(">h", value)


def code_attribute(cp: ConstantPool, code: bytes, max_stack: int, max_locals: int) -> bytes:
    """One ``Code`` attribute; linear methods need no StackMapTable."""
    body = struct.pack(">HHI", max_stack, max_locals, len(code)) + code + b"\x00\x00\x00\x00"
    return u2(cp.utf8("Code")) + struct.pack(">I", len(body)) + body


def method_info(cp: ConstantPool, access: int, name: str, desc: str, code: bytes, max_stack: int, max_locals: int) -> bytes:
    attr = code_attribute(cp, code, max_stack, max_locals)
    return struct.pack(">HHHH", access, cp.utf8(name), cp.utf8(desc), 1) + attr


def field_info(cp: ConstantPool, access: int, name: str, desc: str) -> bytes:
    return struct.pack(">HHHH", access, cp.utf8(name), cp.utf8(desc), 0)


def model_class_bytes(class_name: str, entity_class: str, cubes: list[dict], tex_w: int, tex_h: int) -> bytes:
    """Create a Java 17 HierarchicalModel class for a static BBModel pose.

    Every Blockbench cube becomes a ModelPart child.  This has two important
    properties: cube pivots remain useful and faces that had unsupported
    multi-axis rotations still render as clean, axis-aligned geometry instead
    of aborting the release.  Group and per-cube animation tracks are retained
    in the bundled source animation JSON.
    """
    cp = ConstantPool()
    super_name = "net/minecraft/client/model/HierarchicalModel"
    model_part = "net/minecraft/client/model/geom/ModelPart"
    mesh = "net/minecraft/client/model/geom/builders/MeshDefinition"
    part_def = "net/minecraft/client/model/geom/builders/PartDefinition"
    cube_builder = "net/minecraft/client/model/geom/builders/CubeListBuilder"
    pose = "net/minecraft/client/model/geom/PartPose"
    layer = "net/minecraft/client/model/geom/builders/LayerDefinition"

    # public <init>(ModelPart root) { super(); this.root = root; }
    init = (
        b"\x2a"  # aload_0
        + b"\xb7" + u2(cp.methodref(super_name, "<init>", "()V"))
        + b"\x2a\x2b"  # aload_0, aload_1
        + b"\xb5" + u2(cp.fieldref(class_name, "root", f"L{model_part};"))
        + b"\xb1"
    )

    # public ModelPart root()
    root_method = b"\x2a" + b"\xb4" + u2(cp.fieldref(class_name, "root", f"L{model_part};")) + b"\xb0"

    # public static LayerDefinition createBodyLayer()
    create = bytearray()
    create += b"\xbb" + u2(cp.class_(mesh)) + b"\x59" + b"\xb7" + u2(cp.methodref(mesh, "<init>", "()V")) + b"\x4b"  # astore_0
    create += b"\x2a" + b"\xb6" + u2(cp.methodref(mesh, "m_171576_", f"()L{part_def};")) + b"\x4c"  # astore_1
    for index, cube in enumerate(cubes):
        # root.addOrReplaceChild("cube_N", CubeListBuilder.create().texOffs(u,v)
        #       .addBox(-w/2,-h/2,-d/2,w,h,d), PartPose.offset(cx,cy,cz));
        create += b"\x2b"  # aload_1
        create += ldc(cp, cp.string(f"cube_{index}"))
        create += b"\xb8" + u2(cp.methodref(cube_builder, "m_171558_", f"()L{cube_builder};"))
        create += sipush(cube["u"]) + sipush(cube["v"])
        create += b"\xb6" + u2(cp.methodref(cube_builder, "m_171514_", f"(II)L{cube_builder};"))
        for f in cube["box"]:
            create += ldc(cp, cp.float_(f))
        create += b"\xb6" + u2(cp.methodref(cube_builder, "m_171481_", f"(FFFFFF)L{cube_builder};"))
        for f in cube["pose"]:
            create += ldc(cp, cp.float_(f))
        create += b"\xb8" + u2(cp.methodref(pose, "m_171419_", f"(FFF)L{pose};"))
        create += b"\xb6" + u2(cp.methodref(part_def, "m_171599_", f"(Ljava/lang/String;L{cube_builder};L{pose};)L{part_def};"))
        create += b"\x57"  # pop returned PartDefinition
    create += b"\x2a" + sipush(tex_w) + sipush(tex_h)
    create += b"\xb8" + u2(cp.methodref(layer, "m_171565_", f"(L{mesh};II)L{layer};")) + b"\xb0"

    # The original classes are generic EntityModel subclasses.  Keep their
    # erased bridge method so MobRenderer invokes this no-op pose handler.
    entity_desc = f"L{entity_class};"
    typed_setup = b"\xb1"
    bridge = (
        b"\x2a\x2b" + b"\xc0" + u2(cp.class_(entity_class))
        + b"\x24\x25\x17\x04\x17\x05\x17\x06"  # fload_2..fload_6
        + b"\xb6" + u2(cp.methodref(class_name, "setupAnim", f"({entity_desc}FFFFF)V"))
        + b"\xb1"
    )

    methods = [
        method_info(cp, 0x0001, "<init>", f"(L{model_part};)V", init, 2, 2),
        method_info(cp, 0x0009, "createBodyLayer", f"()L{layer};", bytes(create), 9, 2),
        method_info(cp, 0x0001, "m_142109_", f"()L{model_part};", root_method, 1, 1),
        method_info(cp, 0x0001, "setupAnim", f"({entity_desc}FFFFF)V", typed_setup, 0, 7),
        method_info(cp, 0x1041, "m_6973_", f"(Lnet/minecraft/world/entity/Entity;FFFFF)V", bridge, 7, 7),
    ]
    fields = [field_info(cp, 0x0012, "root", f"L{model_part};")]
    # Add this/super entries before serialising the constant pool.  Class-file
    # indices are immutable once bytecode instructions have been emitted.
    this_class = cp.class_(class_name)
    super_class = cp.class_(super_name)

    return (
        b"\xca\xfe\xba\xbe" + struct.pack(">HH", 0, 61) + cp.dump()
        + struct.pack(">HHH", 0x0021, this_class, super_class)
        + b"\x00\x00"  # interfaces
        + u2(len(fields)) + b"".join(fields)
        + u2(len(methods)) + b"".join(methods)
        + b"\x00\x00"  # class attributes
    )


# ---------------------------------------------------------------------------
# BBModel conversion helpers
# ---------------------------------------------------------------------------

def png_dimensions(blob: bytes) -> tuple[int, int]:
    """Read dimensions from a PNG IHDR without requiring Pillow."""
    if blob[:8] != b"\x89PNG\r\n\x1a\n" or blob[12:16] != b"IHDR":
        raise ValueError("expected a PNG with an IHDR header")
    return struct.unpack(">II", blob[16:24])


def texture_bytes(pack: zipfile.ZipFile, rel_model: str, bb: dict) -> tuple[bytes, bytes | None]:
    """Return the pack's external PNG and optional animation mcmeta file.

    The supplied files are resource-pack-ready animated strips.  They are
    copied untouched so the live models use the intended animation frames.
    """
    folder = rel_model.rsplit("/", 1)[0]
    texture_name = bb["textures"][0]["name"]
    path = f"{PACK_ROOT}{folder}/{texture_name}"
    try:
        png = pack.read(path)
    except KeyError:
        # The embedded texture is authoritative for BBModel-only files.
        png = extract_texture_png(bb)
        path = ""
    mcmeta = None
    if path:
        try:
            mcmeta = pack.read(path + ".mcmeta")
        except KeyError:
            pass
    return png, mcmeta


def pick_uv(element: dict, tex_w: int, tex_h: int) -> tuple[int, int]:
    """Choose a valid face origin for CubeListBuilder's shared UV layout."""
    for face in element.get("faces", {}).values():
        if face.get("texture") is not None and face.get("enabled", True):
            uv = face.get("uv")
            if uv and len(uv) == 4:
                return (
                    max(0, min(tex_w - 1, int(round(min(uv[0], uv[2]))))),
                    max(0, min(tex_h - 1, int(round(min(uv[1], uv[3]))))),
                )
    return (0, 0)


def bb_to_entity_cubes(bb: dict) -> tuple[list[dict], int, int]:
    """Flatten a BBModel's static cubes into vanilla ModelPart builder data.

    Vanilla's CubeListBuilder has one rectangular UV island per cuboid whereas
    the supplied free-format models have arbitrary per-face UVs.  The chosen
    UV origin keeps each cuboid textured and the raw BBModel remains embedded
    for full-fidelity animation/editing.  Transforming Blockbench's Y-up grid
    to Minecraft's Y-down model grid gives the entity a proper feet anchor.
    """
    resolution = bb.get("resolution") or {}
    tex_w = int(resolution.get("width") or 128)
    tex_h = int(resolution.get("height") or tex_w)
    cubes = []
    for e in bb.get("elements", []):
        x1, y1, z1 = [float(v) for v in e["from"]]
        x2, y2, z2 = [float(v) for v in e["to"]]
        sx, sy, sz = abs(x2 - x1), abs(y2 - y1), abs(z2 - z1)
        if min(sx, sy, sz) <= 0:
            continue
        # Blockbench model Y is upward.  Entity model feet live at y=24.
        cx = (x1 + x2) / 2.0
        cy = 24.0 - (y1 + y2) / 2.0
        cz = (z1 + z2) / 2.0
        u, v = pick_uv(e, tex_w, tex_h)
        cubes.append({
            "u": u,
            "v": v,
            "box": [-sx / 2.0, -sy / 2.0, -sz / 2.0, sx, sy, sz],
            "pose": [cx, cy, cz],
        })
    if not cubes:
        raise ValueError("BBModel has no visible cubes")
    return cubes, tex_w, tex_h


def bb_to_flat_item(bb: dict, texture_path: str, label: str) -> dict:
    """Make a safely normalized static vanilla item model from any BBModel.

    This is used for the model catalogue.  Item JSON allows only one axis of
    cuboid rotation, so complex free-format rotations are intentionally baked
    as unrotated boxes rather than silently emitting invalid JSON.
    """
    elements = bb.get("elements", [])
    if not elements:
        raise ValueError(f"{label}: no elements")
    mins = [min(float(e["from"][i]) for e in elements) for i in range(3)]
    maxs = [max(float(e["to"][i]) for e in elements) for i in range(3)]
    span = max(maxs[i] - mins[i] for i in range(3))
    scale = 14.0 / max(span, 0.001)
    translate = [8.0 - (mins[0] + maxs[0]) * scale / 2.0, -mins[1] * scale, 8.0 - (mins[2] + maxs[2]) * scale / 2.0]

    def pt(point: Iterable[float]) -> list[float]:
        return [round(float(point[i]) * scale + translate[i], 4) for i in range(3)]

    out = []
    for e in elements:
        faces = {}
        for direction, face in e.get("faces", {}).items():
            if face.get("enabled", True) and face.get("texture") is not None:
                f = {"uv": [float(v) for v in face["uv"]], "texture": "#0"}
                if face.get("rotation"):
                    f["rotation"] = int(face["rotation"])
                faces[direction] = f
        if faces:
            out.append({"from": pt(e["from"]), "to": pt(e["to"]), "faces": faces})
    if not out:
        raise ValueError(f"{label}: no visible faces")
    return {
        "credit": "Original Blockbench model supplied by user; static catalogue conversion by ArcanaForge",
        "textures": {"0": texture_path, "particle": texture_path},
        "elements": out,
        "display": {
            "gui": {"rotation": [25, 45, 0], "translation": [0, -1, 0], "scale": [0.82, 0.82, 0.82]},
            "ground": {"translation": [0, 2, 0], "scale": [0.5, 0.5, 0.5]},
            "fixed": {"rotation": [0, 180, 0], "translation": [0, -1, 0], "scale": [0.7, 0.7, 0.7]},
            "thirdperson_righthand": {"rotation": [75, 45, 0], "translation": [0, 2.5, 0], "scale": [0.55, 0.55, 0.55]},
            "firstperson_righthand": {"rotation": [0, -90, 25], "translation": [1.13, 3.2, 1.13], "scale": [0.68, 0.68, 0.68]},
        },
    }


def patch_model_override(merged: dict[str, bytes], path: str, custom_data: int, model: str) -> None:
    if path not in merged:
        raise KeyError(f"Missing base item model: {path}")
    data = json.loads(merged[path].decode("utf-8"))
    overrides = data.setdefault("overrides", [])
    if any(x.get("predicate", {}).get("custom_model_data") == custom_data for x in overrides):
        raise ValueError(f"Duplicate CustomModelData {custom_data} in {path}")
    overrides.append({"predicate": {"custom_model_data": custom_data}, "model": model})
    merged[path] = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def base_languages() -> dict[str, dict[str, str]]:
    return {
        "en_us": {
            "advancement.arcanaforge.magic_wand.title": "Wand of the Archmage",
            "advancement.arcanaforge.magic_wand.desc": "Get the crystal wand look for the Staff of Sparks (CustomModelData 101)",
            "advancement.arcanaforge.ghost_hat.title": "Helm of the Ghost Knight",
            "advancement.arcanaforge.ghost_hat.desc": "Get the ghost knight hat look for the King's Seal (CustomModelData 102)",
            "advancement.arcanaforge.golem_figurine.title": "Pocket Golem",
            "advancement.arcanaforge.golem_figurine.desc": "Get the Ancient Golem figurine look for the golem spawn egg (CustomModelData 103)",
            "entity.arcanaforge.watcher": "The Watcher",
            "entity.arcanaforge.eyebat": "Eyebat",
            "message.arcanaforge.watcher_arrival": "§5Something is watching from the darkness...",
        },
        "ru_ru": {
            "advancement.arcanaforge.magic_wand.title": "Жезл архимага",
            "advancement.arcanaforge.magic_wand.desc": "Получить кристальный жезл — облик Посоха искр (CustomModelData 101)",
            "advancement.arcanaforge.ghost_hat.title": "Шлем Рыцаря-Призрака",
            "advancement.arcanaforge.ghost_hat.desc": "Получить шляпу рыцаря-призрака — облик Печати Короля (CustomModelData 102)",
            "advancement.arcanaforge.golem_figurine.title": "Карманный голем",
            "advancement.arcanaforge.golem_figurine.desc": "Получить статуэтку Древнего Голема — облик яйца голема (CustomModelData 103)",
            "entity.arcanaforge.watcher": "Смотрящий",
            "entity.arcanaforge.eyebat": "Глазыш",
            "message.arcanaforge.watcher_arrival": "§5Из темноты за вами кто-то наблюдает...",
        },
    }


MODS_TOML = """\
modLoader="javafml"
loaderVersion="[47,)"
license="Apache-2.0 AND MIT"

[[mods]]
modId="forgottenarcana"
version="1.1.0"
displayName="Забытые Арканы: Ночной дозор | Forgotten Arcana: Nightwatch"
authors="esikovartem, Arena Agent"
logoFile="logo.png"
description='''ArcanaForge Nightwatch: one Forge 1.20.1 JAR. The Forgotten King now has the Dark Ghost King 3D model; the Watcher appears with Eyebat helpers on the second night. The complete supplied Blockbench model archive and a 3D catalogue are included.'''

[[mods]]
modId="weaponforge"
version="1.0.0"
displayName="Weapon Forge - Кузница стихий"
authors="Arena.ai Agent"
description='''84 elemental weapons in the single ArcanaForge Nightwatch JAR.'''

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
    "Specification-Title: arcanaforge-nightwatch\r\n"
    "Specification-Vendor: Arena Agent\r\n"
    "Specification-Version: 1\r\n"
    f"Implementation-Title: arcanaforge-nightwatch\r\nImplementation-Version: {BUNDLE_VERSION}\r\n"
    "Implementation-Vendor: Arena Agent\r\n"
    f"Implementation-Timestamp: {BUILD_STAMP}\r\n\r\n"
)
PACK_MCMETA = {"pack": {"description": "ArcanaForge Nightwatch: one Forge mod JAR", "pack_format": 15}}


@dataclass(frozen=True)
class CatalogueModel:
    rel: str
    name: str
    item_model: str
    custom_data: int


def main() -> None:
    for path in (SRC_FA, SRC_WF, MODEL_PACK):
        if not os.path.isfile(path):
            raise SystemExit(f"Missing required source: {path}")

    print("== 1. Merge the two original Forge mods ==")
    merged: dict[str, bytes] = {}
    for source, tag in ((SRC_FA, "Forgotten Arcana"), (SRC_WF, "Weapon Forge")):
        with zipfile.ZipFile(source) as archive:
            for info in archive.infolist():
                if info.is_dir() or info.filename in SKIP_META:
                    continue
                if info.filename in merged:
                    raise RuntimeError(f"File collision while merging {tag}: {info.filename}")
                merged[info.filename] = archive.read(info.filename)
        print(f"  {tag}: merged")

    print("== 2. Keep the established three bonus item models ==")
    bonus_files: dict[str, bytes] = {}
    for bb_file, name, norm_h in BONUS:
        bb = load_bbmodel(os.path.join(BB_DIR, bb_file))
        png = extract_texture_png(bb)
        # Existing source models use the constrained java-block subset.
        model = bb_to_vanilla(bb, f"arcanaforge:item/{name}", norm_h, label=name)
        bonus_files[f"assets/arcanaforge/models/item/{name}.json"] = json.dumps(model, ensure_ascii=False, indent=2).encode("utf-8")
        bonus_files[f"assets/arcanaforge/textures/item/{name}.png"] = png
    for path, cmd, target in OVERRIDES:
        patch_model_override(merged, path, cmd, target)

    print("== 3. Import Blockbench pack and build live entity replacements ==")
    source_models: dict[str, dict] = {}
    source_textures: dict[str, tuple[bytes, bytes | None]] = {}
    preserved_pack_files: list[str] = []
    with zipfile.ZipFile(MODEL_PACK) as pack:
        # Preserve the full supplied archive in a conventional asset namespace.
        for info in pack.infolist():
            if info.is_dir() or not info.filename.startswith(PACK_ROOT):
                continue
            relative = info.filename[len(PACK_ROOT):]
            output_path = f"assets/arcanaforge/blockbench/{relative}"
            bonus_files[output_path] = pack.read(info.filename)
            preserved_pack_files.append(output_path)

        for rel, model_class, entity_class, replacement_texture, name in LIVE_REPLACEMENTS:
            raw = pack.read(PACK_ROOT + rel)
            bb = json.loads(raw.decode("utf-8"))
            png, mcmeta = texture_bytes(pack, rel, bb)
            cubes, tw, th = bb_to_entity_cubes(bb)
            class_path = model_class + ".class"
            if class_path not in merged:
                raise KeyError(f"Original client model missing: {class_path}")
            merged[class_path] = model_class_bytes(model_class, entity_class, cubes, tw, th)
            merged[replacement_texture] = png
            # Existing glow layer would otherwise project the old glow texture
            # across the new geometry. A transparent image preserves its safe API.
            merged[replacement_texture.replace(".png", "_glow.png")] = TRANSPARENT_PNG
            if mcmeta:
                merged[replacement_texture + ".mcmeta"] = mcmeta
            source_models[rel] = bb
            source_textures[rel] = (png, mcmeta)
            print(f"  {name}: {len(cubes)} cubes -> {class_path}")

        print("== 4. Make every supplied model accessible as a 3D catalogue look ==")
        catalogue = [CatalogueModel(*x) for x in CREATURE_CATALOGUE + STAFF_CATALOGUE]
        for entry in catalogue:
            bb = source_models.get(entry.rel)
            texture = source_textures.get(entry.rel)
            if bb is None or texture is None:
                bb = json.loads(pack.read(PACK_ROOT + entry.rel).decode("utf-8"))
                texture = texture_bytes(pack, entry.rel, bb)
                source_models[entry.rel] = bb
                source_textures[entry.rel] = texture
            png, mcmeta = texture
            model_path = f"assets/arcanaforge/models/item/catalogue/{entry.name}.json"
            texture_path = f"assets/arcanaforge/textures/item/catalogue/{entry.name}.png"
            bonus_files[model_path] = json.dumps(
                bb_to_flat_item(bb, f"arcanaforge:item/catalogue/{entry.name}", entry.name),
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")
            bonus_files[texture_path] = png
            if mcmeta:
                bonus_files[texture_path + ".mcmeta"] = mcmeta
            patch_model_override(merged, entry.item_model, entry.custom_data, f"arcanaforge:item/catalogue/{entry.name}")
            print(f"  {entry.name}: CustomModelData {entry.custom_data}")

    print("== 5. Add Nightwatch second-night event and translations ==")
    languages = base_languages()
    for locale, entries in languages.items():
        bonus_files[f"assets/arcanaforge/lang/{locale}.json"] = json.dumps(entries, ensure_ascii=False, indent=2).encode("utf-8")

    # Rename only presentation strings; registry IDs and original gameplay stay
    # stable for worlds that previously used Forgotten Arcana.
    language_patches = {
        "en_us": {
            "item.forgottenarcana.boss_seal": "Seal of the Dark Ghost King",
            "item.forgottenarcana.boss_seal.tooltip2": "...and the Dark Ghost King shall rise from the Void",
            "item.forgottenarcana.arcane_wisp_spawn_egg": "Eyebat Spawn Egg",
            "item.forgottenarcana.rune_golem_spawn_egg": "Watcher Spawn Egg",
            "item.forgottenarcana.void_lich_spawn_egg": "Dark Ghost King Spawn Egg",
            "entity.forgottenarcana.arcane_wisp": "Eyebat",
            "entity.forgottenarcana.rune_golem": "Watcher",
            "entity.forgottenarcana.void_lich": "Dark Ghost King",
            "event.forgottenarcana.boss_summoned": "The seal is broken... The Dark Ghost King has awakened!",
            "event.forgottenarcana.boss_defeated": "The Dark Ghost King has been vanquished! The Void recedes...",
        },
        "ru_ru": {
            "item.forgottenarcana.boss_seal": "Печать Тёмного Призрачного Короля",
            "item.forgottenarcana.boss_seal.tooltip2": "...и Тёмный Призрачный Король восстанет из Пустоты",
            "item.forgottenarcana.arcane_wisp_spawn_egg": "Яйцо призыва: Глазыш",
            "item.forgottenarcana.rune_golem_spawn_egg": "Яйцо призыва: Смотрящий",
            "item.forgottenarcana.void_lich_spawn_egg": "Яйцо призыва: Тёмный Призрачный Король",
            "entity.forgottenarcana.arcane_wisp": "Глазыш",
            "entity.forgottenarcana.rune_golem": "Смотрящий",
            "entity.forgottenarcana.void_lich": "Тёмный Призрачный Король",
            "event.forgottenarcana.boss_summoned": "Печать сломана... Тёмный Призрачный Король пробудился!",
            "event.forgottenarcana.boss_defeated": "Тёмный Призрачный Король повержен! Пустота отступает...",
        },
    }
    for locale, patch in language_patches.items():
        path = f"assets/forgottenarcana/lang/{locale}.json"
        old = json.loads(merged[path].decode("utf-8"))
        old.update(patch)
        merged[path] = json.dumps(old, ensure_ascii=False, indent=2).encode("utf-8")

    for adv_name, item, cmd in ADVANCEMENTS:
        bonus_files[f"data/arcanaforge/advancements/{adv_name}.json"] = json.dumps(advancement_json(adv_name, item, cmd), ensure_ascii=False, indent=2).encode("utf-8")

    # In a fresh world 37,000 ticks is the beginning of its second night.
    # Functions use only vanilla commands, so they work on both client and
    # dedicated Forge servers without a client-only dependency.
    bonus_files["data/minecraft/tags/functions/load.json"] = b'{"values":["arcanaforge:nightwatch/load"]}\n'
    bonus_files["data/minecraft/tags/functions/tick.json"] = b'{"values":["arcanaforge:nightwatch/tick"]}\n'
    bonus_files["data/arcanaforge/functions/nightwatch/load.mcfunction"] = (
        "# The counter starts when this built-in data pack loads.\n"
        "scoreboard objectives add af_nightwatch dummy\n"
        "scoreboard players set #ticks af_nightwatch 0\n"
    ).encode("utf-8")
    bonus_files["data/arcanaforge/functions/nightwatch/tick.mcfunction"] = (
        "scoreboard players add #ticks af_nightwatch 1\n"
        "execute if score #ticks af_nightwatch matches 37000 run function arcanaforge:nightwatch/second_night\n"
    ).encode("utf-8")
    bonus_files["data/arcanaforge/functions/nightwatch/second_night.mcfunction"] = (
        "# One persistent, motionless Watcher per player, 28 blocks ahead.\n"
        "execute as @a at @s unless entity @e[type=forgottenarcana:rune_golem,tag=arcanaforge.watcher,distance=..96,limit=1] positioned ^ ^ ^28 facing entity @s eyes run summon forgottenarcana:rune_golem ~ ~ ~ {Tags:[\"arcanaforge.watcher\",\"arcanaforge.second_night\"],CustomName:'{\"translate\":\"entity.arcanaforge.watcher\"}',CustomNameVisible:1b,PersistenceRequired:1b,NoAI:1b,Silent:1b}\n"
        "# The three stationary Eyebats are the Watcher's helpers.\n"
        "execute as @a at @s positioned ^ ^ ^28 run summon forgottenarcana:arcane_wisp ~3 ~3 ~ {Tags:[\"arcanaforge.eyebat\",\"arcanaforge.watcher_helper\"],CustomName:'{\"translate\":\"entity.arcanaforge.eyebat\"}',PersistenceRequired:1b,NoAI:1b,Silent:1b}\n"
        "execute as @a at @s positioned ^ ^ ^28 run summon forgottenarcana:arcane_wisp ~-3 ~4 ~2 {Tags:[\"arcanaforge.eyebat\",\"arcanaforge.watcher_helper\"],CustomName:'{\"translate\":\"entity.arcanaforge.eyebat\"}',PersistenceRequired:1b,NoAI:1b,Silent:1b}\n"
        "execute as @a at @s positioned ^ ^ ^28 run summon forgottenarcana:arcane_wisp ~ ~6 ~-3 {Tags:[\"arcanaforge.eyebat\",\"arcanaforge.watcher_helper\"],CustomName:'{\"translate\":\"entity.arcanaforge.eyebat\"}',PersistenceRequired:1b,NoAI:1b,Silent:1b}\n"
        "tellraw @a [{\"translate\":\"message.arcanaforge.watcher_arrival\"}]\n"
    ).encode("utf-8")

    catalogue_info = {
        "bundle": "ArcanaForge Nightwatch",
        "version": BUNDLE_VERSION,
        "minecraft": "1.20.1",
        "forge": "47+",
        "live_replacements": [
            {"entity": "forgottenarcana:void_lich", "model": "dark_ghost_king", "role": "Forgotten King replacement"},
            {"entity": "forgottenarcana:rune_golem", "model": "watcher", "role": "second-night Watcher"},
            {"entity": "forgottenarcana:arcane_wisp", "model": "eyebat", "role": "Watcher helper"},
        ],
        "catalogue_models": [entry.__dict__ for entry in catalogue],
        "second_night_tick": 37000,
        "model_source_root": "assets/arcanaforge/blockbench/",
        "note": "Entity animations are stored as supplied Blockbench/Bedrock source; live Forge vanilla ModelPart models are static poses.",
    }
    bonus_files["arcanaforge_nightwatch.json"] = json.dumps(catalogue_info, ensure_ascii=False, indent=2).encode("utf-8")

    for path, blob in bonus_files.items():
        if path in merged:
            raise RuntimeError(f"Unexpected generated resource collision: {path}")
        merged[path] = blob
    merged["META-INF/mods.toml"] = MODS_TOML.encode("utf-8")
    merged["META-INF/MANIFEST.MF"] = MANIFEST.encode("utf-8")
    merged["pack.mcmeta"] = (json.dumps(PACK_MCMETA, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    print("== 6. Write the one-file mod ==")
    with zipfile.ZipFile(OUT_JAR, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for path in sorted(merged):
            info = zipfile.ZipInfo(path, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(info, merged[path])
    os.makedirs(os.path.dirname(OUT_COPY), exist_ok=True)
    shutil.copyfile(OUT_JAR, OUT_COPY)
    print(f"  {OUT_JAR}: {os.path.getsize(OUT_JAR):,} bytes, {len(merged)} files")

    print("== 7. Verify artifact ==")
    with zipfile.ZipFile(OUT_JAR) as archive:
        if archive.testzip() is not None:
            raise RuntimeError(f"Corrupt output at {archive.testzip()}")
        names = set(archive.namelist())
        for required in (
            "ru/arena/forgottenarcana/ForgottenArcanaMod.class",
            "com/weaponforge/WeaponForge.class",
            "ru/arena/forgottenarcana/client/model/VoidLichModel.class",
            "ru/arena/forgottenarcana/client/model/RuneGolemModel.class",
            "ru/arena/forgottenarcana/client/model/ArcaneWispModel.class",
            "data/arcanaforge/functions/nightwatch/second_night.mcfunction",
            "data/minecraft/tags/functions/tick.json",
            "arcanaforge_nightwatch.json",
        ):
            assert required in names, required
        for rel, *_ in LIVE_REPLACEMENTS:
            assert f"assets/arcanaforge/blockbench/{rel}" in names, rel
        # Keep every non-directory source asset from the supplied ZIP, not only
        # the files used by the three live replacements.
        assert preserved_pack_files, "model pack unexpectedly contains no files"
        for path in preserved_pack_files:
            assert path in names, path
        for entry in catalogue:
            path = f"assets/arcanaforge/models/item/catalogue/{entry.name}.json"
            assert path in names, path
            json.loads(archive.read(path))
        for class_path in (
            "ru/arena/forgottenarcana/client/model/VoidLichModel.class",
            "ru/arena/forgottenarcana/client/model/RuneGolemModel.class",
            "ru/arena/forgottenarcana/client/model/ArcaneWispModel.class",
        ):
            raw = archive.read(class_path)
            assert raw[:4] == b"\xca\xfe\xba\xbe" and raw[6:8] == b"\x00=", class_path
        assert archive.read("META-INF/mods.toml").count(b"[[mods]]") == 2
        assert archive.read("assets/forgottenarcana/textures/entity/void_lich.png") != archive.read("assets/forgottenarcana/textures/entity/rune_golem.png")
    if open(OUT_JAR, "rb").read() != open(OUT_COPY, "rb").read():
        raise RuntimeError("The release copy in новый мод differs from the built JAR")
    print("  all checks passed ✔")


if __name__ == "__main__":
    main()
