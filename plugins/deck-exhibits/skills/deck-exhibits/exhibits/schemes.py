"""Схемы с текстом: выводы с иконками, столпы, рамка из блоков, резюме, доли карточками, цитаты, карточки показателей."""
from .core import Fig, need, num

DARK = {'accent', 'accent_dark', 'accent_mid', 'accent_soft', 'good', 'bad'}


def points(items, *, cols=3, icon_pos='top', style='plain', side=None, task=None, max_lines=6,
           theme=None, mode='показ', width=None):
    """Пункты с иконками: ключевые выводы, что делают лидеры, результаты исследования.

    items: [{'icon': 'trending-up', 'text': '**Растём** при сохранении маржи', 'title'?: 'Заголовок'}] 2–8 штук.
    cols: колонок; icon_pos: 'top' (иконка над текстом) или 'left' (слева, для 1–2 колонок).
    style: 'plain' (без рамок), 'rule' (тонкие вертикальные разделители), 'card' (серые карточки с полоской акцента снизу),
           'plate' (название в акцентной плашке, пояснение в серой карточке; нужен title).
    side: [('~30 млрд', 'рост устройств'), ...] тёмная колонка цифр справа (до 4).
    task: фраза-задача над пунктами в овале.
    """
    f = Fig(theme, mode, width, 'Пункты с иконками')
    f.text_scheme = True
    need(2 <= len(items) <= 8, 'пунктов 2–8; больше: разбить на два слайда или таблица')
    side_w = f.w * 0.24 if side else 0
    W = f.w - side_w - (24 if side else 0)
    gap = f.th.gap if style in ('card', 'plate') else 32
    cw = (W - gap * (cols - 1)) / cols
    y0 = 0
    if task:
        tw_ = min(f.tw(task, 'label', 700) + 60, W)
        t = f.wrap(task, tw_ - 50, 'label', 700, 2, 'фраза-задача')
        hh = 26 + 20 * (t.count('\n') + 1)
        f.rect((W - tw_) / 2, 0, tw_, hh, 'bg', stroke='line_strong', dash='2 3', rx=hh / 2)
        f.text(W / 2, 28, t, 'label', 'ink', 700, 'middle', lh=20)
        y0 = hh + 24
    rows = (len(items) + cols - 1) // cols
    pad = f.th.pad
    # высоты строк
    heights = []
    for r in range(rows):
        hmax = 0
        for it in items[r * cols:(r + 1) * cols]:
            inner = cw - (2 * pad if style in ('card', 'plate') else 0) - (52 if icon_pos == 'left' else 0)
            lines = 0
            if it.get('title'):
                lines += f.wrap(it['title'], inner, 'label', 700, 3, 'заголовок пункта').count('\n') + 1
            # тот же перенос, что при рисовании: высота строки без пустого запаса
            lines += f.rich_lines(it['text'], inner, 'label', max_lines, f'пункт «{it["text"][:40]}…» для {cols} колонок')
            hmax = max(hmax, lines)
        icon_h = 58 if icon_pos == 'top' else 0
        heights.append(icon_h + hmax * round(f.s('label') * 1.35) + (2 * pad + 16 if style in ('card', 'plate') else 10) + (24 if style == 'plate' else 0))
    y = y0
    for r in range(rows):
        rh = heights[r]
        for c, it in enumerate(items[r * cols:(r + 1) * cols]):
            x = c * (cw + gap)
            ix, iy = x, y
            inner_x, inner_w = x, cw
            if style == 'card':
                f.rect(x, y, cw, rh, 'surface', rx=4)
                f.rect(x + cw * 0.25, y + rh - 8, cw * 0.5, 4, 'accent', rx=2)
                inner_x, inner_w = x + pad, cw - 2 * pad
                iy = y + pad
            if style == 'plate':
                t = f.wrap(it.get('title', ''), cw - 2 * pad, 'label', 700, 2, 'название в плашке')
                ph = 22 + 19 * (t.count('\n') + 1)
                f.rect(x, y + 56, cw, ph, 'accent_dark')
                f.text(x + cw / 2, y + 56 + 26, t, 'label', 'on_dark', 700, 'middle', lh=19)
                f.rect(x, y + 56 + ph, cw, rh - ph - 56, 'surface')
                f.icon(it['icon'], x + cw / 2, y + 24, 34, 'accent_dark')
                f.para(x + pad, y + 56 + ph + 28, it['text'].replace('**', ''), cw - 2 * pad, 'label', 'ink', max_lines=max_lines, what='пояснение')
                continue
            if style == 'rule' and c > 0:
                # разделитель сплошной через все строки
                f.line(x - gap / 2, y, x - gap / 2, y + rh + (26 if r < rows - 1 else 0), 'line', 1)
            if icon_pos == 'top':
                if style == 'card':
                    f.icon(it['icon'], inner_x + inner_w / 2, iy + 22, 26, 'on_dark', bg='accent_dark', bg_r=24)
                else:
                    f.icon(it['icon'], inner_x + 16, iy + 18, 30, 'accent_dark')
                ty = iy + 66
                tx, tw_ = inner_x, inner_w
            else:
                f.icon(it['icon'], inner_x + 18, iy + 16, 30, 'accent_dark')
                ty = iy + 20
                tx, tw_ = inner_x + 52, inner_w - 52
            if it.get('title'):
                ty += f.para(tx, ty, it['title'], tw_, 'label', 'ink', 700, 3, what='заголовок пункта') + 8
            f.rich(tx, ty, it['text'], tw_, 'label', 'ink', max_lines=max_lines, what='текст пункта')
        y += rh + (gap if style in ('card', 'plate') else 26)
    total_h = y - (gap if style in ('card', 'plate') else 26)
    if side:
        sx = f.w - side_w
        f.rect(sx, y0, side_w, total_h - y0, 'accent_dark')
        k = len(side)
        bh = (total_h - y0 - 24) / k
        for i, (big, txt) in enumerate(side):
            by = y0 + 12 + i * bh
            f.text(sx + side_w / 2, by + bh / 2 - 6, big, 'head', 'on_dark', 700, 'middle')
            f.para(sx + side_w / 2, by + bh / 2 + 16, txt, side_w - 32, 'small', 'on_dark', max_lines=2, anchor='middle', what='подпись цифры')
            if i:
                f.line(sx + 20, by, sx + side_w - 20, by, 'accent_soft', 1)
    return f.finish(total_h + 4)


