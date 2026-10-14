"""Таблицы, которые читаются как график: столбики в ячейках, шары Харви, тон, мини-стеки; тепловая сетка точками."""
from .core import Fig, need, num

DARK = {'accent', 'accent_dark', 'accent_mid', 'accent_soft', 'good', 'bad'}


def _tone(th, v, scale):
    lo, hi = scale
    k = (v - lo) / (hi - lo) if hi != lo else 1
    k = min(max(k, 0), 0.9999)
    return th.ramp[int(k * len(th.ramp))]


def harvey(f, cx, cy, r, v, fill='accent_dark', levels=4):
    """Шар Харви: v от 0 до levels; заливка v / levels круга (4 уровня: четверти, 3 уровня: трети)."""
    f.circle(cx, cy, r, 'bg', fill, 1.5)
    if v > 0:
        f.arc(cx, cy, r, v / levels, fill)


def table(columns, rows, *, group_w=None, legend=None, legend_title=None, harvey_levels=4, row_lines=True, row_h=None,
          theme=None, mode='показ', width=None):
    """Таблица-график. Колонки разных видов, строки можно группировать.

    columns: [{'key', 'title', 'type', 'width'?, ...}], type:
      'text'   текст, **жирные ключи** допустимы; 'bold': True для колонки-имени
      'num'    число: 'decimals', 'unit', 'sign'
      'bar'    столбик в ячейке на сером треке, 'max' (по умолчанию максимум колонки), 'fill' роль цвета, 'decimals', 'unit'
      'harvey' шар Харви, значение 0–4
      'tone'   кружок цвета шкалы одного тона, 'scale': (min, max), 'show': показывать число
      'stack'  мини-стек из частей, 'parts': [имена], значение: список чисел; легенда частей сверху
      'bars'   мини-группа горизонтальных полосок (по одной на серию), 'parts': [имена], значение: список
      'kpi'    ключевое число строки крупно акцентом («в 120 раз», «−80%», «83%»): цифры кейсов не тонут в тексте
      'mark'   категория буквой в залитой клетке, 'marks': {'Р': 'accent', 'С': 'accent_pale'} (роли RACI: решает, согласует);
               это категории, не степень, поэтому не шары Харви
    rows: [{key: значение, 'group'?: 'Имя группы', 'hl'?: True}]; group рисует колонку групп слева с чертой между группами.
    legend: [('harvey', 'Пилот', 3)] для шаров (первым элементом вид колонки: 'harvey' или роль цвета для tone); рисуется сверху справа.
    legend_title: что меряет шкала («Вклад»), пишется перед легендой; без него «малый» и «основной» читаются как разные измерения.
    harvey_levels: сколько ступеней у шаров (4 четверти или 3 трети). Легенда должна идти без пропусков: 0 или 1, затем подряд до harvey_levels.
    row_h: наименьшая высота строки; для текстовой таблицы на весь слайд, чтобы строки не жались к верху.
    """
    f = Fig(theme, mode, width, 'Таблица')
    f.text_scheme = True
    need(1 <= len(rows) <= 16, 'строк 1–16; больше: топ и «прочие» или приложение')
    grouped = any(r.get('group') for r in rows)
    gw = (group_w or 150) if grouped else 0
    fixed = sum(c.get('width', 0) for c in columns)
    flex = [c for c in columns if not c.get('width')]
    defaults = {'num': 90, 'bar': 200, 'harvey': 70, 'tone': 70, 'stack': 220, 'bars': 200, 'kpi': 170, 'mark': 90}
    for c in flex:
        if c['type'] != 'text':
            c['_w'] = defaults[c['type']]
    text_cols = [c for c in flex if c['type'] == 'text']
    rest = f.w - gw - fixed - sum(c.get('_w', 0) for c in flex)
    need(rest > 60 * len(text_cols), 'колонки не помещаются по ширине: сократи число или ширины')
    for c in text_cols:
        c['_w'] = rest / len(text_cols)
    for c in columns:
        c['_w'] = c.get('width') or c['_w']
    xs = []
    x = gw
    for c in columns:
        xs.append(x)
        x += c['_w']
    y = 0
    if legend:
        lx = f.w
        items = []
        for kind, lab, v in legend[::-1]:
            lw_ = f.tw(lab, 'small') + (44 if kind == 'mark' else 36)
            lx -= lw_
            items.append((lx, kind, lab, v))
        hv = sorted(v for kind, lab, v in legend if kind == 'harvey')
        if hv and hv != list(range(hv[0], harvey_levels + 1)):
            f.warn.append(f'шкала Харви с пропуском или лишним уровнем {hv} при {harvey_levels} ступенях: шаг шкалы должен быть ровным')
        if legend_title:
            f.text(lx - 14, 15, legend_title, 'small', 'muted', 700, 'end')
        for lx_, kind, lab, v in items:
            if kind == 'harvey':
                harvey(f, lx_ + 9, 10, 8, v, levels=harvey_levels)
            elif kind == 'mark':
                letter, role_ = v
                f.rect(lx_, 1, 22, 18, role_)
                f.text(lx_ + 11, 15, letter, 'small', 'on_dark' if role_ in DARK else 'accent_dark', 700, 'middle')
                f.text(lx_ + 30, 15, lab, 'small', 'ink')
                continue
            else:
                f.circle(lx_ + 9, 10, 8, v)
            f.text(lx_ + 24, 15, lab, 'small', 'ink')
        y = 34
    # части для stack/bars
    for c in columns:
        if c['type'] in ('stack', 'bars'):
            c['_cols'] = list(f.th.series[:len(c['parts'])])
    # шапка
    head_h = 0
    for c, x in zip(columns, xs):
        h = f.para(x + 6, y + 16, c.get('title', ''), c['_w'] - 12, 'small', 'muted', 700, 2, what='заголовок колонки', lh=16,
                   anchor='start')
        head_h = max(head_h, h)
    y += head_h + 14
    head_rule = y
    if not any(c.get('title') for c in columns):
        f.warn.append('у таблицы нет заголовков колонок: непонятно, что она несёт; дай шапку или возьми другой приём')
    f.line(0, y, f.w, y, 'line_strong', 1.2)
    # максимумы
    for c in columns:
        if c['type'] == 'bar':
            c['_max'] = c.get('max') or max(r[c['key']] for r in rows if r.get(c['key']) is not None)
        if c['type'] in ('stack', 'bars'):
            c['_max'] = c.get('max') or max((sum(r[c['key']]) if c['type'] == 'stack' else max(r[c['key']])) for r in rows)
    lh = round(f.s('label') * 1.3)
    cur_group = None
    group_start = y
    for ri, r in enumerate(rows):
        # высота строки по текстам
        texts = {}
        nl = 1
        for c in columns:
            if c['type'] == 'text':
                v = str(r.get(c['key'], ''))
                if '**' in v:
                    texts[c['key']] = v
                    est = f.tw(v.replace('**', ''), 'label') / (c['_w'] - 16)
                    nl = max(nl, int(est) + 1)
                else:
                    t = f.wrap(v, c['_w'] - 16, 'label', 700 if c.get('bold') or r.get('hl') else 400, 4, f'ячейка «{c.get("title", "")}»')
                    texts[c['key']] = t
                    nl = max(nl, t.count('\n') + 1)
        if c_bars := [c for c in columns if c['type'] == 'bars']:
            nl = max(nl, max(len(c['parts']) for c in c_bars) * 14 // lh + 1)
        compact = bool(row_h and row_h < 34)       # плотная таблица: строка по тексту, без запаса
        rh = max(row_h or 40, (10 if compact else 18) + nl * lh)
        g = r.get('group')
        if grouped and g != cur_group:
            if cur_group is not None:
                f.line(0, y, f.w, y, 'line_strong', 1)
            f.para(0, y + 26, g, gw - 14, 'label', 'ink', 700, 3, what='имя группы', lh=18)
            cur_group = g
        elif ri and row_lines:
            f.line(gw, y, f.w, y, 'line', 1)
        cy = y + rh / 2
        ty = y + (8 + f.s('label') if compact else 26)
        for c, x in zip(columns, xs):
            v = r.get(c['key'])
            w = c['_w']
            t = c['type']
            if v is None:
                continue
            if t == 'text':
                if '**' in str(v):
                    f.rich(x + 8, ty, v, w - 16, 'label', 'ink', max_lines=4, what='ячейка')
                else:
                    f.text(x + 8, ty, texts[c['key']], 'label', 'ink', 700 if c.get('bold') or r.get('hl') else 400, lh=lh)
            elif t == 'mark':
                role_ = c['marks'][v]
                f.rect(x + 3, y + 3, w - 6, rh - 6, role_)
                f.text(x + w / 2, cy + 5, str(v), 'small', 'on_dark' if role_ in DARK else 'accent_dark', 700, 'middle')
            elif t == 'kpi':
                kt = str(v)
                need(f.tw(kt, 'head', 700) <= w - 16, f'ключевое число «{kt}» шире колонки {w:.0f}px: расширь колонку или сократи')
                f.text(x + 8, ty + 1, kt, 'head', 'accent', 700)
            elif t == 'num':
                f.text(x + w - 10, ty, num(v, c.get('decimals', 0), c.get('unit', ''), c.get('sign', False)), 'label', 'ink',
                       700 if r.get('hl') else 400, 'end')
            elif t == 'bar':
                bw = (w - 20) * v / c['_max']
                f.rect(x + 8, cy - 12, w - 20, 24, 'surface')
                f.rect(x + 8, cy - 12, bw, 24, c.get('fill', 'accent' if r.get('hl') else 'accent_light'))
                s = num(v, c.get('decimals', 0), c.get('unit', ''))
                inside = bw > f.tw(s, 'small', 700) + 14
                f.text(x + 8 + (bw - 6 if inside else bw + 6), cy + 5, s, 'small',
                       'on_dark' if inside and c.get('fill', 'accent' if r.get('hl') else 'accent_light') in DARK else 'ink', 700, 'end' if inside else 'start')
            elif t == 'harvey':
                need(0 <= v <= harvey_levels, f'шар Харви {v} вне шкалы 0–{harvey_levels}')
                harvey(f, x + w / 2, cy, 11, v, levels=harvey_levels)
            elif t == 'tone':
                tone = _tone(f.th, v, c.get('scale', (0, 1)))
                f.circle(x + w / 2, cy, 12, tone)
                if c.get('show'):
                    f.text(x + w / 2, cy + 4, num(v, c.get('decimals', 0)), 'note', 'on_dark' if tone in DARK else 'ink', 700, 'middle')
            elif t == 'stack':
                xx = x + 8
                tot_w = (w - 50) * sum(v) / c['_max']
                for k, part in enumerate(v):
                    pw_ = tot_w * part / sum(v) if sum(v) else 0
                    f.rect(xx, cy - 13, pw_ - 1, 26, c['_cols'][k])
                    if pw_ > f.tw(num(part), 'small') + 8:
                        f.text(xx + pw_ / 2, cy + 5, num(part), 'small', 'on_dark' if c['_cols'][k] in DARK else 'ink', 400, 'middle')
                    xx += pw_
                f.text(xx + 6, cy + 5, num(sum(v)), 'small', 'ink', 700)
            elif t == 'bars':
                n = len(v)
                bh = min(12, (rh - 12) / n - 2)
                for k, part in enumerate(v):
                    yy = cy - (n * (bh + 2)) / 2 + k * (bh + 2)
                    bw = (w - 44) * part / c['_max']
                    f.rect(x + 8, yy, bw, bh, c['_cols'][k])
                    f.text(x + 12 + bw, yy + bh - 1, num(part), 'note', 'ink')
        y += rh
    f.line(0, y, f.w, y, 'line_strong', 1)
    # легенда частей
    for c, x in zip(columns, xs):
        if c['type'] in ('stack', 'bars'):
            lx = x + 8
            for k, p in enumerate(c['parts']):
                f.rect(lx, y + 14, 11, 11, c['_cols'][k])
                f.text(lx + 16, y + 24, p, 'note', 'muted')
                lx += f.tw(p, 'note') + 30
            y += 30
    return f.finish(y + 6, rule=head_rule)


def heat_grid(metrics, items, values, *, groups=None, total=None, scale=(1, 10), legend_steps=5, rotate=None,
              decimals=1, theme=None, mode='показ', width=None):
    """Тепловая сетка точками: объекты в колонках, показатели в строках, цвет вместо чисел.

    metrics: имена строк; items: имена колонок; values: {item: [значение по metrics]}.
    groups: [('Лидеры инноваций', ['Утрехт', 'Хельсинки']), ...] шапки групп над колонками.
    total: {item: число} строка итоговой оценки столбиками сверху.
    rotate: подписи колонок вертикально (по умолчанию, если не влезают).
    """
    f = Fig(theme, mode, width, 'Тепловая сетка')
    need(len(items) <= 40 and len(metrics) <= 12, 'колонок до 40, строк до 12')
    lw = min(max(f.tw(m, 'label') for m in metrics) + 24, 220)
    ng = len(groups) if groups else 1
    gap = 14 if groups else 0
    cw = (f.w - lw - gap * (ng - 1)) / len(items)
    if rotate is None:
        rotate = max(f.tw(i, 'small') for i in items) > cw - 6
    order = [it for _, its in groups for it in its] if groups else list(items)
    xs = {}
    x = lw
    gi = 0
    if groups:
        for gname, its in groups:
            gx = x
            for it in its:
                xs[it] = x + cw / 2
                x += cw
            f.para(gx, 18, gname, len(its) * cw - 8, 'label', 'ink', 700, 3, what='имя группы', lh=18)
            f.line(gx, 0, gx, 4, 'line', 1)
            x += gap
    else:
        for it in items:
            xs[it] = x + cw / 2
            x += cw
    y_names = 80 if groups else 10
    name_h = max(f.tw(i, 'small') for i in items) + 10 if rotate else 24
    for it in order:
        if rotate:
            yy = y_names + name_h
            f.el.append(f'<text x="{xs[it] + 5:.1f}" y="{yy:.1f}" transform="rotate(-90 {xs[it] + 5:.1f} {yy:.1f})" '
                        f'style="font-size:{f.s("small")}px" fill="{f.c("ink")}">{it}</text>')
        else:
            f.text(xs[it], y_names + 16, it, 'small', 'ink', 400, 'middle')
    y = y_names + name_h + 12
    if total:
        th_ = 44
        tmax = max(total.values())
        for it in order:
            h = th_ * total[it] / tmax
            tone = _tone(f.th, total[it], scale)
            f.rect(xs[it] - cw * 0.3, y + th_ - h, cw * 0.6, h, tone)
            f.text(xs[it], y + th_ + 18, num(total[it], decimals), 'small', 'ink', 700, 'middle')
        f.text(0, y + th_ + 18, 'Итоговая оценка', 'label', 'ink', 700)
        y += th_ + 30
    rh = 38
    r = min(cw * 0.36, 11)
    for mi, m in enumerate(metrics):
        cy = y + rh / 2
        f.para(0, cy + 5, m, lw - 14, 'label', 'ink', max_lines=1, what='имя показателя')
        for it in order:
            f.circle(xs[it], cy, r, _tone(f.th, values[it][mi], scale))
        y += rh
    # легенда
    lo, hi = scale
    y += 18
    f.text(0, y + 5, 'Шкала:', 'small', 'muted', 700)
    lx = lw
    steps = f.th.ramp
    for k, tone in enumerate(steps):
        a = lo + (hi - lo) * k / len(steps)
        b = lo + (hi - lo) * (k + 1) / len(steps)
        f.circle(lx + 8, y, 8, tone)
        lab = f'{num(a, 0)}–{num(b, 0)}'
        f.text(lx + 22, y + 5, lab, 'small', 'muted')
        lx += 40 + f.tw(lab, 'small')
    return f.finish(y + 16)
