"""Разница: мост изменений, пара с разницей, разрыв до цели, две группы по показателям, гантели."""
from .core import Fig, need, num


def waterfall(start, steps, end=None, *, unit='', decimals=0, highlight=(), notes=None, height=330, axis='auto',
              theme=None, mode='показ', width=None):
    """Мост: из чего сложилась разница между двумя числами.

    start: ('Маржа 2025', 18.4); steps: [('Цены', +2.1), ('Объём', +1.3), ('Себестоимость', -0.9)];
    end: ('Маржа 2026', 20.9) или None (посчитается). Шаг ('Итог 1П', None) рисует промежуточный итог.
    highlight: шаги, о которых заголовок; остальные приращения серые. Без highlight рост accent, падение bad.
    notes: {шаг: текст} выноска под крупнейшими шагами (не больше двух).
    axis: 'auto' обрезает ось со знаком разрыва, если размах шагов меньше половины базы; 'zero' всегда от нуля.
    """
    f = Fig(theme, mode, width, 'Мост изменений')
    need(1 <= len(steps) <= 8, f'шагов 1–8, пришло {len(steps)}; мелкие объедини в «прочее»')
    total = start[1] + sum(v for _, v in steps if v is not None)
    if end is None:
        end = ('Итог', total)
    need(abs(end[1] - total) < 10 ** -(decimals) * 0.6 + 1e-9,
         f'мост не сходится: {start[1]} + шаги = {total:.4f}, а конец {end[1]}')
    if notes:
        need(len(notes) <= 2, 'выносок под мостом не больше двух')
    bars = [(start[0], 0, start[1], 'total')]
    run = start[1]
    for lab, v in steps:
        if v is None:
            bars.append((lab, 0, run, 'sub'))
            continue
        bars.append((lab, run, run + v, 'up' if v >= 0 else 'down'))
        run += v
    bars.append((end[0], 0, end[1], 'total'))
    n = len(bars)
    lo = min(0, min(min(a, b) for _, a, b, _ in bars))
    hi = max(max(a, b) for _, a, b, _ in bars)
    broken = False
    if axis == 'auto' and lo == 0:
        floor = min(min(a, b) for _, a, b, k in bars if k in ('up', 'down')) if any(k in ('up', 'down') for *_, k in bars) else 0
        span = hi - floor
        if floor > 0 and span < 0.5 * hi:
            lo = max(0, floor - span * 0.6)
            broken = True
    top = 34

    def Y(v):
        return top + height * (hi - v) / (hi - lo)
    gw = f.w / n
    bw = min(gw * 0.62, 120)
    hl = set(highlight)
    prev_x = None
    lab_lines = {}
    for i, (lab, a, b, kind) in enumerate(bars):
        cx = i * gw + gw / 2
        x = cx - bw / 2
        if kind in ('total', 'sub'):
            fill = 'accent_dark' if kind == 'total' else 'grey'
        elif hl:
            fill = 'accent' if lab in hl else 'grey'
        else:
            fill = 'accent' if kind == 'up' else 'bad'
        y1, y2 = Y(max(a, b)), Y(max(min(a, b), lo))
        f.rect(x, y1, bw, max(y2 - y1, 1.5), fill, f'{lab}: {num(b - a if kind in ("up", "down") else b, decimals, unit)}')
        if prev_x is not None:
            yl = Y(a if kind in ('up', 'down') else b)
            f.line(prev_x, yl, x, yl, 'line_strong', 1, '3 3')
        prev_x = x + bw
        if kind in ('up', 'down'):
            on = (lab in hl) if hl else True
            f.text(cx, y1 - 8, num(b - a, decimals, sign=True), 'label',
                   ('accent' if kind == 'up' else 'bad') if on else 'ink', 700 if on else 400, 'middle')
        else:
            f.text(cx, y1 - 8, num(b, decimals), 'label', 'ink', 700, 'middle')
        t = f.wrap(lab, gw - 6, 'label', 700 if kind == 'total' else 400, 3, 'подпись шага')
        lab_lines[lab] = t.count('\n') + 1
        f.text(cx, Y(lo) + 24, t, 'label', 'ink' if kind == 'total' else 'muted', 700 if kind == 'total' else 400, 'middle', lh=18)
    f.line(0, Y(lo), f.w, Y(lo), 'line_strong', 1)
    if broken:
        yb_ = Y(lo) - 26
        for i, (lab, a, b, kind) in enumerate(bars):
            if kind in ('total', 'sub'):
                cx = i * gw + gw / 2
                x = cx - bw / 2 - 3
                f.poly([(x, yb_ + 4), (x + bw + 6, yb_ - 4), (x + bw + 6, yb_ + 4), (x, yb_ + 12)], 'bg')
        f.text(f.w, 14, 'ось обрезана', 'note', 'muted', 400, 'end')
    if unit:
        f.text(0, 14, unit, 'small', 'muted')
    yb = Y(lo) + 24 + 18 * (max(lab_lines.values()) - 1) + 24
    if notes:
        for lab, txt in notes.items():
            i = [b[0] for b in bars].index(lab)
            cx = i * gw + gw / 2
            nw = 300
            x0 = min(max(cx - nw / 2, 0), f.w - nw)
            f.line(cx, Y(lo) + 32 + 18 * (lab_lines[lab] - 1), cx, yb + 8, 'accent', 1.2)
            f.para(x0, yb + 26, txt, nw, 'small', 'ink', max_lines=3, what='выноска шага')
    return f.finish()