def pillars(columns, *, total=None, icon_style='ring', theme=None, mode='показ', width=None):
    """Столпы: 3–5 направлений колонками. Иконка, заголовок, текст или пункты, эффект цифрой, общий итог внизу.

    columns: [{'icon', 'title', 'text'?, 'items'?: [('Тема', 'одна строка')], 'effect'?: '+5 млн ₽', 'effect_note'?: 'эффект в год'}]
    icon_style: 'ring' (обводка) или 'solid' (тёмный круг).
    total: 'Вместе: +14 млн ₽ в год, разрыв до цели закрыт' плашка внизу.
    """
    f = Fig(theme, mode, width, 'Столпы')
    f.text_scheme = True
    n = len(columns)
    need(2 <= n <= 5, 'столпов 2–5')
    gap = f.th.gap
    cw = (f.w - gap * (n - 1)) / n
    y_title = 108
    th = max(f.wrap(c['title'], cw - 16, 'label', 700, 3, 'заголовок столпа').count('\n') + 1 for c in columns)
    y_body = y_title + th * 20 + 16
    # высоты карточек тем выравниваются по ряду
    nrow = max(len(c.get('items', [])) for c in columns)
    row_h = [0] * nrow
    for c in columns:
        for k, (a, b) in enumerate(c.get('items', [])):
            ta = f.wrap(a, cw - 28, 'label', 700, 2, 'тема столпа')
            tb = f.wrap(b, cw - 28, 'small', 400, 4, 'строка темы')
            row_h[k] = max(row_h[k], 26 + 19 * (ta.count('\n') + 1) + 18 * (tb.count('\n') + 1))
    # высота текста под заголовком: по самой длинной колонке, чтобы темы начинались с одной линии
    lh_t = round(f.s('label') * 1.3)
    text_h = max(((f.wrap(c['text'], cw - 30, 'label', 400, 5, 'текст столпа').count('\n') + 1) * lh_t + 22) if c.get('text') else 0
                 for c in columns)
    bottoms = []
    for i, c in enumerate(columns):
        x = i * (cw + gap)
        cx = x + cw / 2
        if icon_style == 'solid':
            f.icon(c['icon'], cx, 42, 40, 'on_dark', bg='accent_dark', bg_r=40)
        else:
            f.icon(c['icon'], cx, 42, 30, 'ink', ring='ink', bg_r=34)
        f.text(cx, y_title, f.wrap(c['title'], cw - 16, 'label', 700, 3, 'заголовок столпа'), 'head', 'ink', 700, 'middle', lh=20)
        y = y_body
        if c.get('text'):
            f.para(cx, y + 6, c['text'], cw - 30, 'label', 'muted', max_lines=5, anchor='middle', what='текст столпа', lh=lh_t)
        y += text_h
        for k, (a, b) in enumerate(c.get('items', [])):
            ta = f.wrap(a, cw - 28, 'label', 700, 2, 'тема столпа')
            tb = f.wrap(b, cw - 28, 'small', 400, 4, 'строка темы')
            hh = row_h[k]
            f.rect(x, y, cw, hh, 'surface')
            f.text(x + 14, y + 24, ta, 'label', 'ink', 700, lh=19)
            f.text(x + 14, y + 24 + 19 * (ta.count('\n') + 1) + 2, tb, 'small', 'ink', lh=18)
            y += hh + 8
        if c.get('effect'):
            f.text(cx, y + 26, c['effect'], 'head', 'ink', 700, 'middle')
            if c.get('effect_note'):
                f.text(cx, y + 48, c['effect_note'], 'note', 'muted', 400, 'middle')
            y += 56
        bottoms.append(y)
        if i and not c.get('items'):
            f.line(x - gap / 2, 10, x - gap / 2, max(bottoms) - 6, 'line', 1)
    y = max(bottoms) + 10
    if total:
        f.rect(0, y, f.w, 48, 'surface')
        f.text(f.w / 2, y + 30, total, 'label', 'ink', 700, 'middle')
        y += 48
    return f.finish(y + 4)


