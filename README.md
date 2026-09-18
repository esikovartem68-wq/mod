# ArcanaForge: Ночной дозор — один мод

**`ArcanaForge-1.20.1-v1.1.0.jar`** — единый мод для **Minecraft Java 1.20.1 + Forge 47.x**.
Готовый файл находится здесь:

> **[`новый мод/ArcanaForge-1.20.1-v1.1.0.jar`](новый%20мод/ArcanaForge-1.20.1-v1.1.0.jar)**

В папку `mods` нужно положить **только этот один JAR**. Не ставьте рядом старый
`ArcanaForge-1.20.1-v1.0.0.jar`, отдельные `ForgottenArcana` или `weaponforge`:
они содержатся внутри новой сборки и вместе вызовут конфликт ID.

## Что добавлено в «Ночной дозор»

### Тёмный Призрачный Король

Старый босс **Забытый Король** (`forgottenarcana:void_lich`) заменён визуально:
теперь это **Тёмный Призрачный Король** из `ghost_king/dark_ghost_king.bbmodel`.

- Модель состоит из 72 объёмных кубов: корона, плащ, меч, хвост и парящие сферы.
- Боевая логика старого босса не сломана: призыв Печатью на Древнем алтаре,
  босс-бар, атаки и лут сохранены.
- В интерфейсе, яйце призыва и игровых сообщениях он переименован в
  «Тёмного Призрачного Короля».

### Смотрящий и Глазыши

- На **вторую ночь нового мира** (игровой тик `37000`) в 28 блоках перед каждым
  игроком появляется **Смотрящий**. Он развёрнут к игроку, неподвижен и наблюдает
  издалека.
- Вместе с ним появляются три **Глазыша** — его парящие помощники.
- Смотрящий использует объёмную модель `watcher/watcher.bbmodel` (75 кубов), а
  Глазыши — `eyebat/eyebat.bbmodel` (49 кубов).
- Для совместимости с уже существующим модом это устойчивые визуальные замены
  старых ID: Смотрящий — `forgottenarcana:rune_golem`, Глазыш —
  `forgottenarcana:arcane_wisp`. Поэтому старые миры и команды не теряют сущности.
  Глазыши, вызванные ночным событием, неподвижны; при обычном вызове яйцом
  сохраняют прежнюю магическую механику витка.

> Событие рассчитано на новый мир с обычным ходом времени. Счётчик начинает
> отсчёт при загрузке встроенного дата-пака мода; после `/reload` он запускается
> заново.

Ручной вызов для проверки:

```mcfunction
/summon forgottenarcana:rune_golem ~ ~ ~ {CustomName:'{"text":"Смотрящий"}',NoAI:1b,PersistenceRequired:1b}
/summon forgottenarcana:arcane_wisp ~ ~2 ~ {CustomName:'{"text":"Глазыш"}',NoAI:1b,PersistenceRequired:1b}
/summon forgottenarcana:void_lich ~ ~ ~
```

## Все модели из присланной папки

В JAR сохранён полный исходный пакет из `blockbench_models_pack (1).zip`:
BBModel, текстуры, `.mcmeta`, Bedrock/GeckoLib-анимации и файлы генераторов лежат
в `assets/arcanaforge/blockbench/`. Их можно извлечь из JAR или открыть исходный
ZIP в Blockbench.

В Forge 1.20.1 ванильный рендерер не умеет напрямую проигрывать Bedrock/GeckoLib
анимации из `.bbmodel`. Поэтому три главных существа получили реальные
`ModelPart`-модели в игре, а **каждая** модель из архива дополнительно доступна
как статичная 3D-фигурка через `CustomModelData`. Анимированные текстуры из
архива сохранены без изменений.

### Каталог существ — команды

| Модель | Команда |
|---|---|
| Тёмный Призрачный Король | `/give @s forgottenarcana:void_lich_spawn_egg{CustomModelData:331}` |
| Каменный Страж | `/give @s forgottenarcana:rune_golem_spawn_egg{CustomModelData:321}` |
| Смотрящий | `/give @s forgottenarcana:rune_golem_spawn_egg{CustomModelData:322}` |
| Глазыш | `/give @s forgottenarcana:arcane_wisp_spawn_egg{CustomModelData:311}` |
| Страшный зомби | `/give @s forgottenarcana:arcane_wisp_spawn_egg{CustomModelData:312}` |
| Монстр из колодца | `/give @s forgottenarcana:arcane_wisp_spawn_egg{CustomModelData:313}` |
| Могильщик | `/give @s forgottenarcana:arcane_wisp_spawn_egg{CustomModelData:314}` |
| Домовой | `/give @s forgottenarcana:arcane_wisp_spawn_egg{CustomModelData:315}` |
| Бледный лесовик | `/give @s forgottenarcana:arcane_wisp_spawn_egg{CustomModelData:316}` |
| Мировой червь | `/give @s forgottenarcana:arcane_wisp_spawn_egg{CustomModelData:317}` |

Фигурка меняет только внешний вид предмета; она не выдаёт новый ID яйца и не
притворяется отдельным мобом. Так не ломаются сохранения и рецепты базового мода.

### Облики посохов — команды

| Модель | Команда |
|---|---|
| Коралловый посох | `/give @s forgottenarcana:staff_sparks{CustomModelData:201}` |
| Скелетный посох | `/give @s forgottenarcana:staff_sparks{CustomModelData:202}` |
| Ледяной посох | `/give @s forgottenarcana:frost_wand{CustomModelData:203}` |
| Деревянный посох | `/give @s forgottenarcana:frost_wand{CustomModelData:204}` |
| Скипетр Локи | `/give @s forgottenarcana:void_scepter{CustomModelData:205}` |
| Скипетр Тьмы | `/give @s forgottenarcana:void_scepter{CustomModelData:206}` |

Сохранены также три прежних бонусных облика:

```mcfunction
/give @s forgottenarcana:staff_sparks{CustomModelData:101}
/give @s forgottenarcana:boss_seal{CustomModelData:102}
/give @s forgottenarcana:rune_golem_spawn_egg{CustomModelData:103}
```

## Базовое содержимое сборки

В единственном JAR находятся оба прежних мода:

- **Забытые Арканы 1.1.0** — мана-руда, Древний алтарь, магические жезлы,
  Рунный голем, Глазыш, Смотрящий и Тёмный Призрачный Король.
- **Weapon Forge 1.0.0** — 84 стихийных оружия (14 типов × 6 стихий), умения,
  комбинации и HUD.

Forge покажет в меню две записи (`forgottenarcana` и `weaponforge`) — это
нормально: технически они загружаются из одного файла.

## Пересборка и проверка

Для пересборки не нужны Java, Gradle или интернет: исходные JAR и архив моделей
уже находятся в репозитории.

```bash
python3 tools/build_nightwatch_bundle.py
```

Скрипт создаёт два идентичных файла:

- `ArcanaForge-1.20.1-v1.1.0.jar` — выпуск в корне репозитория;
- `новый мод/ArcanaForge-1.20.1-v1.1.0.jar` — файл для установки.

Во время сборки скрипт проверяет целостность ZIP, наличие обоих модов, трёх
заменённых классов моделей, ночного события, полного каталога и совпадение
контрольных копий.

## Лицензии

- Forgotten Arcana и добавленный контент — [Apache-2.0](LICENSE).
- Weapon Forge — MIT.
- Модели из `новый мод/blockbench_models_pack (1).zip` предоставлены пользователем;
  их исходники включены в JAR без изменения авторства.
