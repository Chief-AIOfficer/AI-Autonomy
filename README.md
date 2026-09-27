# AI-Autonomy: скиллы Claude Code

Набор скиллов для [Claude Code](https://code.claude.com), которые помогают работать с ИИ самостоятельно и надёжно: исследовать тему, проверять факты, собирать результат в понятный документ. Устроен как маркетплейс плагинов: подключаете один раз, ставите нужные скиллы, обновления приходят штатно.

## Подключение

В Claude Code:

```
/plugin marketplace add Chief-AIOfficer/AI-Autonomy
/plugin install deep-research@ai-autonomy
```

Или из терминала:

```bash
claude plugin marketplace add Chief-AIOfficer/AI-Autonomy
claude plugin install deep-research@ai-autonomy
```

Обновить: `/plugin marketplace update ai-autonomy`.

## Скиллы

| Скилл | Что делает |
|---|---|
| [deep-research](plugins/deep-research/skills/deep-research/README.md) | Исследование по вопросу: бриф, параллельный сбор источников, независимая проверка каждого несущего утверждения, отчёт в Markdown и HTML с честным «не найдено этим поиском» там, где данных нет |

## Требования

Claude Code и Python 3.9 или новее. Сторонние библиотеки не нужны.

## Автор и лицензия

Александр Ульянов. Лицензия MIT (файл `LICENSE`): можно использовать, менять и распространять, в том числе в коммерческой работе, сохраняя указание автора. Вопросы и предложения через Issues.