def pair_delta(panels, *, decimals=0, height=300, theme=None, mode='показ', width=None):
    """Насколько одно больше другого или «было → стало»: два столбца, пунктир от верхушек и крупная разница.

    panels: [{'title': 'Удовлетворённость', 'sub': 'п.п.', 'a': ('Финтех', 39), 'b': ('Банки', 15), 'decimals'?: 1,
              'hl'?: 'a'|'b', 'delta'?: 'в 120 раз', 'delta_sub'?: 'быстрее'}]
    1–3 панели рядом, у каждой своя шкала (так честнее, чем общая ось для разных единиц).
    Было → стало: a = ('Было', …), b = ('Стало', …), hl='b' (акцент на результате), стрелка идёт от «было» к «стало».
    delta: своя подпись разницы, когда арифметика не говорит главного («в 120 раз» вместо «−119»); delta_sub строкой под ней.
    sub кончается на «%» (единица панели проценты): разница без своей подписи получает «п.п.» сама.
    tone: 'bad' красит выделенный столбец и разницу в цвет потери (негативный исход рядом с позитивным).
    """
    f = Fig(theme, mode, width, 'Пара с разницей')
    need(1 <= len(panels) <= 3, 'панелей 1–3')
    pw = (f.w - (len(panels) - 1) * 40) / len(panels)
    top = 70

    def _diff(p):
        (_, va), (_, vb) = p['a'], p['b']
        if p.get('delta'):
            return p['delta']
        d = num((vb - va) if p.get('hl', 'a') == 'b' else (va - vb), p.get('decimals', decimals), sign=True)
        # разница двух процентов это процентные пункты: без единицы «−8,3» читается как минус 8,3%
        return d + '\u00a0п.п.' if (p.get('sub') or '').strip().endswith('%') else d
    # одна ширина столбцов на все панели: сужается, чтобы справа влезла самая широкая разница
    # и зазор между столбцами: подписи под парой не должны наезжать
    lab_half = max((f.tw(p['a'][0]) + f.tw(p['b'][0])) / 2 + 12 for p in panels)
    # панелей несколько: разница мельче и на одной горизонтали во всех панелях
    drole = 'delta' if len(panels) > 1 else 'big'
    gap = 18
    for _ in range(3):
        bw = max(36, min(pw * 0.22, 90, min((pw - 68 - gap - f.tw(_diff(p), drole, 700) - 12) / 2 for p in panels)))
        gap = max(18, lab_half - bw)
    def _mid(p):
        va, vb = p['a'][1], p['b'][1]
        vmax = max(va, vb)
        ya, yb = top + height * (1 - va / vmax), top + height * (1 - vb / vmax)
        return (ya + yb) / 2
    row_y = sum(_mid(p) for p in panels) / len(panels) + f.s(drole) * 0.36 if len(panels) > 1 else None
    for k, p in enumerate(panels):
        x0 = k * (pw + 40)
        d = p.get('decimals', decimals)
        f.para(x0, 18, p['title'], pw, 'label', 'ink', 700, 1, what='заголовок панели')
        if p.get('sub'):
            f.text(x0, 40, p['sub'], 'small', 'muted')
        (la, va), (lb, vb) = p['a'], p['b']
        need(va >= 0 and vb >= 0, 'pair_delta для неотрицательных; иначе waterfall')
        vmax = max(va, vb)
        hl = p.get('hl', 'a')
        diff = _diff(p)
        xa, xb = x0 + 10, x0 + 10 + bw + gap
        base = top + height
        tone = 'bad' if p.get('tone') == 'bad' else 'accent'
        cols = (tone, 'grey') if hl == 'a' else ('grey', tone)
        for x, lab, v, col in ((xa, la, va, cols[0]), (xb, lb, vb, cols[1])):
            h = height * v / vmax
            f.rect(x, base - h, bw, h, col)
            inside = h >= 34
            f.text(x + bw / 2, base - h + 22 if inside else base - h - 8, num(v, d), 'label',
                   ('on_dark' if col == tone else 'ink') if inside else (tone if col == tone else 'ink'), 700 if col == tone else 400, 'middle')
            f.text(x + bw / 2, base + 22, lab, 'label', 'ink', 400, 'middle')
        f.line(x0, base, xb + bw + 10, base, 'line_strong', 1)
        ya, yb = base - height * va / vmax, base - height * vb / vmax
        hi_y, lo_y = min(ya, yb), max(ya, yb)
        xr = xb + bw + 44
        f.line(xa + bw, hi_y, xr, hi_y, 'line_strong', 1, '4 3')
        f.line(xb + bw, lo_y, xr, lo_y, 'line_strong', 1, '4 3')
        if lo_y - hi_y > 14:
            # стрелка от первого значения ко второму: рост вверх, снижение вниз
            if hl == 'b':
                f.arrow(xr, ya, xr, yb + (-1 if yb > ya else 1), 'line_strong', 1.2, 8)
            else:
                f.arrow(xr, lo_y, xr, hi_y + 1, 'line_strong', 1.2, 8)
        if row_y is not None:
            ty = row_y
        else:
            ty = (hi_y + lo_y) / 2 + f.s('big') * 0.36 if lo_y - hi_y > 50 else lo_y + 40
        f.para(xr + 14, ty, diff, x0 + pw - xr - 14, drole, tone, 700, 1, what='разница')
        if p.get('delta_sub'):
            f.para(xr + 14, ty + 26, p['delta_sub'], x0 + pw - xr - 14, 'label', tone, 700, 2, what='подпись разницы', lh=19)
    return f.finish()


