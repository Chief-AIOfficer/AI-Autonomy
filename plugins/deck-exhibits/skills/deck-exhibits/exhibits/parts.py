"""Структура целого: из каких частей состоит и как меняется доля."""
from .core import Fig, need, num

DARK = {'accent', 'accent_dark', 'accent_mid', 'accent_soft', 'good', 'bad'}


def seg_colors(th, names, highlight=(), dark='top'):
    """Цвета сегментов снизу вверх. Без выделения: шкала одного тона, верхний сегмент самый тёмный.
    С выделением: выделенные accent_dark/accent, остальные серые."""
    n = len(names)
    need(n <= 6, 'сегментов не больше шести; мелкие собери в «прочее»')
    if highlight:
        acc = iter(['accent_dark', 'accent', 'accent_soft'])
        greys = iter(['grey', 'grey_light', 'surface', 'grey', 'grey_light', 'surface'])
        return {nm: next(acc) if nm in highlight else next(greys) for nm in names}
    ramp = th.ramp if n > 3 else th.ramp[1:4] if n == 3 else th.ramp[2:4] if n == 2 else [th.ramp[3]]
    ramp = ramp[-n:] if n <= len(ramp) else ramp + ['grey'] * (n - len(ramp))
    if dark == 'bottom':
        ramp = ramp[::-1]
    return {nm: ramp[i] for i, nm in enumerate(names)}


def stacked_100(categories, segments, *, highlight=(), normalize=True, links=False, footer=None, decimals=0,
                height=380, head=None, theme=None, mode='показ', width=None):
    """Столбцы 100%: как меняется структура по группам или периодам. Подписи серий слева, легенды нет.

    segments: {имя: [значения по категориям]} в порядке снизу вверх.
    normalize: пересчитать в доли (для счётных данных, где сумма не 100).
    links: светлые связки между соседними столбцами для выделенных сегментов (видно, как растёт и падает доля).
    footer: {'title': 'Индекс зрелости', 'values': [1.9, 2.2, ...], 'decimals': 1} строка под столбцами.
    head: подпись над столбцами (например, «% респондентов»).
    """
    f = Fig(theme, mode, width, 'Столбцы 100%')
    names = list(segments)
    n = len(categories)
    need(2 <= n <= 8, 'столбцов 2–8')
    for k in names:
        need(len(segments[k]) == n, f'сегмент {k}: длина не совпадает с числом категорий')
    cols = seg_colors(f.th, names, highlight)
    lw = min(max(f.tw(k, 'label', 700 if k in highlight else 400) for k in names) + 30, f.w * 0.24)
    lw = max(lw, 140)
    gw = (f.w - lw) / n
    bw = min(gw * (0.62 if links else 0.6), 120)
    top = 64
    base = top + height
    tops_by = []
    for i, cat in enumerate(categories):
        cx = lw + i * gw + gw / 2
        t = f.wrap(str(cat), gw - 8, 'label', 400, 2, 'подпись столбца')
        f.text(cx, top - 18 - 18 * t.count('\n'), t, 'label', 'ink', 400, 'middle', lh=18)
        f.line(cx - bw / 2 - 6, top - 8, cx + bw / 2 + 6, top - 8, 'line_strong', 1)
        tot = sum(segments[k][i] for k in names) if normalize else 100
        y = base
        spans = {}
        for k in names:
            v = segments[k][i]
            h = height * v / tot if tot else 0
            f.rect(cx - bw / 2, y - h, bw, h, cols[k], f'{cat}, {k}: {num(v, decimals)}')
            if h >= f.s('label') + 4:
                f.text(cx, y - h / 2 + 5, num(v, decimals), 'label', 'on_dark' if cols[k] in DARK else 'ink', 400, 'middle')
            spans[k] = (y - h, y)
            y -= h
        tops_by.append(spans)
    if links:
        for i in range(n - 1):
            xa = lw + i * gw + gw / 2 + bw / 2
            xb = lw + (i + 1) * gw + gw / 2 - bw / 2
            for k in (highlight or names):
                (a0, a1), (b0, b1) = tops_by[i][k], tops_by[i + 1][k]
                f.poly([(xa, a0), (xb, b0), (xb, b1), (xa, a1)], 'accent_pale' if cols[k] != 'accent_dark' else 'grey_light')
    # подписи серий слева у первого столбца
    prev_top = base + 40
    for k in names:
        y0, y1 = tops_by[0][k]
        t = f.wrap(k, lw - 20, 'label', 700 if k in highlight else 400, 4, 'подпись сегмента')
        nl = t.count('\n') + 1
        yy = min((y0 + y1) / 2 - (nl - 1) * 9 + 5, prev_top - 8 - (nl - 1) * 18 - 4)
        f.text(0, yy, t, 'label', 'ink', 700 if k in highlight else 400, lh=18)
        prev_top = yy - 14
        if k != names[-1]:
            f.line(0, y0, lw - 12, y0, 'line', 1, '4 3')
    if head:
        f.text(0, 18, head, 'small', 'muted')
    yb = base
    if footer:
        f.line(0, base + 16, f.w, base + 16, 'line', 1)
        f.para(0, base + 44, footer['title'], lw - 16, 'label', 'ink', 700, 2, what='строка итогов', lh=18)
        for i, v in enumerate(footer['values']):
            f.text(lw + i * gw + gw / 2, base + 44, num(v, footer.get('decimals', 1)), 'label', 'ink', 400, 'middle')
        yb = base + 72
    return f.finish(yb + 6)


