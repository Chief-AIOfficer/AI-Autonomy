"""Полосы и столбцы: рейтинг, сравнение категорий, ряд по периодам."""
from .core import Fig, need, num, nice_max


def _norm_rows(data):
    rows = []
    for r in data:
        if isinstance(r, dict):
            rows.append(dict(r))
        else:
            rows.append({'label': r[0], 'value': r[1]})
    for r in rows:
        need('label' in r and 'value' in r, f'в строке нет label или value: {r}')
    return rows


def bar_ranked(data, *, highlight=(), unit='', decimals=0, sort=True, value_inside=False,
               total=None, cols=(), notes=None, scale_max=None, label_w=None,
               theme=None, mode='показ', width=None):
    """Рейтинг горизонтальными полосами: кто больше. Акцент только на тех, о ком заголовок.

    data: [(подпись, значение)] или [{'label', 'value', 'sub'?, 'to'?}]; 'to' рисует диапазон штриховкой до этого значения.
    highlight: подписи строк, которые красить акцентом; остальные серые.
    total: {'label', 'value'} строка итога под чертой, жирная.
    cols: правые колонки [{'title', 'values': [...], 'decimals'?, 'sign'?}] (например, «изменение, %»).
    notes: {подпись: текст} выноска справа от полосы.
    """
    f = Fig(theme, mode, width, 'Рейтинг полосами')
    rows = _norm_rows(data)
    need(2 <= len(rows) <= 20, f'рейтинг держит 2–20 строк, пришло {len(rows)}; больше: таблица или топ-N + «прочие»')
    need(all(r['value'] >= 0 for r in rows), 'отрицательные значения: бери pair_delta или bar_diverging')
    if sort:
        rows.sort(key=lambda r: -r['value'])
    hl = set(highlight)
    has_sub = any(r.get('sub') for r in rows)
    lw = label_w or min(max(f.tw(r['label'], 'label', 700 if r['label'] in hl else 400) for r in rows + ([dict(total)] if total else [])) + 24, f.w * 0.36)
    col_w = 96
    right = f.w - len(cols) * col_w
    note_w = 0
    if notes:
        note_w = 220
        right -= note_w
    rh = 46 if has_sub else 34
    bar_h = 24 if has_sub else 22
    vmax = scale_max or max(max(r.get('to', r['value']), r['value']) for r in rows + ([total] if total else []))
    vmax = vmax * (1.0 if value_inside else 1.12)
    x0 = lw
    pw = right - x0 - 8
    y = 8
    if cols:
        for k, c in enumerate(cols):
            f.text(right + k * col_w + col_w - 6, y + 10, c['title'], 'small', 'muted', 700, 'end')
        y += 26
    for i, r in enumerate(rows):
        on = r['label'] in hl
        col = 'accent' if on else 'grey'
        cy = y + rh / 2
        lab = f.wrap(r['label'], lw - 16, 'label', 700 if on else 400, 2, 'подпись строки')
        two = '\n' in lab
        ty = cy + (-2 if has_sub and r.get('sub') else 5) - (8 if two else 0)
        f.text(0, ty, lab, 'label', 'accent' if on else 'ink', 700 if on else 400, lh=17)
        if r.get('sub'):
            f.text(0, ty + 18, r['sub'], 'small', 'muted')
        bw = pw * r['value'] / vmax
        f.rect(x0, cy - bar_h / 2, bw, bar_h, col, f"{r['label']}: {num(r['value'], decimals, unit)}")
        if r.get('to') and r['to'] > r['value']:
            bw2 = pw * r['to'] / vmax
            f.rect(x0 + bw, cy - bar_h / 2, bw2 - bw, bar_h, 'accent_pale' if on else 'grey_light')
        val = num(r['value'], decimals, unit)
        vw = f.tw(val, 'label', 700)
        if value_inside and bw > vw + 16:
            f.text(x0 + 8, cy + 5, val, 'label', 'on_dark' if on else 'ink', 700 if on else 400)
        else:
            f.text(x0 + bw + 6 + (pw * (r.get('to', 0) - r['value']) / vmax if r.get('to', 0) > r['value'] else 0), cy + 5,
                   val, 'label', 'accent' if on else 'ink', 700 if on else 400)
        for k, c in enumerate(cols):
            v = c['values'][i]
            f.text(right + k * col_w + col_w - 6, cy + 5, num(v, c.get('decimals', 1), sign=c.get('sign', False)) if isinstance(v, (int, float)) else str(v),
                   'label', 'ink', 400, 'end')
        if notes and r['label'] in notes:
            f.para(f.w - note_w + 20, cy + 5 - (8 if f.tw(notes[r['label']], 'small') > note_w - 20 else 0), notes[r['label']], note_w - 20, 'small', 'accent', max_lines=2, what='выноска')
        f.line(0, y + rh, f.w, y + rh, 'line_soft', 1, '1 3')
        y += rh
    if total:
        f.line(0, y + 2, f.w, y + 2, 'line_strong', 1.2)
        y += 4
        cy = y + rh / 2
        f.text(0, cy + 5, total['label'], 'label', 'ink', 700)
        bw = pw * total['value'] / vmax
        f.rect(x0, cy - bar_h / 2, bw, bar_h, 'accent_dark')
        f.text(x0 + bw + 6, cy + 5, num(total['value'], decimals, unit), 'label', 'ink', 700)
        for k, c in enumerate(cols):
            v = c.get('total')
            if v is not None:
                f.text(right + k * col_w + col_w - 6, cy + 5, num(v, c.get('decimals', 1), sign=c.get('sign', False)), 'label', 'ink', 700, 'end')
        y += rh
    return f.finish(y + 6)


