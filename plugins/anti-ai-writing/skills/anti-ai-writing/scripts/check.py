#!/usr/bin/env python3
"""Механическая проверка русского текста по стандарту anti-ai-writing.

Ловит то, что надёжно ловится правилами: длинное тире, знак тире и кавычек
не своего канала, плотность тире, жёсткие запреты SKILL.md §3, жирные
«Термин:» в списках, рубленые фрагменты, ровный ритм, Title Case в заголовках.
Смысловые паттерны (пустой образ, выдуманная связь, ответ не тому читателю)
остаются за чтением.

    python3 check.py файл.md --channel post
    echo "текст" | python3 check.py - --channel docx
    python3 check.py файл.md --channel report --json

Код выхода: 0 нет ошибок, 1 есть ошибки (предупреждения код не меняют), 2 сбой запуска.
"""

import argparse
import json
import re
import sys

# Запрещённые знаки как объект проверки (emdash-ok): U+2014, U+2015, U+2E3A, U+2E3B
EM_DASHES = "".join(chr(c) for c in (0x2014, 0x2015, 0x2E3A, 0x2E3B))
EN_DASH = chr(0x2013)
LEFT_CURLY, RIGHT_CURLY, LOW_QUOTE = chr(0x201C), chr(0x201D), chr(0x201E)

AUTHORED = {"post", "chat", "email", "comment"}
EDITED = {"docx", "article", "deck", "report", "landing", "pdf"}
CHANNELS = sorted(AUTHORED | EDITED)

# Явные границы слова для кириллицы: надёжнее \b на склейках с цифрами и дефисом
L = r"(?<![А-Яа-яЁёA-Za-z])"
R = r"(?![А-Яа-яЁёA-Za-z])"

HARD_BANS = [
    ("пустой контраст", L + r"[Нн]е просто " + r"[^.!?\n]{1,60}?,\s*(?:а|это)" + R),
    ("пустой контраст", L + r"[Нн]е только" + R + r"[^.!?\n]{1,80}?" + L + r"но и" + R),
    ("пустой контраст", r"(?:^|[.!?]\s+)[Ээ]то не [^.!?\n]{1,50}?[,.]\s*[Ээ]то" + R),
    ("пустой контраст", L + r"[Дд]ело не в" + R),
    ("подводка", L + r"(?:[Сс]тоит|[Вв]ажно|[Нн]ельзя не|[Сс]ледует) (?:отметить|понимать|помнить|подчеркнуть|учитывать)" + R),
    ("подводка", L + r"(?:[Нн]еобходимо понимать|[Мм]ожно с уверенностью сказать)" + R),
    ("пустое открытие", L + r"(?:[Вв] современном мире|[Нн]а сегодняшний день|[Вв] эпоху|[Нн]е секрет,? что)" + R),
    ("пустое открытие", r"(?:^|[.!?]\s+)[Вв] условиях [а-яё]+(?:ой|ей|ых|их|ого|его) [а-яё]+"),
    ("анонс", L + r"[Дд]авайте (?:разберёмся|разберемся|рассмотрим|погрузимся|посмотрим)" + R),
    ("анонс", L + r"(?:[Пп]огрузимся в|[Вв]от что нужно знать|самое интересное)" + R),
    ("пересказ в конце", L + r"(?:[Пп]одводя итог|[Вв] заключение|[Рр]езюмируя)" + R),
    ("пересказ в конце", r"(?:^|[.!?]\s+)Таким образом,"),
    ("раздувание значимости", L + r"игра(?:ет|ют|л|ла|ли) (?:ключевую|важную|решающую|значительную|важнейшую) роль" + R),
    ("раздувание значимости", L + r"(?:является ключевым|нельзя переоценить|трудно переоценить)" + R),
    ("маркетинговый штамп", L + r"раскры(?:ть|вает|вают|ет|ют) (?:свой |ваш |весь )?потенциал" + R),
    ("маркетинговый штамп", L + r"(?:на новый уровень|мощный инструмент)" + R),
    ("маркетинговый штамп", L + r"открыва(?:ет|ют) новые (?:горизонты|возможности|перспективы)" + R),
    ("маркетинговый штамп", L + r"[Кк]омплексн(?:ый|ого|ое|ым|ом) (?:подход|решени)"),
    ("«данный»", L + r"[Дд]анн(?:ый|ая|ое|ого|ой|ому|ом|ую)" + R),
    ("обвязка чата", L + r"[Вв]от (?:вариант|пример|текст|черновик|версия)[^\n.]{0,30}:"),
    ("обвязка чата", L + r"(?:[Оо]тличный вопрос|[Кк]онечно!|[Нн]адеюсь,? (?:это )?(?:было )?(?:полезно|помог))"),
    ("обвязка чата", L + r"[Ее]сли (?:нужно|хотите),? (?:я )?могу" + R),
    ("обвязка чата", r"\[(?:Имя|имя|Название|название|Компания|компания)\]"),
    ("самомаркировка честности", L + r"(?:[Чч]естн(?:ый|ое|ая) (?:разбор|мнение|ответ|список)|[Сс]кажу (?:прямо|честно|без прикрас)|[Бб]уду (?:откровенен|честен)|без воды|[Дд]авайте честно)" + R),
    ("размытый авторитет", L + r"(?:[Ээ]ксперты|[Аа]налитики|[Сс]пециалисты|[Ии]сследователи) (?:отмечают|считают|сходятся|уверены|прогнозируют|подчёркивают)" + R),
    ("размытый авторитет", L + r"(?:[Ии]сследования показывают|[Пп]о мнению (?:экспертов|аналитиков|специалистов))" + R),
    ("текст про сам текст", L + r"(?:[Тт]аблица|[Сс]хема|[Сс]писок|[Гг]рафик) ниже (?:сравнивает|показывает|содержит|приводит)" + R),
    ("текст про сам текст", L + r"(?:[Вв] этом разделе (?:мы )?(?:рассмотрим|разберём|разберем)|собраны из открытых источников|неподтверждённое помечено|не удалось подтвердить, помечено)"),
    ("концовка-кивок", L + r"(?:[Ээ]то наглядно (?:показывает|демонстрирует)|[Вв]ывод очевиден|[Ээ]то и есть главное)" + R),
]

