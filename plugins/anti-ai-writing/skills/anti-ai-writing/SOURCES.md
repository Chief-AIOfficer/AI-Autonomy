# Источники

## Скиллы и инструменты, из которых взяты идеи

Все под лицензией MIT. Формулировки переписаны на русский и под русский язык, примеры свои, кроме оговорённых.

- [blader/humanizer](https://github.com/blader/humanizer), v3.1.0. Объяснение, почему модель так пишет; порядок паттернов по силе и пометка «слабый»; концовки-кивки, спор с пустотой, текст про сам текст, ответ не тому читателю (пример в каталоге п. 34 переложен с английского), заголовок, повторённый первой фразой.
- [ilyautov/humanizer-ru](https://github.com/ilyautov/humanizer-ru), v3.31.3. Правило «удаляй, не дописывай» и замер «добавь голос» (195 слепых оценок, сентябрь 2026); факт-замок и соединительная ткань; сверка с исходником и бриф свежей вычитки; жанровые поправки (замер на AINL-Eval 2025, 35 158 аннотаций); самомаркировка честности, неодушевлённый деятель, пустой образ, псевдотерапия, швы правки, непроверяемая точность, разнобой числовых форматов; список «не маркеров».
- [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing). Список «чего не вставлять никогда» (ограничения на редактора, а не детекции текста); защищённые зоны.
- [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop). Финальный вопрос самопроверки «узнает ли автор свой текст».
- [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop). Тест на переносимость фразы в чужой текст.
- [mandakan/llm-slop-detector](https://github.com/mandakan/llm-slop-detector), пакет claudeisms. Английские тики Claude (держатся как гипотеза: исходный отчёт не найден).

## Данные и исследования

- Wikipedia: [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), WikiProject AI Cleanup. Основа английского слоя и эр лексики.
- Kobak et al., «Delving into LLM-assisted writing in biomedical publications», Science Advances, 2025 ([arXiv:2406.07016](https://arxiv.org/abs/2406.07016)). Смена словаря моделей.
- Pangram, [замер Claude Opus 5.5 против Opus 5](https://www.pangram.com/es/blog/can-pangram-detect-opus-5-5) (вендор детектора). Сдвиги в «in short», «for example», списках и длине предложений.
- Liang et al., «GPT detectors are biased against non-native English writers», Patterns, 2023. Ложные срабатывания на неносителях (до 61% на эссе TOEFL).
- Jabarian & Imas, «Artificial Writing and Automated Detection», BFI Working Paper, 2025. Точность детекторов.
- [arXiv:2603.27006](https://arxiv.org/abs/2603.27006). Плотность тире как сигнатура конкретной модели, а не любого ИИ.
- Справочная служба русского языка, [«Дефис и тире: как выбрать знак»](https://gramota.ru/journal/stati/pravila-i-normy/defis-i-tire-kak-vybrat-i-postavit-pravilnyy-znak-v-tekste); Мильчин, Чельцова, «Справочник издателя и автора». Норма тире в русской типографике (стандарт сознательно отходит от неё: длинное тире не ставится, см. CHANGELOG 3.0.0).