def share_bar(parts, *, decimals=0, highlight=None, theme=None, mode='показ', width=None):
    """Одна полоса 100% и описание под каждой частью. Для «организации делятся на три горизонта».

    parts: [('Горизонт 1: доступ', 46, 'Сотрудникам дают общие ИИ-инструменты'), ...] 2–4 части.
    """
    f = Fig(theme, mode, width, 'Полоса долей')
    need(2 <= len(parts) <= 4, 'частей 2–4; больше: stacked_100 или bar_ranked')
    tot = sum(p[1] for p in parts)
    names = [p[0] for p in parts]
    cols = seg_colors(f.th, names[::-1], [highlight] if highlight else ())
    x = 0
    bh = 40
    n = len(parts)
    colw = f.w / n
    ytxt = bh + 52
    for i, (nm, v, desc) in enumerate(parts):
        w = f.w * v / tot
        f.rect(x, 0, w - (2 if i < n - 1 else 0), bh, cols[nm], f'{nm}: {num(v, decimals)}')
        f.text(x + w / 2, bh / 2 + 6, num(v, decimals), 'label', 'on_dark' if cols[nm] in DARK else 'ink', 700, 'middle')
        tx = i * colw
        anchor_x = max(min(x + w / 2, tx + colw - 20), tx + 20)
        f.line(x + w / 2, bh + 6, x + w / 2, bh + 18, 'line_strong', 1)
        if abs(anchor_x - (x + w / 2)) > 2:
            f.line(x + w / 2, bh + 18, anchor_x, bh + 18, 'line_strong', 1)
        f.text(tx, ytxt, nm, 'label', 'ink', 700)
        f.para(tx, ytxt + 24, desc, colw - 28, 'label', 'muted', max_lines=4, what='описание части')
        x += w
    return f.finish()