def framework(sections, *, head=('', ''), theme=None, mode='показ', width=None):
    """Рамка из блоков: разделы слева (Зачем, Что, Как), модули строками, действия справа с жирными ключами.

    sections: [{'label': 'Зачем', 'icon'?: 'compass', 'rows': [{'name': 'Таксономия рисков', 'text': '**Определить** категории…'}]}]
    Тон разделов от тёмного к светлому: что раньше и важнее, то темнее.
    head: подписи колонок (модули, действия).
    """
    f = Fig(theme, mode, width, 'Рамка из блоков')
    f.text_scheme = True
    need(1 <= len(sections) <= 5, 'разделов 1–5')
    need(sum(len(s['rows']) for s in sections) <= 9, 'строк не больше девяти')
    lw, mw = 130, f.w * 0.36
    rx = lw + 14 + mw + 30
    rw = f.w - rx
    tones = ['accent_dark', 'accent', 'accent_light', 'grey_light', 'surface']
    y = 0
    if any(head):
        f.text(lw + 14, 18, head[0], 'label', 'ink', 700)
        f.text(rx, 18, head[1], 'label', 'ink', 700)
        y = 34
    rh = 50
    for si, s in enumerate(sections):
        tone = tones[min(si, len(tones) - 1)] if len(sections) > 1 else 'accent_dark'
        n = len(s['rows'])
        f.rect(0, y, lw, n * rh - 6, tone, rx=4)
        tc = 'on_dark' if tone in DARK else 'ink'
        cy = y + (n * rh - 6) / 2
        if s.get('icon') and n == 1:
            f.icon(s['icon'], 26, cy, 20, tc)
            f.text(46, cy + 5, s['label'], 'label', tc, 700)
        elif s.get('icon'):
            f.icon(s['icon'], lw / 2, cy - 12, 22, tc)
            f.text(lw / 2, cy + 22, s['label'], 'label', tc, 700, 'middle')
        else:
            f.text(lw / 2, cy + 5, s['label'], 'label', tc, 700, 'middle')
        for r in s['rows']:
            f.rect(lw + 14, y, mw, rh - 6, 'surface', rx=(rh - 6) / 2)
            f.para(lw + 30, y + (rh - 6) / 2 + 5, r['name'], mw - 44, 'label', 'ink', 700 if si == 0 else 400, 1, what='модуль')
            nl = f.wrap(r['text'].replace('**', ''), rw, 'small', 700, 2, 'действия модуля').count('\n') + 1
            f.rich(rx, y + (rh - 6) / 2 + 5 - (nl - 1) * 19 / 2, r['text'], rw, 'small', 'ink', max_lines=2, lh=19, what='действия модуля')
            y += rh
    return f.finish(y)