def gap_to_target(rows, *, unit='', decimals=0, target_word='цель', fact_word='сейчас', theme=None, mode='показ', width=None):
    """Сколько не хватает до цели: полоса факта, стрелка разрыва, плашка цели. По строке на объект.

    rows: [('Москва', 40, 54), ...]: подпись, факт, цель.
    """
    f = Fig(theme, mode, width, 'Разрыв до цели')
    need(1 <= len(rows) <= 10, 'строк 1–10')
    lw = max(f.tw(r[0], 'label') for r in rows) + 24
    plate_w = f.tw(f'{target_word}: {num(max(r[2] for r in rows), decimals, unit)}', 'label', 700) + 24
    pw = f.w - lw - plate_w - 10
    vmax = max(max(r[1], r[2]) for r in rows)
    rh = 52
    y = 6
    for lab, fact, tgt in rows:
        cy = y + rh / 2
        f.text(0, cy + 5, lab, 'label', 'ink')
        wf = pw * fact / vmax
        f.rect(lw, cy - 15, wf, 30, 'grey_light')
        f.text(lw + wf / 2, cy + 5, num(fact, decimals), 'label', 'ink', 700, 'middle')
        xt = lw + pw * tgt / vmax
        gap = tgt - fact
        if gap > 0:
            f.line(lw + wf + 6, cy, xt - 4, cy, 'accent', 1.5)
            f.poly([(xt - 2, cy), (xt - 11, cy - 5), (xt - 11, cy + 5)], 'accent')
            f.line(xt, cy - 11, xt, cy + 11, 'accent', 1.5)
            gs = num(-gap, decimals)
            mid = (lw + wf + xt) / 2
            gw_ = f.tw(gs, 'label', 700) + 10
            if xt - (lw + wf) > gw_ + 20:
                f.rect(mid - gw_ / 2, cy - 11, gw_, 22, 'bg')
                f.text(mid, cy + 5, gs, 'label', 'accent', 700, 'middle')
            f.plate(xt + 10, cy + 5, f'{target_word}: {num(tgt, decimals, unit)}', 'accent_dark', 'on_dark', 'label', 10, anchor='start')
        else:
            f.plate(lw + wf + 10, cy + 5, f'выше цели на {num(-gap, decimals, unit)}', 'good', 'on_dark', 'label', 10, anchor='start')
        y += rh
    f.rect(lw, y + 14, 14, 14, 'grey_light')
    f.text(lw + 22, y + 26, fact_word, 'small', 'muted')
    fx = lw + 40 + f.tw(fact_word, 'small')
    f.line(fx, y + 21, fx + 22, y + 21, 'accent', 1.5)
    f.text(fx + 30, y + 26, 'разрыв до цели', 'small', 'muted')
    return f.finish(y + 40)