def stacked_columns(categories, segments, *, totals=True, steps=None, seg_growth=None, highlight=(), decimals=0,
                    height=360, growth_title='рост за год', dark='bottom', theme=None, mode='показ', width=None):
    """Стековые столбцы по периодам: как растёт целое и из чего. Итог над столбцом, темпы между столбцами.

    segments: {имя: [значения]} снизу вверх; подписи сегментов справа от последнего столбца.
    steps: ['+15%', '+13%', ...] темп между соседними столбцами (n-1 штук), стрелка над столбцами.
    seg_growth: {имя: '+18%'} кружки темпа по сегментам справа, цвет как у сегмента.
    """
    f = Fig(theme, mode, width, 'Стековые столбцы')
    names = list(segments)
    n = len(categories)
    need(2 <= n <= 10, 'столбцов 2–10')
    cols = seg_colors(f.th, names, highlight, dark)
    right = max(f.tw(k, 'label') for k in names) + 30 + (70 if seg_growth else 0)
    pw = f.w - right
    gw = pw / n
    bw = min(gw * 0.62, 110)
    totv = [sum(segments[k][i] for k in names) for i in range(n)]
    vmax = max(totv)
    top = 40 + (60 if steps else 0)
    base = top + height
    last_spans = {}
    for i, cat in enumerate(categories):
        cx = i * gw + gw / 2
        y = base
        for k in names:
            v = segments[k][i]
            h = height * v / vmax
            f.rect(cx - bw / 2, y - h, bw, h - 1, cols[k], f'{cat}, {k}: {num(v, decimals)}')
            if h >= f.s('small') + 4:
                f.text(cx, y - h / 2 + 5, num(v, decimals), 'small', 'on_dark' if cols[k] in DARK else 'ink', 700 if cols[k] in DARK else 400, 'middle')
            if i == n - 1:
                last_spans[k] = (y - h, y)
            y -= h
        if totals:
            f.text(cx, y - 8, num(totv[i], decimals), 'label', 'ink', 700, 'middle')
        f.text(cx, base + 22, str(cat), 'label', 'muted', 400, 'middle')
    f.line(0, base, pw, base, 'line_strong', 1)
    if steps:
        need(len(steps) == n - 1, 'steps: на один меньше, чем столбцов')
        for i, s in enumerate(steps):
            x1, x2 = i * gw + gw / 2 + 10, (i + 1) * gw + gw / 2 - 10   # ноги соседних скобок не сходятся на одной вертикали
            lift = 26 if totals else 8
            y1 = base - height * totv[i] / vmax - lift
            y2 = base - height * totv[i + 1] / vmax - lift + 2
            yt = min(y1, y2) - 22
            f.elbow(x1, y1, x2, y2, yt)
            f.plate((x1 + x2) / 2, yt - 8, s, 'surface', 'ink', 'small', 6)
    lx = pw + 14
    prev = base + 60
    step = 50 if seg_growth else 20
    for k in names:
        y0, y1 = last_spans[k]
        yy = min((y0 + y1) / 2 + 5, prev - step)
        f.text(lx, yy, k, 'label', 'ink', 700 if k in highlight else 400)
        if seg_growth and k in seg_growth:
            gx = f.w - 28
            f.circle(gx, yy - 5, 22, cols[k])
            f.text(gx, yy, seg_growth[k], 'small', 'on_dark' if cols[k] in DARK else 'ink', 700, 'middle')
        prev = yy
    if seg_growth:
        f.text(f.w, min(last_spans[names[-1]][0], top) - 40, growth_title, 'small', 'muted', 700, 'end')
    return f.finish()


