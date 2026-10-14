# Тепловая сетка (`heat_grid`)

> Собрано `build_docs.py` из `catalog.py` и кода функции. Руками не править.

**Что говорит слайд.** Много объектов по нескольким показателям: цвет вместо чисел, группы колонок.

**Брать, когда в ТЗ:** «рейтинг городов по критериям», «архетипы», 10–40 объектов × 3–12 показателей.

**Не брать, если:** объектов меньше 6 (table); нужны точные числа (table).

**Данные на вход:** metrics, items, values {item: [..]}, groups, total.

**Потолки:** колонок до 40, строк до 12.

**Типы сообщения:** Оценка вариантов.

## Правила оформления

- Шкала одного тона из темы, легенда одной строкой внизу.
- Итоговая оценка столбиками над сеткой.

## Вызов

```python
import sys; sys.path.insert(0, SKILL_DIR)   # SKILL_DIR: папка скилла, см. SKILL.md
import exhibits as X
ex = X.heat_grid(metrics, items, values, *, groups=None, total=None, scale=(1, 10), legend_steps=5, rotate=None, decimals=1, theme=None, mode='показ', width=None)
ex.svg        # строка SVG, ширина 1168 px при 1:1 со слайдом 1280×720
ex.warnings   # наложения, выход за край, мелкий кегль: пусто = чисто
```

## Параметры (из кода)

```
Тепловая сетка точками: объекты в колонках, показатели в строках, цвет вместо чисел.

metrics: имена строк; items: имена колонок; values: {item: [значение по metrics]}.
groups: [('Лидеры инноваций', ['Утрехт', 'Хельсинки']), ...] шапки групп над колонками.
total: {item: число} строка итоговой оценки столбиками сверху.
rotate: подписи колонок вертикально (по умолчанию, если не влезают).
```

## Пример

`heat_grid` (кадр: `python3 tests/demo.py heat_grid`)

```python
def heat_grid():
    import random
    random.seed(5)
    groups = [('Лидеры', ['Казань', 'Москва', 'Тюмень', 'Сочи']), ('Догоняющие', ['Пермь', 'Уфа', 'Самара', 'Омск']),
              ('Отстающие', ['Чита', 'Курган', 'Иваново', 'Тамбов'])]
    items = [i for _, its in groups for i in its]
    metrics = ['Транспорт', 'Цифровые услуги', 'Безопасность', 'Экология', 'Жильё']
    base = {i: 8.5 - 2.5 * k for k, (_, its) in enumerate(groups) for i in its}
    vals = {i: [max(1, min(10, base[i] + random.uniform(-1.5, 1.5))) for _ in metrics] for i in items}
    tot = {i: sum(v) / len(v) for i, v in vals.items()}
    return X.heat_grid(metrics, items, vals, groups=groups, total=tot)
```

## Образцы (публичные слайды, описаны словами)

- `C_scorecard_06` BCG 2026: Тепловая матрица точками по группам городов. Шесть групп колонками, в каждой пять городов, столбик общей оценки над строкой и круги по шести показателям, светлый к тёмному. Цвет вместо чисел, легенда одной строкой внизу.
  смотреть: https://www.bcg.com/publications/2026/the-global-champions-of-urban-mobility

## Антипримеры («Не то»)

- `C_scorecard_02` McKinsey 2026: Тепловая таблица статуса. Сетка страна × показатель в трёх состояниях: голубое улучшение, серое ухудшение, белое без изменений. Легенда сверху справа, группы показателей разделены линией.
  смотреть: https://www.mckinsey.com/featured-insights/future-of-asia/southeast-asia-quarterly-economic-review