def group_delta(metrics, groups, *, decimals=0, pct=True, bad_if_negative=True, theme=None, mode='показ', width=None):
    """Две группы по нескольким показателям и разница между ними плашкой: где отстаём.

    metrics: [{'title': 'Велокультура', 'sub': 'взрослые с велосипедом, %', 'values': (59, 33), 'decimals'?: 2}]
    groups: ('Лидеры', 'Середняки'). Разница в % от первой (pct=True) или в единицах.
    """
    f = Fig(theme, mode, width, 'Две группы по показателям')
    need(2 <= len(metrics) <= 5, 'показателей 2–5')
    lw = min(max(f.tw(g, 'label', 700) for g in groups) + 28, 200)
    cw = (f.w - lw) / len(metrics)
    y_head = 18
    maxsub = 0
    for k, m in enumerate(metrics):
        x = lw + k * cw
        f.text(x, y_head, m['title'], 'label', 'ink', 700)
        if m.get('sub'):
            maxsub = max(maxsub, f.para(x, y_head + 22, m['sub'], cw - 24, 'small', 'muted', max_lines=3, what='подпись показателя'))
    y1 = y_head + 22 + maxsub + 30
    y2 = y1 + 96
    bh = 32
    for gi, (g, yy) in enumerate(((groups[0], y1), (groups[1], y2))):
        f.rect(0, yy, 6, bh, 'accent_dark' if gi == 0 else 'grey')
        f.para(16, yy + 20, g, lw - 24, 'label', 'ink', 700, 2, what='имя группы', lh=18)
    for k, m in enumerate(metrics):
        x = lw + k * cw
        a, b = m['values']
        d = m.get('decimals', decimals)
        vmax = max(a, b) or 1
        barw = (cw - 90) * 0.85
        for v, yy, col, tc in ((a, y1, 'accent_dark', 'on_dark'), (b, y2, 'grey', 'ink')):
            w_ = max(barw * v / vmax, 40)
            f.rect(x, yy, w_, bh, col)
            f.text(x + w_ / 2, yy + 21, num(v, d), 'label', tc, 700, 'middle')
        xe = x + barw + 20
        f.line(x + barw * a / vmax + 4, y1 + bh / 2, xe, y1 + bh / 2, 'line_strong', 1)
        f.line(xe, y1 + bh / 2, xe, y2 + bh / 2, 'line_strong', 1)
        f.arrow(xe, y2 + bh / 2, x + max(barw * b / vmax, 40) + 6, y2 + bh / 2, 'line_strong', 1, 7)
        dv = (b - a) / a * 100 if pct and a else b - a
        s = num(dv, 0, sign=True, pct=True) if pct else num(dv, d, sign=True)
        neg = dv < 0
        if abs(dv) < 1e-9:
            fill, tc = 'surface', 'muted'
        elif neg == bad_if_negative:
            fill, tc = 'bad_pale', 'bad'
        else:
            fill, tc = 'good_pale', 'good'
        mid = (y1 + y2 + bh) / 2
        f.plate(xe, mid + 6, s, fill, tc, 'label', 9)
    f.line(0, y2 + bh + 24, f.w, y2 + bh + 24, 'line', 1)
    return f.finish(y2 + bh + 28)