def columns(categories, series, *, highlight=None, unit='', decimals=0, groups=None, frame=None,
            callout=None, side=None, cagr=None, axis_note=None, height=360, value_labels=True,
            pair_deltas=False, delta_unit='', up_is_good=True, title=None, sub=None, top_min=None, value_text=None,
            theme=None, mode='показ', width=None):
    """Вертикальные столбцы: ряд по периодам или сравнение категорий, одна или несколько серий.

    categories: подписи по оси X (годы, страны).
    series: {имя: [значения]}; одна серия без легенды, несколько: подпись серии у последней группы.
    highlight: имя серии, индекс категории или список индексов: что красить акцентом, остальное серое.
               Без highlight одна серия рисуется accent_dark, несколько серий цветами theme.series.
    groups: [{'from': i, 'to': j, 'title': 'вывод группы', 'tone': 'dark'|'accent'|'grey'}] плашки-выводы над группами.
    frame: {'from': i, 'to': j, 'note': 'текст'} пунктирная рамка вокруг худших/лучших и выноска под осью.
    callout: {'cat': i, 'series'?: имя, 'text': '+68% г/г', 'sub'?: 'Корпоративные'} выноска с линией к столбцу.
    side: {'title': 'И что из этого', 'text': '...', 'note'?: '...'} врезка справа на треть ширины.
    cagr: {'from': i, 'to': j, 'text': '+12% в год'} стрелка над столбцами.
    pair_deltas: при двух сериях скобка со стрелкой над каждой парой и плашка разницы (второе минус первое),
                 зелёная или красная по up_is_good; delta_unit: 'п.п.' и т. п.
    title, sub: заголовок панели и единицы внутри рисунка; несколько панелей в ряд собирать через X.panels.
    top_min: верх поля графика не выше этого y (ставит X.panels, чтобы оси панелей совпали).
    value_text: свои подписи значений по категориям (одна серия), когда число на шкале условное: «≈9 мес.», «5–6 дней».
    """
    f = Fig(theme, mode, width, 'Столбцы')
    names = list(series)
    need(1 <= len(names) <= 4, 'серий 1–4; больше: малые кратные (small_multiples) или линии')
    n = len(categories)
    for k in names:
        need(len(series[k]) == n, f'серия {k}: {len(series[k])} значений при {n} категориях')
    need(n * len(names) <= 40, 'больше 40 столбцов не читается; агрегируй периоды или бери линию')
    side_w = f.w * 0.3 if side else 0
    pw = f.w - side_w - (24 if side else 0)
    legend_w = 0
    if len(names) > 1:
        legend_w = max(f.tw(k, 'small', 700) for k in names) + 40
        pw -= legend_w
    top = 30 + f.panel_head(title, sub)
    if groups:
        top += 52
    if cagr:
        top += 48
    if pair_deltas:
        need(len(names) == 2, 'pair_deltas только для двух серий')
        top += 56
    if callout:
        top += 40
    top = max(top, top_min or 0)
    base = top + height
    vals = [v for k in names for v in series[k] if v is not None]
    need(all(v >= 0 for v in vals), 'отрицательные значения: pair_delta или waterfall')
    vmax = max(vals) * 1.0
    gw = pw / n
    inner = 0.72 if len(names) == 1 else 0.82
    bw = gw * inner / len(names)
    gap_in = 2 if len(names) > 1 else 0

    def is_on(k, i):
        if highlight is None:
            return None
        if isinstance(highlight, str):
            return k == highlight
        if isinstance(highlight, int):
            return i == highlight
        return i in highlight

    tops = {}
    for i, cat in enumerate(categories):
        gx = i * gw + gw * (1 - inner) / 2
        for j, k in enumerate(names):
            v = series[k][i]
            if v is None:
                continue
            on = is_on(k, i)
            if on is None:
                fill = f.th.series[j] if len(names) > 1 else 'accent_dark'
            else:
                fill = 'accent' if on else 'grey'
            h = height * v / vmax
            x = gx + j * bw
            f.rect(x + gap_in / 2, base - h, bw - gap_in, h, fill, f'{cat}, {k}: {num(v, decimals, unit)}')
            tops[(i, k)] = (x + bw / 2, base - h)
            hide = callout and callout['cat'] == i and callout.get('series', names[0]) == k
            vt = value_text[i] if value_text and len(names) == 1 else num(v, decimals)
            if value_labels and not hide and (value_text or bw >= f.tw(vt, 'small') * 0.9):
                f.text(x + bw / 2, base - h - 7, vt, 'small' if len(names) > 1 else 'label',
                       'accent' if on else 'ink', 700 if on else 400, 'middle')
        lab = f.wrap(str(cat), gw - 4, 'label', 400, 2, 'подпись категории')
        f.text(i * gw + gw / 2, base + 22, lab, 'label', 'muted', 400, 'middle', lh=17)
    f.line(0, base, pw, base, 'line_strong', 1)
    if len(names) > 1:
        # легенда без рамки: подписи серий справа сверху вниз в цвете серий
        for j, k in enumerate(names):
            on = is_on(k, 0) if isinstance(highlight, str) else None
            fill = ('accent' if on else 'grey') if on is not None else f.th.series[j]
            yy = top + 10 + j * 26
            f.rect(pw + 14, yy - 11, 12, 12, fill)
            f.text(pw + 32, yy, k, 'small', 'ink', 700 if on else 400)
    if groups:
        for g in groups:
            x1, x2 = g['from'] * gw + 4, (g['to'] + 1) * gw - 4
            tone = {'dark': ('accent_dark', 'on_dark'), 'accent': ('accent', 'on_dark'), 'grey': ('surface', 'ink')}[g.get('tone', 'dark')]
            t = f.wrap(g['title'], x2 - x1 - 28, 'label', 700, 2, 'вывод группы')
            hh = 22 + 19 * (t.count('\n') + 1)
            f.rect(x1, 8, min(x2 - x1, f.tw(max(t.split('\n'), key=len), 'label', 700) + 32), hh, tone[0], rx=6)
            f.text(x1 + 14, 8 + 26, t, 'label', tone[1], 700, lh=19)
            if g['to'] < n - 1:
                xs = (g['to'] + 1) * gw
                f.line(xs, 8, xs, base, 'line', 1)
    if frame:
        x1, x2 = frame['from'] * gw + 2, (frame['to'] + 1) * gw - 2
        ymin = min(tops[(i, k)][1] for i in range(frame['from'], frame['to'] + 1) for k in names if (i, k) in tops)
        f.rect(x1, ymin - 30, x2 - x1, base - ymin + 30 + 40, 'none', stroke='accent_mid', dash='5 4')
        if frame.get('note'):
            cx = (x1 + x2) / 2
            f.line(cx, base + 40, cx, base + 64, 'accent_mid', 1.2)
            f.circle(cx, base + 64, 4, 'accent_mid')
            f.para(cx + 14, base + 70, frame['note'], min(pw - cx - 14, 460), 'small', 'ink', max_lines=4, what='выноска рамки')
    if callout:
        k = callout.get('series', names[0])
        bx, by = tops[(callout['cat'], k)]
        tw_ = max(f.tw(callout['text'], 'head', 700), f.tw(callout.get('sub', ''), 'small'))
        right = bx + 20 + tw_ <= f.w
        tx = bx + 20 if right else bx - 20 - tw_
        ty = by - 56
        # над столбцами, которые выноска перекрывает по ширине, с запасом на их подписи значений
        under = [yy for (i_, k_), (xx, yy) in tops.items() if tx - gw / 2 <= xx <= tx + tw_ + gw / 2 and i_ != callout['cat']]
        if under:
            ty = min(ty, min(under) - 30 - (18 if callout.get('sub') else 0))
        f.text(bx, by - 8, num(series[k][callout['cat']], decimals), 'label', 'accent', 700, 'middle')
        # выноска ломаной под прямым углом: от точки над значением вверх, затем короткий отвод к тексту
        f.circle(bx, by - 30, 3.5, 'accent')
        f.line(bx, by - 30, bx, ty - 6, 'accent', 1.5)
        f.line(bx, ty - 6, (tx - 6) if right else (tx + tw_ + 6), ty - 6, 'accent', 1.5)
        f.text(tx, ty, callout['text'], 'head', 'accent', 700)
        if callout.get('sub'):
            f.text(tx, ty + 18, callout['sub'], 'small', 'accent')
    if cagr:
        (x1, y1), (x2, y2) = tops[(cagr['from'], names[0])], tops[(cagr['to'], names[-1])]
        # скобка над всеми столбцами отрезка, не только над крайними
        span = [yy for (i_, k_), (xx, yy) in tops.items() if cagr['from'] <= i_ <= cagr['to']]
        yt = min(span) - 44 - (40 if callout else 0)
        f.elbow(x1, y1 - 26, x2, y2 - 24, yt, 'line_strong', 1)
        f.plate((x1 + x2) / 2, yt - 10, cagr['text'], 'accent', 'on_dark', 'label')
    if pair_deltas:
        a_, b_ = names
        for i in range(n):
            if (i, a_) not in tops or (i, b_) not in tops:
                continue
            (xa, ya), (xb, yb) = tops[(i, a_)], tops[(i, b_)]
            yt = min(ya, yb) - 40
            f.elbow(xa, ya - 26, xb, yb - 24, yt)
            d = series[b_][i] - series[a_][i]
            good = (d >= 0) == up_is_good
            fill, tc = ('surface', 'muted') if abs(d) < 1e-9 else (('good_pale', 'good') if good else ('bad_pale', 'bad'))
            f.plate((xa + xb) / 2, yt - 10, num(d, decimals, delta_unit, sign=True), fill, tc, 'small', 7)
    if side:
        sx = f.w - side_w
        t1 = f.wrap(side['text'], side_w - 40, 'label', 400, 8, 'врезка')
        t2 = f.wrap(side['note'], side_w - 40, 'small', 400, 5, 'врезка, примечание') if side.get('note') else ''
        lh1, lh2 = round(f.s('label') * 1.35), round(f.s('small') * 1.35)
        h_side = 34 + 30 + (t1.count('\n') + 1) * lh1 + ((t2.count('\n') + 1) * lh2 + 14 if t2 else 0) + 14
        y0 = max(top, base - h_side)
        f.rect(sx, y0, side_w, h_side, 'surface')
        yy = y0 + 34
        f.text(sx + 20, yy, side['title'], 'head', 'ink', 700)
        yy += 30
        f.text(sx + 20, yy, t1, 'label', 'ink', lh=lh1)
        yy += (t1.count('\n') + 1) * lh1 + 14
        if t2:
            f.text(sx + 20, yy, t2, 'small', 'muted', lh=lh2)
    if axis_note:
        f.text(0, top - 8 if not groups else base + 60, axis_note, 'small', 'muted')
    return f.finish(base=base, top=top)