def exec_summary(blocks, *, style='labels', theme=None, mode='показ', width=None):
    """Резюме для руководителя: блоки с метками слева (Ситуация, Сложность, Решение) или скобки-ярусы пирамиды справа.

    blocks: [{'label': 'Ситуация', 'lead': '**Маржа падает** третий год…', 'bullets'?: ['…', '…'], 'hl'?: True, 'aside'?: 'слайды 3–4'}]
    aside: короткая пометка в отдельной колонке справа (где это раскрыто, на каких слайдах).
    style: 'labels' метки слева и черта; 'pyramid' вывод первым, ярусы подписаны справа скобками.
    hl: блок-решение, выделяется тонкой рамкой акцента.
    """
    f = Fig(theme, mode, width, 'Резюме')
    need(2 <= len(blocks) <= 5, 'блоков 2–5')
    left = 170 if style == 'labels' else 0
    right = 200 if style == 'pyramid' else 0
    aside_w = 150 if style == 'labels' and any(b.get('aside') for b in blocks) else 0
    tw_ = f.w - left - right - aside_w - 24
    y = 4
    for b in blocks:
        y0 = y
        y += 22
        h = f.rich(left + 16, y, b['lead'], tw_, 'label', 'ink', key_color='accent_dark', max_lines=4, what='вывод блока')
        y += h + 10
        for bl in b.get('bullets', []):
            f.circle(left + 22, y - 5, 2.5, 'muted')
            y += f.rich(left + 34, y, bl, tw_ - 18, 'small', 'ink', max_lines=3, what='пункт блока') + 8
        y += 8
        if b.get('hl'):
            f.rect(left, y0 + 2, f.w - left - right, y - y0 - 2, 'none', stroke='accent', rx=2)
        if style == 'labels':
            f.text(0, y0 + 26, b['label'], 'label', 'accent_dark', 700)
            if b.get('aside'):
                f.para(f.w - aside_w + 16, y0 + 26, b['aside'], aside_w - 20, 'small', 'accent', 700, 2, what='пометка справа')
            f.line(0, y0, f.w - right, y0, 'line', 1)
        else:
            bx = f.w - right + 10
            f.line(bx, y0 + 6, bx + 8, y0 + 6, 'line_strong', 1.2)
            f.line(bx + 8, y0 + 6, bx + 8, y - 6, 'line_strong', 1.2)
            f.line(bx, y - 6, bx + 8, y - 6, 'line_strong', 1.2)
            f.line(bx + 8, (y0 + y) / 2, bx + 18, (y0 + y) / 2, 'line_strong', 1.2)
            f.text(bx + 26, (y0 + y) / 2 + 5, b['label'], 'label', 'muted', 700)
        y += 8
    return f.finish(y)


