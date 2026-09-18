# ArcanaForge — общий мод (сборка) | Bundle

Один JAR для **Minecraft 1.20.1 (Forge 47+)**, в котором живут сразу
**два мода + бонусные 3D-модели**:

| Что внутри | Версия | Лицензия |
|------------|--------|----------|
| Забытые Арканы (Forgotten Arcana) — магия, руда, алтарь, босс | 1.1.0 | Apache-2.0 |
| Weapon Forge — Кузница стихий (84 стихийных оружия) | 1.0.0 | MIT |
| Бонус: 3 новые 3D-модели + 3 достижения | — | Apache-2.0 |

Forge умеет держать несколько модов в одном файле, поэтому в списке
модов вы увидите две записи — это нормально: файл при этом один.

## Установка

1. Установите [Forge 1.20.1](https://files.minecraftforge.net/) (47.x).
2. Положите **`ArcanaForge-1.20.1-v1.0.0.jar`** в папку `mods`.
3. Запускайте игру. Отдельно ставить ForgottenArcana и WeaponForge
   **не нужно** (и нельзя — будет конфликт дубликатов).

| Файл | Назначение |
|------|------------|
| `ArcanaForge-1.20.1-v1.0.0.jar` | **актуальный общий мод — ставьте его** |
| `ForgottenArcana-1.20.1-v1.1.0.jar` | исходник сборки (архив) |
| `ForgottenArcana-1.20.1-v1.0.0.jar` | старый архив |
| `мод/weaponforge-1.0.0 (1).jar` | исходник сборки (архив) |

## Что умеет сборка

### Забытые Арканы (forgottenarcana)
- **Блоки:** мана-руда (вены до 9, высоты −64…40), древний алтарь
  с 3D-моделью и светящимся руническим кругом.
- **Предметы:** осколок и кристалл маны, Сердце Бездны, Посох искр,
  Жезл мороза, Скипетр Пустоты, Печать Забытого Короля, три вида
  магических стрел.
- **Мобы:** Магический виток, Рунный голем, **Забытый Король**
  (босс, вызывается Печатью на алтаре).
- **Эффект:** Обморожение (Frostbite).
- Рецепты, лут-таблицы, достижения, генерация мира.

### Weapon Forge (weaponforge)
- **84 оружия** (14 типов × 6 стихий: огонь, лёд, гроза, лес,
  пустота, свет) с анимированными Blockbench-моделями.
- У каждого оружия — комбо-способности, ульта за ярость и HUD слева сверху.
- 6 стихийных ядер для крафта.

### Бонусные модели (новое в сборке!)
Три BB-модели из папки `мод/` сконвертированы в игровой формат и
вшиты в сборку как особые облики существующих предметов
(работают через `CustomModelData` — поведение предметов не меняется):

| Облик | Как получить | Достижение |
|-------|--------------|------------|
| **Кристальный жезл** (вместо Посоха искр) | `/give @s forgottenarcana:staff_sparks{CustomModelData:101}` | «Жезл архимага» |
| **Шляпа Рыцаря-Призрака** (вместо Печати Короля, печать по-прежнему призывает босса!) | `/give @s forgottenarcana:boss_seal{CustomModelData:102}` | «Шлем Рыцаря-Призрака» |
| **Статуэтка Древнего Голема** (вместо яйца рунного голема, голем призывается как обычно) | `/give @s forgottenarcana:rune_golem_spawn_egg{CustomModelData:103}` | «Карманный голем» |

Превью моделей (рендер из игровых файлов сборки):

- `preview/magic_wand.png` — кристальный жезл (32 элемента)
- `preview/ghost_knight_hat.png` — шляпа рыцаря-призрака (38 элементов)
- `preview/ancient_golem_figurine.png` — Древний Голем (98 элементов)

## 3D-модели (BBModel / Blockbench)

Исходники всех моделей лежат в [`bbmodels/`](bbmodels/) (текстуры вшиты —
открываются в Blockbench как есть). Новенькие из этой сборки:

| Файл | Модель |
|------|--------|
| `bbmodels/magic_wand.bbmodel` | Кристальный жезл |
| `bbmodels/ghost_knight_hat.bbmodel` | Шляпа Рыцаря-Призрака |
| `bbmodels/ancient_golem.bbmodel` | Древний Голем (с анимацией idle) |

Остальные 12 файлов — модели Забытых Аркан (см. старый README в git-истории).

## Как собрано (для любопытных)

Сборка полностью воспроизводима скриптом [`tools/build_bundle.py`](tools/build_bundle.py):
1. Оба исходных JAR распаковываются и сливаются в один
   (конфликтов файлов нет — неймспейсы `forgottenarcana` / `weaponforge`
   и пакеты классов не пересекаются; общими были только
   `mods.toml`, `MANIFEST.MF` и `pack.mcmeta` — они объединены).
2. `mods.toml` содержит две секции `[[mods]]` — Forge загружает их
   как два отдельных мода из одного файла. Код не менялся.
3. BB-модели конвертируются в ванильные JSON-модели + PNG-текстуры
   в неймспейс `arcanaforge` (проверки: координаты в −16…32,
   повороты кратные 22.5°, UV в границах текстуры).
4. На три предмета Аркан вешаются `overrides` по `CustomModelData`,
   добавляются 3 достижения (родитель — `forgottenarcana:root`)
   и переводы RU/EN.

Пересобрать: `python3 tools/build_bundle.py`
(нужен Python 3 + Pillow только для `tools/preview_models.py`).

## Структура проекта

```
├── ArcanaForge-1.20.1-v1.0.0.jar      # ОБЩИЙ МОД — ставьте его
├── ForgottenArcana-1.20.1-v1.1.0.jar   # исходник (архив)
├── ForgottenArcana-1.20.1-v1.0.0.jar   # исходник (архив)
├── мод/                                # исходники сборки: 2-й мод + 3 BB-модели
├── bbmodels/                           # все 15 BB-моделей (Blockbench)
├── tools/                              # build_bundle.py + preview_models.py
├── preview/                            # рендеры бонусных моделей
├── CHANGELOG.md
└── LICENSE                             # Apache-2.0 (WeaponForge внутри — MIT)
```

## Лицензии

- Forgotten Arcana и бонусный контент сборки — [Apache-2.0](LICENSE).
- Weapon Forge внутри сборки — MIT (автор: Arena.ai Agent).
  В `mods.toml` указано `Apache-2.0 AND MIT`.

---

# ArcanaForge bundle (EN)

One JAR for **Minecraft 1.20.1 (Forge 47+)** holding **two mods +
bonus 3D models**: Forgotten Arcana 1.1.0 (magic, ore, altar, boss),
Weapon Forge 1.0.0 (84 elemental weapons) and 3 new models wired as
`CustomModelData` looks for existing items (see table above for
`/give` commands). Install: drop `ArcanaForge-1.20.1-v1.0.0.jar`
into `mods` (Forge 1.20.1, 47.x) — do NOT also install the two
standalone jars. Rebuild anytime with `python3 tools/build_bundle.py`.