# Формулы деловой переписки, которые раздражают адресата (references/business-letter.md).
# Предупреждения, только для канала email.
EMAIL_FORMULAS = [
    (L + r"[Дд]оброго времени суток", "шаблонное приветствие; «Здравствуйте» или «Добрый день»"),
    (L + r"[Уу]важаемые коллеги", "обращение ко всем сразу; имена или «Здравствуйте»"),
    (L + r"[Зз]аранее (?:спасибо|благодар)", "давит на адресата; благодарить после помощи"),
    (L + r"(?:[Дд]овожу|[Дд]оводим) до (?:вашего|Вашего) сведения|[Оо]бращаем (?:ваше|Ваше) внимание|[Нн]астоящим (?:сообщаю|уведомляю)", "канцелярское вступление; сразу суть"),
    (L + r"[Уу]бедительн(?:ая|о) просьб", "приказ под видом просьбы; «пожалуйста» и срок"),
    (r"(?:^|[^А-Яа-яЁёA-Za-z])(?:ASAP|АСАП)" + R + "|" + L + r"(?:[Сс]рочно!|нужно вчера|[Гг]орит!)", "срочность без срока; дата или время и причина"),
    (L + r"(?:одним глазком|дело на пять минут)", "преуменьшение объёма работы"),
    (L + r"[Яя] (?:вас|тебя) услышал", "звучит как «ваше мнение мне безразлично»"),
    (L + r"[Пп]риносим (?:свои )?извинения за (?:доставленные|возможные) неудобства", "отписка; одно извинение своими словами и решение"),
    (L + r"(?:[Нн]адеюсь|[Нн]адеемся) на (?:ваш |Ваш )?положительный ответ|[Сс] надеждой на (?:скорейший ответ|дальнейшее сотрудничество)", "давление в концовке; следующий шаг или ничего"),
    (L + r"[Сс] заботой о (?:вас|Вас|вашем|Вашем)", "пустая формула заботы"),
    (L + r"[Вв]ы ведь профессионал|[Уу]верен,? (?:для вас|что для вас) это не (?:проблема|составит труда)", "давление через похвалу"),
]