def breakdown_column(segments, *, col_titles=(), total_label='', unit='', compare=None, decimals=0, height=420,
                     theme=None, mode='показ', width=None):
    """Один высокий столбец, разбитый на части, и таблица частей справа. Для «рынок из чего состоит».

    segments: [('Аутсорсинг', 450, '400–500', '5–10'), ...] сверху вниз: имя, значение для высоты, колонки таблицы.
    compare: ('Продано сейчас', 145, '×10') маленький столбец слева со стрелкой-кратностью.
    """
    f = Fig(theme, mode, width, 'Столбец-разбивка')
    need(2 <= len(segments) <= 14, 'частей 2–14')
    tot = sum(s[1] for s in segments)
    x = 0
    top = 40
    bw = 110
    if compare:
        lab, v, mult = compare
        h = height * v / tot
        f.rect(x, top + height - h, bw * 0.8, h, 'grey')
        f.text(x + bw * 0.4, top + height + 24, lab, 'small', 'ink', 400, 'middle')
        f.arrow(x + bw * 0.4, top + height - h - 8, x + bw * 0.4, top + 6, 'line_strong', 1.2)
        f.text(x + bw * 0.4 + 10, top + height / 2, mult, 'big', 'ink', 700)
        x += bw * 0.8 + 90
    names = [s[0] for s in segments]
    ramp = ['accent_dark', 'accent_mid', 'accent', 'accent_soft', 'accent_light', 'accent_pale']
    y = top
    rows_y = []
    tx = x + bw + 30
    rh = min(32, (height) / len(segments))
    f.text(tx + 24, top - 14, '', 'small')
    for i, s in enumerate(segments):
        h = height * s[1] / tot
        col = ramp[min(i * len(ramp) // len(segments), len(ramp) - 1)]
        f.rect(x, y, bw, h - 1, col, f'{s[0]}: {num(s[1], decimals, unit)}')
        rows_y.append((y, y + h, col))
        y += h
    f.text(x + bw / 2, top - 10, total_label, 'label', 'ink', 700, 'middle')
    # таблица
    cw = 150
    namew = f.w - tx - 24 - cw * len(col_titles)
    for k, t in enumerate(col_titles):
        f.para(tx + 24 + namew + k * cw, top - 26, t, cw - 10, 'small', 'muted', 700, 2, what='заголовок колонки', lh=16)
    ty = top + 12
    for i, s in enumerate(segments):
        yy = ty + i * rh
        y0, y1, col = rows_y[i]
        f.rect(tx, yy - 11, 12, 12, col)
        f.para(tx + 24, yy, s[0], namew - 10, 'label', 'ink', max_lines=1, what='имя части')
        for k, v in enumerate(s[2:2 + len(col_titles)]):
            f.text(tx + 24 + namew + k * cw, yy, str(v), 'label', 'ink')
        f.line(tx, yy + rh - 20, f.w, yy + rh - 20, 'line_soft', 1)
    return f.finish(max(top + height + 40, ty + len(segments) * rh))


def nested_market(levels, *, unit='', side=None, theme=None, mode='показ', width=None):
    """Вложенные круги рынка (TAM, SAM, SOM): от всего рынка к доступной нам доле.

    levels: [('Весь рынок ИТ', 19), ('Внутренние ИТ', 5.7), ('Наш сегмент', 2.0)] от большего к меньшему; площадь ∝ значению.
    side: [('40%', 'рост рынка за 5 лет'), ...] цифры справа (до четырёх).
    """
    import math
    f = Fig(theme, mode, width, 'Вложенные круги')
    need(2 <= len(levels) <= 4, 'уровней 2–4')
    R = 200
    cx, base = 430, 2 * R + 20
    tones = ['accent_pale', 'accent_light', 'accent_soft', 'accent_dark'][-len(levels):] if len(levels) < 4 else ['accent_pale', 'accent_light', 'accent_soft', 'accent_dark']
    v0 = levels[0][1]
    radii = [R * math.sqrt(v / v0) for _, v in levels]
    for (nm, v), r, t in zip(levels, radii, tones):
        f.circle(cx, base - r, r, t)
    for i, ((nm, v), r, t) in enumerate(zip(levels, radii, tones)):
        nxt = radii[i + 1] if i + 1 < len(radii) else 0
        ty = base - 2 * r + (r - nxt) + 6 if nxt else base - r + 6
        f.text(cx, ty, num(v, 1 if v < 10 else 0, unit), 'head', 'on_dark' if t in DARK else 'ink', 700, 'middle')
        f.line(cx - r * 0.95 if not nxt else cx - math.sqrt(max(r * r - (ty - (base - r)) ** 2, 0)), ty - 6, 210, ty - 6, 'line', 1)
        f.para(0, ty - 2, nm, 200, 'small', 'ink', max_lines=3, what='имя уровня')
    if side:
        sx = cx + R + 80
        y = 40
        for big, txt in side[:4]:
            f.text(sx, y + 34, big, 'big', 'accent', 700)
            f.para(sx, y + 62, txt, f.w - sx, 'small', 'ink', max_lines=2, what='подпись цифры')
            f.line(sx, y + 88, f.w, y + 88, 'line', 1)
            y += 104
    return f.finish(max(base + 10, 40 + 104 * len(side or [])))
