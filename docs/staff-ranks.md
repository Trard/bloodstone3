# Дополнительные ранги

Иконки используют пиксельные буквы существующих `voenkor`, `rank_production` и модераторских плашек. Фон, ступенчатые края, верхняя и нижняя обводка и тень букв повторяют оригиналы. Цвет главного военкора взят у обычного военкора; фон младшего техадминистратора на 15% темнее `rank_production`. Белые буквы не затемняются.

| Ранг | Ключ перевода | Русский символ | Английский символ |
| --- | --- | --- | --- |
| ГЛ.ВОЕНКОР | `bloodstone.suffix.head_war_correspondent` | `\uE0DE` —  | `\uE0E0` —  |
| МЛ.ТЕХ.АДМИН | `bloodstone.suffix.junior_technical_admin` | `\uE0DF` —  | `\uE0E1` —  |

Английские плашки: `H.WAR MASTER` и `JR.TECH.ADMIN`. Формулировка `WAR MASTER` сохранена из существующего перевода военкора в ресурспаке.

Для выбора языка используйте компонент `translate`, а не фиксированный символ. Например, проверка обоих рангов в чате:

```mcfunction
/tellraw @s [{"translate":"bloodstone.suffix.head_war_correspondent","color":"white"},{"text":" "},{"translate":"bloodstone.suffix.junior_technical_admin","color":"white"}]
```

Для исходных цветов плашек текстовый компонент должен быть белым. Шрифт `minecraft:default` уже подключает `minecraft:suffixes`.

Текстуры находятся в `assets/minecraft/textures/font/suffixes/ru/` и `en/`, записи шрифта — в `assets/minecraft/font/suffixes.json`, переводы — в `assets/bloodstone/lang/ru_ru.json` и `en_us.json`. У обеих иконок высота и ascent равны 7; русские размеры — 63×7 и 72×7, английские — 70×7 и 78×7.

Генератор исходных PNG:

```sh
python scripts/build_staff_rank_icons.py --output new/staff-ranks
```

Нужен Python с Pillow. Генератор создаёт четыре PNG в выбранной папке, не меняя шрифты или переводы. Для регистрации новых символов используется `scripts/add_suffix.py`.