COPULA = re.compile(L + r"(?:[Яя]вляется|[Яя]вляются|[Пп]редставля(?:ет|ют) собой|[Вв]ыступа(?:ет|ют) в качестве)" + R)
SPACED_HYPHEN = re.compile(r"(?<=\S) - (?=\S)")
SPACED_EN = re.compile(r"(?<=\S) " + EN_DASH + r" (?=\S)")
SEMANTIC_DASH = re.compile(r"(?<=\S) [-" + EN_DASH + EM_DASHES + r"] (?=\S)")
BOLD_LABEL = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\*\*[^*\n]{1,60}?(?::\*\*|\*\*\s*:)")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
HEADING = re.compile(r"^\s*#{1,6}\s+(.+?)\s*#*\s*$")
EMOJI_START = re.compile(r"^\s*(?:[-*+]\s+)?[\U0001F300-\U0001FAFF☀-➿⭐]")
QUOTED = re.compile(r"«[^»\n]*»|\"[^\"\n]*\"|" + LOW_QUOTE + "[^\n" + LEFT_CURLY + "]*" + LEFT_CURLY)
CYRILLIC = re.compile(r"[А-Яа-яЁё]")
WORD = re.compile(r"[А-Яа-яЁёA-Za-z0-9]+(?:-[А-Яа-яЁёA-Za-z0-9]+)*")


def clean_lines(text):
    """Строки текста без зон, которые не правятся: frontmatter, блоки кода,
    инлайн-код, адреса ссылок, цитаты (строки с «>»). Нумерация строк сохраняется."""
    lines = text.split("\n")
    out = []
    in_code = False
    in_front = bool(lines) and lines[0].strip() == "---"
    for i, line in enumerate(lines):
        if in_front:
            out.append("")
            if i > 0 and line.strip() == "---":
                in_front = False
            continue
        if line.strip().startswith("```"):
            in_code = not in_code
            out.append("")
            continue
        if in_code or line.lstrip().startswith(">"):
            out.append("")
            continue
        line = re.sub(r"`[^`]*`", " ", line)
        line = re.sub(r"\[\[[^\]]*\]\]", " ", line)
        line = re.sub(r"\]\([^)]*\)", "]", line)
        line = re.sub(r"https?://\S+", " ", line)
        out.append(line)
    return out


def snippet(line, start, end, pad=25):
    a = max(0, start - pad)
    b = min(len(line), end + pad)
    return ("…" if a else "") + line[a:b].strip() + ("…" if b < len(line) else "")


