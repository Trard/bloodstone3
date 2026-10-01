# Шприц — Minecraft Java 1.21.11

Импортированы обе модели из предоставленного `шпритц (1).zip` штатным скриптом
`scripts/extract_bbmodel_1214.py` согласно `skills/bloodstone-resourcepack-tools/SKILL.md`.
Геометрия, повороты, положения предмета в руках и исходная текстура сохранены.
UV-координаты текстуры 64 × 64 преобразованы в стандартную шкалу Java 0–16.

| Вариант | `minecraft:item_model` |
| --- | --- |
| Наполненный шприц | `bloodstone:tools/syringe/default/syringe` |
| Пустой шприц | `bloodstone:tools/syringe/default/syringe_empty` |

Наполненный вариант соответствует второй модели архива: поршень поднят, внутри
есть объём жидкости. Пустой вариант соответствует первой модели: поршень опущен,
высота жидкости равна нулю. Оба PNG из архива идентичны, поэтому модели используют
одну текстуру `bloodstone:item/tools/syringe/default/syringe`.

Базовый предмет — `minecraft:carrot_on_a_stick`; CustomModelData — **21011**
(первое значение списка `floats`). Плагин должен дополнительно ставить явный
`minecraft:item_model`, чтобы выбор модели не зависел от переопределений базового
предмета в других ресурс-паках. В этом паке также есть резервное сопоставление
CustomModelData 21011 с наполненным шприцем. Значения ниже 21011 и начиная с 21012
используют обычную ванильную модель.

Команды для проверки внешнего вида (без функционала плагина):

```mcfunction
/give @s minecraft:carrot_on_a_stick[minecraft:item_model="bloodstone:tools/syringe/default/syringe",minecraft:custom_model_data={floats:[21011.0f]}]
/give @s minecraft:carrot_on_a_stick[minecraft:item_model="bloodstone:tools/syringe/default/syringe_empty"]
/give @s minecraft:carrot_on_a_stick[minecraft:custom_model_data={floats:[21011.0f]}]
```

Все текстуры находятся в `textures/item/` и попадают в отдельный атлас предметов
1.21.11. Структура атласа и ванильный fallback проверены по официальному клиентскому
JAR 1.21.11 (SHA-1 `ba2df812c2d12e0219c489c4cd9a5e1f0760f5bd`). Структурная проверка
проверяет ссылки, границы UV, сохранение геометрии/текстуры и выбор CustomModelData;
визуальная проверка внутри Minecraft остаётся отдельным шагом.

Источники формата:

- [Minecraft 1.21.11: формат ресурс-пака 75.0 и отдельный атлас предметов](https://www.minecraft.net/en-us/article/minecraft-java-edition-1-21-11)
- [Minecraft 1.21.4: item model и CustomModelData floats](https://www.minecraft.net/en-us/article/minecraft-java-edition-1-21-4)