def share_cards(parts, *, center='', theme=None, mode='показ', width=None):
    """Доли усилий или бюджета карточками вокруг кольца: 70/20/10. Самая большая доля в самой большой карточке.

    parts: [(70, 'Люди и процессы', ['Вовлечь руководителей', ...]), (20, 'Данные и технологии', [...]), (10, 'ИИ', [...])]
    """
    f = Fig(theme, mode, width, 'Доли карточками')
    need(2 <= len(parts) <= 3, 'долей 2–3')
    tot = sum(p[0] for p in parts)
    cx, cy, R = f.w / 2, 190, 150
    start = 0.75 - parts[0][0] / tot / 2     # первая доля смотрит на свою карточку слева
    tones = ['accent_dark', 'accent', 'accent_light']
    for i, (v, _, _) in enumerate(parts):
        fr = v / tot
        import math
        a0 = 2 * math.pi * start - math.pi / 2
        a1 = 2 * math.pi * (start + fr) - math.pi / 2
        big = 1 if fr > 0.5 else 0
        r = R
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        f.el.append(f'<path d="M{x0:.1f},{y0:.1f} A{r},{r} 0 {big} 1 {x1:.1f},{y1:.1f}" stroke="{f.c(tones[i])}" stroke-width="34" fill="none"/>')
        start += fr
    if center:
        f.para(cx, cy - 10, center, R * 1.3, 'label', 'ink', 700, 4, anchor='middle', what='текст в кольце')
    cw = f.w / 2 - R - 50
    lx, rx_ = 0, f.w - cw
    slots = [(lx, 10), (rx_, 10), (rx_, 210)]
    for i, (v, title, items) in enumerate(parts):
        x, y = slots[i]
        y_ = y + 20
        f.text(x + 18, y_ + 32, f'{num(v)}%', 'big', tones[i] if tones[i] != 'accent_light' else 'accent_soft', 700)
        f.text(x + 18, y_ + 62, title, 'head', 'ink', 700)
        yy = y_ + 90
        for it in items:
            yy += f.para(x + 18, yy, it, cw - 36, 'small', 'ink', max_lines=2, what='пункт доли') + 12
        h = yy - y + 4
        f.el.insert(0, f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{h:.1f}" fill="{f.c("surface")}"/>')
        f._grow(y + h)
        ex = x + cw if x == lx else x
        yl = y_ + 22
        dx = (max(R * R - (yl - cy) ** 2, 0)) ** 0.5 + 20
        f.line(ex, yl, cx + (-dx if x == lx else dx), yl, tones[i] if tones[i] != 'accent_light' else 'accent_soft', 1.2)
    return f.finish()


def quotes(items, *, lead=None, theme=None, mode='показ', width=None):
    """Голос клиента: цитаты в карточках одного размера, крупная кавычка, автор должностью; вывод слева на тёмной колонке.

    items: [('Нам нужно право на ремонт…', 'Руководитель сервиса, ритейл')], 2–4 цитаты.
    lead: вывод из цитат для левой колонки.
    """
    f = Fig(theme, mode, width, 'Цитаты')
    need(2 <= len(items) <= 4, 'цитат 2–4; больше: таблица цитат в приложении')
    lw = f.w * 0.26 if lead else 0
    x0 = lw + (24 if lead else 0)
    gap = f.th.gap
    cw = (f.w - x0 - gap * (len(items) - 1)) / len(items)
    texts = [f.wrap(q, cw - 2 * f.th.pad, 'label', 400, 8, 'цитата') for q, _ in items]
    nl = max(t.count('\n') + 1 for t in texts)
    ch = 70 + nl * 21 + 50
    for i, ((q, who), t) in enumerate(zip(items, texts)):
        x = x0 + i * (cw + gap)
        f.rect(x, 0, cw, ch, 'surface')
        f.text(x + f.th.pad, 52, '«', 'big', 'accent', 700, check=False)
        f.text(x + f.th.pad, 78, t, 'label', 'ink', lh=21, italic=True)
        f.para(x + f.th.pad, ch - 20, who, cw - 2 * f.th.pad, 'note', 'muted', max_lines=1, what='автор цитаты')
    if lead:
        f.rect(0, 0, lw, ch, 'accent_dark')
        f.para(20, 36, lead, lw - 40, 'head', 'on_dark', 700, 6, what='вывод из цитат', lh=24)
    return f.finish(ch)


def kpi_cards(cards, *, theme=None, mode='показ', width=None):
    """Дашборд: 2–6 карточек показателей со спарклайном; просевший показатель выделен.

    cards: [{'name': 'Выручка', 'value': '4,2 млн ₽', 'delta': '+18% к прошлому месяцу', 'trend': [..], 'bad'?: True, 'good_is_up'?: True}]
    """
    f = Fig(theme, mode, width, 'Карточки показателей')
    n = len(cards)
    need(2 <= n <= 6, 'показателей 2–6 (Миллерд); больше: таблица')
    gap = f.th.gap
    cw = (f.w - gap * (n - 1)) / n
    h = 150
    for i, c in enumerate(cards):
        x = i * (cw + gap)
        bad = c.get('bad')
        f.rect(x, 0, cw, h, 'bad_pale' if bad else 'surface', stroke='bad' if bad else None, rx=6)
        f.text(x + 18, 28, c['name'].upper(), 'note', 'muted', 700)
        f.text(x + 18, 74, c['value'], 'big' if n <= 3 else 40 if n == 4 else 32, 'bad' if bad else 'ink', 700)
        f.para(x + 18, 98, c['delta'], cw - 36, 'small', 'bad' if bad else 'good', 700, 1, what='изменение')
        tr = c.get('trend')
        if tr:
            lo, hi = min(tr), max(tr)
            pts = [(x + 18 + (cw - 36) * k / (len(tr) - 1), 136 - 22 * ((v - lo) / (hi - lo) if hi > lo else 0.5)) for k, v in enumerate(tr)]
            f.path('M' + ' L'.join(f'{a:.1f},{b:.1f}' for a, b in pts), 'bad' if bad else 'good', 2)
    return f.finish(h + 2)


def hub(center, items, *, split=None, heads=None, theme=None, mode='показ', width=None):
    """Центр и результаты вокруг: человек или объект посередине, пункты двумя колонками, связи ортогональными линиями.

    center: {'title': 'Ты', 'sub'?: 'руководитель в поиске работы', 'icon'?: 'user'}.
    items: [{'n'?: '1', 'title': 'Роль', 'text': 'Оцениваешь, **какая роль** подходит'}] 4–10 штук; слева первые split, справа остальные.
    heads: подписи колонок над пунктами, например ('До отклика', 'После отклика').
    Связи идут от карточки к вертикальной шине и от шины к центру: косых линий нет (правило стиля v3).
    """
    f = Fig(theme, mode, width, 'Центр и результаты вокруг')
    f.text_scheme = True
    need(4 <= len(items) <= 10, 'пунктов 4–10; больше: сгруппировать по фазам или таблица')
    split = split or (len(items) + 1) // 2
    left, right = items[:split], items[split:]
    need(left and right, 'нужны пункты и слева, и справа')
    W = f.w
    cr = 86                         # радиус центра
    conn = 54                       # от шины до карточки
    bw = (W - 2 * cr - 2 * conn - 40) / 2
    pad = f.th.pad
    nw = 34                         # квадрат номера
    tx_off = pad + (nw + 12 if any(it.get('n') for it in items) else 0)
    inner = bw - tx_off - pad
    lh = round(f.s('label') * 1.35)

    def box_h(it):
        lines = 0
        if it.get('title'):
            lines += f.wrap(it['title'], inner, 'label', 700, 2, 'заголовок пункта').count('\n') + 1
        lines += f.rich_lines(it['text'], inner, 'label', 3, f'пункт «{it["text"][:40]}…»')
        return 2 * pad + lines * lh - (lh - f.s('label'))

    gap = f.th.gap
    y0 = 0
    if heads:
        y0 = 30
    hl = [box_h(it) for it in left]
    hr = [box_h(it) for it in right]
    H = max(sum(hl) + gap * (len(hl) - 1), sum(hr) + gap * (len(hr) - 1))

    def place(col, hs, x, side):
        # равные зазоры по высоте колонки
        free = H - sum(hs)
        g = free / (len(hs) - 1) if len(hs) > 1 else 0
        y = y0 + (0 if len(hs) > 1 else free / 2)
        mids = []
        for it, h in zip(col, hs):
            f.rect(x, y, bw, h, 'surface', title=it.get('title'))
            f.rect(x if side == 'L' else x + bw - 4, y, 4, h, 'accent')
            ty = y + pad + f.s('label') * 0.8
            if it.get('n'):
                f.rect(x + pad, y + pad - 2, nw, nw, 'accent_dark')
                f.text(x + pad + nw / 2, y + pad + nw / 2 + 5, str(it['n']), 'label', 'on_dark', 700, 'middle', check=False)
            tx = x + tx_off
            if it.get('title'):
                ty += f.para(tx, ty, it['title'], inner, 'label', 'ink', 700, 2, what='заголовок пункта') - f.s('label') + lh
            f.rich(tx, ty, it['text'], inner, 'label', 'ink', max_lines=3, what='текст пункта')
            mids.append(y + h / 2)
            y += h + g
        return mids

    xl = 0
    xr = W - bw
    ml = place(left, hl, xl, 'L')
    mr = place(right, hr, xr, 'R')
    cx, cy = W / 2, y0 + H / 2
    busl, busr = xl + bw + conn, xr - conn
    for m in ml:
        f.line(xl + bw, m, busl, m, 'line_strong', 1.2)
    for m in mr:
        f.line(busr, m, xr, m, 'line_strong', 1.2)
    f.line(busl, min(ml + [cy]), busl, max(ml + [cy]), 'line_strong', 1.2)
    f.line(busr, min(mr + [cy]), busr, max(mr + [cy]), 'line_strong', 1.2)
    f.line(busl, cy, cx - cr, cy, 'line_strong', 1.2)
    f.line(cx + cr, cy, busr, cy, 'line_strong', 1.2)
    f.circle(cx, cy, cr, 'accent_dark')
    yy = cy - 18 if center.get('icon') else cy - 4
    if center.get('icon'):
        f.icon(center['icon'], cx, cy - 34, 30, 'on_dark')
    f.text(cx, yy + 14, center['title'], 'head', 'on_dark', 700, 'middle')
    if center.get('sub'):
        t = f.wrap(center['sub'], 2 * cr - 34, 'small', 400, 3, 'подпись центра')
        f.text(cx, yy + 38, t, 'small', 'on_dark', 400, 'middle', lh=18)
    if heads:
        f.text(xl, 18, heads[0], 'small', 'muted', 700)
        f.text(xr + bw, 18, heads[1], 'small', 'muted', 700, 'end')
    return f.finish(y0 + H + 4)


def fan(source, items, target, *, theme=None, mode='показ', width=None):
    """Веер и сборка: из одного запроса расходятся параллельные направления, каждое копает своё, и сходятся в один итог.

    source, target: {'title': 'Запрос', 'sub'?: 'паспорт вакансии', 'icon'?: 'search'}.
    items: [{'title': 'Люди', 'text': 'заказчик роли, руководитель', 'icon'?: 'users', 'hi'?: True}] 3–10 штук.
    hi: решающие направления, полоса и её связи акцентом. Остальные серые.
    Название и описание направления в одну строку каждое: длинное падает FitError, текст сокращать.
    Связи ортогональные, общая шина слева и справа (правило стиля v3).
    """
    f = Fig(theme, mode, width, 'Веер и сборка')
    f.text_scheme = True
    need(3 <= len(items) <= 10, 'направлений 3–10; больше: сгруппировать или таблица')
    W = f.w
    nw, bus = 196, 30                 # ширина крайних узлов, плечо шины
    rh = 44 if len(items) > 6 else 52
    gap = 10 if len(items) > 6 else 12
    H = len(items) * rh + (len(items) - 1) * gap
    rx0, rx1 = nw + 2 * bus, W - nw - 2 * bus
    has_icon = any(it.get('icon') for it in items)
    tx = rx0 + (46 if has_icon else 18)
    name_w = max(f.tw(it['title'], 'label', 700) for it in items) + 28
    desc_w = rx1 - 18 - tx - name_w
    need(desc_w > 160, 'названия направлений слишком длинные: сократить')
    for it in items:
        f.wrap(it.get('text', ''), desc_w, 'label', 400, 1, f'описание «{it["title"]}»')

    def node(x, spec):
        nh = min(H, 210)
        y = (H - nh) / 2
        f.rect(x, y, nw, nh, 'accent_dark', title=spec['title'])
        cx = x + nw / 2
        yy = y + nh / 2 - 34
        if spec.get('icon'):
            f.icon(spec['icon'], cx, yy - 6, 26, 'on_dark')
            yy += 34
        f.text(cx, yy + 6, spec['title'], 'head', 'on_dark', 700, 'middle')
        if spec.get('sub'):
            f.para(cx, yy + 30, spec['sub'], nw - 28, 'small', 'on_dark', 400, 4, anchor='middle', what='подпись узла')

    node(0, source)
    node(W - nw, target)
    cy = H / 2
    mids = [k * (rh + gap) + rh / 2 for k in range(len(items))]
    bl, br = nw + bus, W - nw - bus
    f.line(nw, cy, bl, cy, 'line_strong', 1.2)
    f.line(bl, mids[0], bl, mids[-1], 'line_strong', 1.2)
    f.line(br, mids[0], br, mids[-1], 'line_strong', 1.2)
    f.arrow(br, cy, W - nw, cy, 'line_strong', 1.2, 9)
    for it, m in zip(items, mids):
        hi = bool(it.get('hi'))
        col, lw = ('accent', 2.4) if hi else ('line_strong', 1.2)
        f.line(bl, m, rx0, m, col, lw)
        f.line(rx1, m, br, m, col, lw)
        f.rect(rx0, m - rh / 2, rx1 - rx0, rh, 'accent' if hi else 'surface', title=it['title'])
        ink = 'on_dark' if hi else 'ink'
        if it.get('icon'):
            f.icon(it['icon'], rx0 + 24, m, 20, ink)
        f.text(tx, m + 5, it['title'], 'label', ink, 700)
        if it.get('text'):
            f.text(tx + name_w, m + 5, it['text'], 'label', 'on_dark' if hi else 'muted', 400)
    # акцентные отрезки шины между решающими направлениями, если они идут подряд
    hk = [k for k, it in enumerate(items) if it.get('hi')]
    if len(hk) > 1 and hk == list(range(hk[0], hk[-1] + 1)):
        f.line(bl, mids[hk[0]], bl, mids[hk[-1]], 'accent', 2.4)
        f.line(br, mids[hk[0]], br, mids[hk[-1]], 'accent', 2.4)
    return f.finish(H + 4)