def split_sentences(text):
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?…])\s+(?=[А-ЯЁA-Z0-9«\"])", text)
    return [p.strip() for p in parts if p.strip()]


def paragraphs_of(lines):
    """Абзацы как (номер первой строки, текст); заголовки и пустые строки делят абзацы."""
    out, cur, start = [], [], None
    for n, line in enumerate(lines, 1):
        if line.strip() and not HEADING.match(line):
            if start is None:
                start = n
            cur.append(line)
        elif cur:
            out.append((start, " ".join(cur)))
            cur, start = [], None
    if cur:
        out.append((start, " ".join(cur)))
    return out


# Правила, которые не применяются в жанрах, где канцелярит это норма (SKILL.md §1)
GENRE_EXEMPT = {
    "legal": {"«данный»", "«является»", "пересказ в конце"},
    "academic": {"«данный»", "«является»", "пересказ в конце"},
}


def check(text, channel, genre=None):
    findings = []
    exempt = GENRE_EXEMPT.get(genre, set())

    def add(level, line_no, rule, message, frag=""):
        if rule in exempt:
            return
        findings.append({"level": level, "line": line_no, "rule": rule, "message": message, "fragment": frag})

    lines = clean_lines(text)
    authored = channel in AUTHORED
    russian = bool(CYRILLIC.search(text))

    # Тире и кавычки
    ascii_pairs = guillemets = 0
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        for m in re.finditer("[" + EM_DASHES + "]", line):
            add("error", n, "длинное тире", "длинного тире нет нигде; знак канала по §4 или перестройка", snippet(line, m.start(), m.end()))
        prose = LIST_ITEM.sub("", line, count=1)
        if authored:
            for m in SPACED_EN.finditer(prose):
                add("error", n, "тире не своего канала", "в авторском канале смысловое тире пишется дефисом с пробелами", snippet(prose, m.start(), m.end()))
        else:
            for m in SPACED_HYPHEN.finditer(prose):
                add("warning", n, "тире не своего канала", "в отредактированном документе смысловое тире пишется en dash с пробелами", snippet(prose, m.start(), m.end()))
        if russian:
            for m in re.finditer("[" + LEFT_CURLY + RIGHT_CURLY + "]", line):
                # „лапки“ внутри ёлочек законны: закрывающая “ после „ пропускается
                if line[m.start()] == LEFT_CURLY and LOW_QUOTE in line[: m.start()]:
                    continue
                add("error", n, "фигурные кавычки", "в русском тексте фигурных кавычек нет; ёлочки или прямые по каналу", snippet(line, m.start(), m.end()))
        ascii_pairs += len(re.findall(r'"[^"\n]{1,200}"', prose))
        guillemets += prose.count("«")
        if authored and "«" in prose:
            i = prose.index("«")
            add("warning", n, "кавычки не своего канала", 'в авторском канале кавычки прямые " "', snippet(prose, i, i + 1))
    if not authored and russian and ascii_pairs:
        add("warning", 0, "кавычки не своего канала", f"в отредактированном документе нужны ёлочки, прямых пар кавычек: {ascii_pairs}")
    if ascii_pairs and guillemets:
        add("warning", 0, "разнобой кавычек", "в одном тексте и ёлочки, и прямые кавычки")

    # Плотность тире
    paragraphs = paragraphs_of(lines)
    counts = [(s, len(SEMANTIC_DASH.findall(LIST_ITEM.sub("", p)))) for s, p in paragraphs]
    total = sum(k for _, k in counts)
    heavy = [(s, k) for s, k in counts if k >= 2]
    n_sent = sum(len(split_sentences(p)) for _, p in paragraphs) or 1
    if len(heavy) >= 2 or (total >= 4 and total / n_sent > 0.3):
        where = ", ".join(f"строка {s} ({k})" for s, k in heavy[:5])
        msg = f"смысловых тире {total} на {n_sent} предложений"
        if where:
            msg += f"; абзацы с двумя и больше: {where}"
        add("warning", 0, "плотность тире", msg + ". Сначала переписать часть через двоеточие, запятую, точку")

    # Жёсткие запреты. Оборот в кавычках это упоминание, а не употребление: пропускается
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        quoted = [m.span() for m in QUOTED.finditer(line)]
        for rule, pattern in HARD_BANS:
            for m in re.finditer(pattern, line):
                pos = m.start() + len(m.group(0)) - len(m.group(0).lstrip(" .!?"))
                if any(a < pos < b for a, b in quoted):
                    continue
                add("error", n, rule, "жёсткий запрет §3", snippet(line, m.start(), m.end()))

    # Раздражающие формулы деловой переписки
    if channel == "email":
        for n, line in enumerate(lines, 1):
            if not line.strip():
                continue
            quoted = [m.span() for m in QUOTED.finditer(line)]
            for pattern, why in EMAIL_FORMULAS:
                for m in re.finditer(pattern, line):
                    if any(a <= m.start() < b for a, b in quoted):
                        continue
                    add("warning", n, "формула переписки", why, snippet(line, m.start(), m.end()))

    # «Является» и родня: не чаще раза на 500 слов
    words = len(WORD.findall(" ".join(lines)))
    copulas = [n for n, line in enumerate(lines, 1) for _ in COPULA.finditer(line)]
    if copulas and len(copulas) > max(1, words // 500):
        add("warning", copulas[0], "«является»", f"связок «является / представляет собой» {len(copulas)} на {words} слов; норма не чаще раза на 500")

    # Жирные «Термин:» в списках
    labels = [n for n, line in enumerate(lines, 1) if BOLD_LABEL.match(line)]
    if len(labels) >= 2:
        add("warning", labels[0], "список «Термин: описание»", f"пунктов с жирным ярлыком и двоеточием: {len(labels)}; пункты обычными фразами или проза")

    # Эмодзи в начале пунктов и абзацев
    emoji_lines = [n for n, line in enumerate(lines, 1) if EMOJI_START.match(line)]
    if len(emoji_lines) >= 2:
        add("warning", emoji_lines[0], "эмодзи как структура", f"строк, начинающихся с эмодзи: {len(emoji_lines)}")

    # Заголовки в Title Case
    for n, line in enumerate(lines, 1):
        m = HEADING.match(line)
        if not m:
            continue
        ws = [w for w in WORD.findall(m.group(1)) if CYRILLIC.search(w) and len(w) > 3]
        if len(ws) >= 2 and all(w[0].isupper() and not w.isupper() for w in ws):
            add("warning", n, "Title Case", "в русских заголовках с заглавной только первое слово и имена", m.group(1))

    # Ритм: рубленые фрагменты и ровная длина
    for start, para in paragraphs:
        if LIST_ITEM.match(para):
            continue
        sents = split_sentences(para)
        lens = [len(WORD.findall(s)) for s in sents]
        run = 0
        for i, k in enumerate(lens):
            short = 1 <= k <= 3 and not sents[i].endswith(("?", "!"))
            run = run + 1 if short else 0
            if run == 3:
                add("warning", start, "рубленые фрагменты", "три и больше предложений по 1-3 слова подряд", " ".join(sents[i - 2 : i + 1]))
        for i in range(len(lens) - 3):
            win = lens[i : i + 4]
            if min(win) >= 8 and max(win) - min(win) <= 3:
                add("warning", start, "ровный ритм", f"четыре предложения подряд почти одной длины ({', '.join(map(str, win))} слов)", sents[i][:60] + "…")
                break

    findings.sort(key=lambda f: (f["level"] != "error", f["line"]))
    return findings


def main(argv=None):
    p = argparse.ArgumentParser(description="Механическая проверка русского текста по стандарту anti-ai-writing")
    p.add_argument("path", help="файл или - для stdin")
    p.add_argument("--channel", required=True, choices=CHANNELS,
                   help="авторские: post, chat, email, comment; отредактированные: docx, article, deck, report, landing, pdf")
    p.add_argument("--genre", choices=sorted(GENRE_EXEMPT), help="legal или academic: не считать «данный», «является», «таким образом», это норма жанра")
    p.add_argument("--json", action="store_true", help="вывод в JSON")
    a = p.parse_args(argv)
    try:
        if a.path == "-":
            text = sys.stdin.read()
        else:
            with open(a.path, encoding="utf-8") as f:
                text = f.read()
    except OSError as e:
        print(f"не удалось прочитать {a.path}: {e.strerror}", file=sys.stderr)
        return 2
    findings = check(text, a.channel, a.genre)
    errors = sum(f["level"] == "error" for f in findings)
    if a.json:
        print(json.dumps({"channel": a.channel, "errors": errors, "warnings": len(findings) - errors,
                          "findings": findings}, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            where = f"строка {f['line']}" if f["line"] else "весь текст"
            mark = "ОШИБКА" if f["level"] == "error" else "внимание"
            frag = f": {f['fragment']}" if f["fragment"] else ""
            print(f"{where}: [{mark}] {f['rule']}. {f['message']}{frag}")
        print(f"Замечаний: {len(findings)} (ошибок {errors}, предупреждений {len(findings) - errors}). Канал: {a.channel}.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