def dumbbell(rows, *, names=('до', 'после'), unit='', decimals=0, style='dots', scale=None, zero=None,
             zones=None, ticks=None, theme=None, mode='показ', width=None):
    """Два значения на строку и полоса разницы: где разрыв большой, а где его нет. Или «было → стало».

    rows: [('Трансформация ИТ', 45, 54), ...] значения в порядке names.
    style: 'dots' (гантель: серая и акцентная точка) или 'arrow' (треугольник до, треугольник после, стрелка).
    zero: значение, где пунктир «равенства» (для шкал вокруг нуля).
    zones: [{'from': i, 'to': j, 'text': '**Ключ** пояснение'}] выводы справа на группу строк.
    ticks: значения подписей шкалы сверху; по умолчанию 5 делений.
    """
    f = Fig(theme, mode, width, 'Гантели')
    need(2 <= len(rows) <= 15, 'строк 2–15')
    lw = min(max(f.tw(r[0], 'label') for r in rows) + 24, f.w * 0.3)
    zw = f.w * 0.27 if zones else 0
    x0, x1 = lw + 14, f.w - zw - (24 if zones else 14)
    lo = min(min(r[1], r[2]) for r in rows)
    hi = max(max(r[1], r[2]) for r in rows)
    if scale:
        lo, hi = scale
    else:
        pad = (hi - lo) * 0.08 or 1
        lo, hi = (min(lo - pad, 0) if lo >= 0 else lo - pad), hi + pad

    def X(v):
        return x0 + (x1 - x0) * (v - lo) / (hi - lo)
    top = 70
    lx = x0
    for k, nm in enumerate(names):
        col = 'grey' if k == 0 else 'accent'
        if style == 'arrow':
            f.poly([(lx, top - 44), (lx + 7, top - 56), (lx + 14, top - 44)], col)
        else:
            f.circle(lx + 7, top - 50, 7, col)
        f.text(lx + 22, top - 45, nm, 'small', 'ink')
        lx += 44 + f.tw(nm, 'small')
    tk = ticks or [lo + (hi - lo) * i / 4 for i in range(5)]
    for t in tk:
        f.text(X(t), top - 12, num(t, decimals), 'small', 'muted', 400, 'middle')
    if unit:
        f.text(x0 - 22, top - 12, unit, 'small', 'muted', 400, 'end')
    rh = 44
    y = top
    for lab, a, b in rows:
        cy = y + rh / 2
        f.para(0, cy + 5, lab, lw - 12, 'label', 'ink', max_lines=1, what='подпись строки')
        xa, xb = X(a), X(b)
        f.rect(min(xa, xb), cy - 7, abs(xb - xa), 14, 'grey_light')
        if style == 'arrow':
            if abs(xb - xa) > 40:
                mx = (xa + xb) / 2
                sgn = 1 if xb > xa else -1
                f.line(mx - 8 * sgn, cy, mx + 8 * sgn, cy, 'line_strong', 1.2)
                f.poly([(mx + 10 * sgn, cy), (mx + 4 * sgn, cy - 4), (mx + 4 * sgn, cy + 4)], 'line_strong')
            f.poly([(xa - 8, cy + 7), (xa, cy - 8), (xa + 8, cy + 7)], 'grey')
            f.poly([(xb - 9, cy + 8), (xb, cy - 9), (xb + 9, cy + 8)], 'accent')
        else:
            f.circle(xa, cy, 8, 'grey')
            f.circle(xb, cy, 8, 'accent')
        f.line(0, y + rh, x1, y + rh, 'line_soft', 1)
        y += rh
    for t in tk:
        f.line(X(t), top, X(t), y, 'line_soft', 1)
    if zero is not None:
        f.line(X(zero), top - 4, X(zero), y, 'line_strong', 1.2, '4 3')
    if zones:
        for z in zones:
            ya, yb = top + z['from'] * rh, top + (z['to'] + 1) * rh
            f.line(f.w - zw, yb, f.w, yb, 'line', 1)
            f.rich(f.w - zw + 6, ya + 22, z['text'], zw - 10, 'small', 'ink', max_lines=5, what='вывод зоны')
    return f.finish(y + 6)
