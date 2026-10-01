# AI-Autonomy: скиллы Claude Code

Набор скиллов для [Claude Code](https://code.claude.com), которые помогают работать с ИИ самостоятельно и надёжно: исследовать тему, проверять факты, собирать результат в понятный документ. Устроен как маркетплейс плагинов: подключаете один раз, ставите нужные скиллы, обновления приходят штатно.

## Подключение

В Claude Code:

```
/plugin marketplace add Chief-AIOfficer/AI-Autonomy
/plugin install deep-research@ai-autonomy
/plugin install anti-ai-writing@ai-autonomy
```

Или из терминала:

```bash
claude plugin marketplace add Chief-AIOfficer/AI-Autonomy
claude plugin install deep-research@ai-autonomy
claude plugin install anti-ai-writing@ai-autonomy
```

Обновить: в терминале `claude plugin marketplace update ai-autonomy`, затем `claude plugin update <скилл>@ai-autonomy` и перезапустить Claude Code. Первая команда только обновляет каталог, вторая ставит новую версию скилла.

## Скиллы

| Скилл | Что делает |
|---|---|
| [deep-research](plugins/deep-research/skills/deep-research/README.md) | Исследование по вопросу: бриф, параллельный сбор источников, независимая проверка каждого несущего утверждения, отчёт в Markdown и HTML с честным «не найдено этим поиском» там, где данных нет |
| [anti-ai-writing](plugins/anti-ai-writing/skills/anti-ai-writing/README.md) | Русский текст без нейросетевой манеры: убирает канцелярит, пустые контрасты и обвязку чата, ставит тире и кавычки по каналу набора, не выдумывает факты при правке и не подменяет голос автора |

## Требования

Claude Code и Python 3.9 или новее. Сторонние библиотеки не нужны.

## Автор и лицензия

Александр Ульянов. Лицензия MIT (файл `LICENSE`): можно использовать, менять и распространять, в том числе в коммерческой работе, сохраняя указание автора. Вопросы и предложения через Issues.
