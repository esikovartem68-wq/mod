# Забытые Арканы | Forgotten Arcana

Магический мод для **Minecraft 1.20.1 (Forge 47+)**.

Добывайте мана-руду, соберите древний алтарь и вызовите **Забытого Короля**
из Пустоты. В бою сражаются магические витки, рунные големы и сам Лич.
В руках — посохи: искр, мороза и скипетр Пустоты.

## Установка

1. Установите [Forge 1.20.1](https://files.minecraftforge.net/) (47.x).
2. Положите `ForgottenArcana-1.20.1-v1.1.0.jar` в папку `mods`.
3. Запускайте игру.

| Файл | Версия |
|------|--------|
| `ForgottenArcana-1.20.1-v1.1.0.jar` | текущая |
| `ForgottenArcana-1.20.1-v1.0.0.jar` | архивная |

## Содержимое

- **Блоки:** мана-руда (генерируется во всех биомах надмирного мира, венами до 9),
  древний алтарь (с 3D-моделью и светящимся руническим кругом).
- **Предметы:** осколок и кристалл маны, Сердце Бездны, Посох искр,
  Жезл мороза, Скипетр Пустоты, Печать Забытого Короля, три вида
  магических стрел.
- **Мобы:** Магический виток (спавн в лесах/горах/болотах),
  Рунный голем, **Забытый Король** (босс, вызывается Печатью на алтаре).
- **Эффект:** Обморожение (Frostbite).
- **Контент данных:** рецепты, лут-таблицы, достижения, мир-генерация —
  всё на JSON, без кода.

## 3D-модели (BBModel / Blockbench)

Все 3D-модели предметов и блоков сделаны в формате **BBModel**
(нативный формат [Blockbench](https://www.blockbench.net/)).
Исходники лежат в папке [`bbmodels/`](bbmodels/):

| Файл | Модель |
|------|--------|
| `bbmodels/void_heart.bbmodel` | Сердце Бездны |
| `bbmodels/boss_seal.bbmodel` | Печать Забытого Короля |
| `bbmodels/mana_crystal.bbmodel` | Кристалл маны |
| `bbmodels/mana_shard.bbmodel` | Осколок маны |
| `bbmodels/arcane_bolt.bbmodel` | Чародейская стрела |
| `bbmodels/frost_bolt.bbmodel` | Ледяная стрела |
| `bbmodels/void_bolt.bbmodel` | Болт Пустоты |
| `bbmodels/staff_sparks.bbmodel` | Посох искр |
| `bbmodels/frost_wand.bbmodel` | Жезл мороза |
| `bbmodels/void_scepter.bbmodel` | Скипетр Пустоты |
| `bbmodels/arcane_altar.bbmodel` | Древний алтарь (блок) |
| `bbmodels/arcane_ore.bbmodel` | Мана-руда (блок) |

Текстуры в `.bbmodel` вшиты (base64) — файлы открываются в Blockbench
как есть, без внешних зависимостей.

**Как пользоваться:**

1. Откройте Blockbench → *Открыть файл* → выберите любой файл из `bbmodels/`.
2. Правьте геометрию и текстуры.
3. *Экспорт → Minecraft (Mojang mappings)* → выберите «предмет» или «блок» —
   получите `models/item/<name>.json` (или `models/block/`) в ванильном формате.
4. Текстуру экспортируйте как `textures/item/<name>.png` (16×16) и положите
   в JAR рядом с остальными ассетами.

Именно так в JAR попадают актуальные модели: `assets/forgottenarcana/models/…`
— это экспорт из `bbmodels/`.

## Структура проекта

```
├── ForgottenArcana-1.20.1-v1.1.0.jar   # актуальный мод
├── ForgottenArcana-1.20.1-v1.0.0.jar   # первая версия (архив)
├── bbmodels/                            # исходники 3D-моделей (Blockbench)
├── CHANGELOG.md
└── LICENSE                              # Apache-2.0
```

## Лицензия

[Apache-2.0](LICENSE)

---

# Forgotten Arcana (EN)

A magic mod for **Minecraft 1.20.1 (Forge 47+)**.

Mine arcane ore, build the Ancient Altar and summon the **Forgotten King**
from the Void. Fight arcane wisps, rune golems and the Lich himself.
Wield the Staff of Sparks, the Frost Wand and the Void Scepter.

**Install:** put `ForgottenArcana-1.20.1-v1.1.0.jar` into your `mods` folder
(Forge 1.20.1, 47.x).

All 3D item/block models are authored in **BBModel** format (Blockbench) —
sources with embedded textures live in [`bbmodels/`](bbmodels/).
Open any file in Blockbench, edit, then *Export → Minecraft* to regenerate
the vanilla `assets/forgottenarcana/models/…` JSON used by the JAR.

See [CHANGELOG.md](CHANGELOG.md) for version details.
