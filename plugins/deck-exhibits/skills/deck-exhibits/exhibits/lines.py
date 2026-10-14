"""Динамика линиями: как менялось во времени."""
from .core import Fig, need, num, nice_max, Exhibit


def _ticks(lo, hi, n=5):
    import math
    span = hi - lo
    raw = span / (n - 1)
    e = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = min((m * e for m in (1, 2, 2.5, 5, 10) if m * e >= raw), default=raw)
    start = math.floor(lo / step) * step
    out = []
    v = start
    out.append(round(v, 10))
    while v < hi - step * 0.01:
        v += step
        out.append(round(v, 10))
    return out


def lines(x, series, *, highlight=None, unit='', decimals=0, events=None, bands=None, gap_fill=None, table=None,
          y_from_zero=None, height=340, end_labels=True, title=None, sub=None, top_min=None, theme=None, mode='показ', width=None):
    """Линии по времени. Главная серия акцентом, остальные серым; подпись имени и последнего значения у конца линии.

    x: подписи точек по оси (годы, месяцы); прореживаются автоматически.
    series: {имя: [значения или None]}; больше 4 серий: только с table или с highlight одной-двух.
    highlight: имена серий акцентом (первая accent, вторая accent_dark); без него при одной серии она акцентная.
    events: [(индекс, 'Начало пандемии')] вертикальные пунктиры с подписью сверху.
    bands: [(i0, i1, 'подпись')] светлые полосы периодов (эпохи, сроки руководителей).
    gap_fill: ('Факт', 'План', '1 026 FTE сверх плана') заливка между двумя сериями там, где первая выше.
    table: {'cols': ['2025', 'среднее'], 'values': {имя: [..]}, 'decimals': 1} легенда-таблица справа вместо подписей у линий.
    title, sub: заголовок панели и единицы под ним (для малых кратных).
    """
    f = Fig(theme, mode, width, 'Линии')
    names = list(series)
    n = len(x)
    need(n >= 3, 'для линии нужно хотя бы 3 точки; меньше: столбцы')
    for k in names:
        need(len(series[k]) == n, f'серия {k}: {len(series[k])} точек при {n} подписях')
    if highlight is None:
        highlight = names[:1] if len(names) == 1 else []
    need(len(names) <= 4 or table or len(highlight) <= 2, 'больше четырёх линий без выделения не читается: выдели 1–2 или дай table')
    hl_col = {}
    for i, k in enumerate(highlight):
        hl_col[k] = ['accent', 'accent_dark', 'accent_soft'][min(i, 2)]
    vals = [v for k in names for v in series[k] if v is not None]
    lo, hi = min(vals), max(vals)
    if y_from_zero is None:
        y_from_zero = lo >= 0 and lo < (hi - lo) * 0.6
    if y_from_zero:
        lo = min(0, lo)
    ticks = _ticks(lo, hi)
    lo, hi = ticks[0], ticks[-1]
    top = 20 + (14 if unit else 0)
    if title:
        f.para(0, 18, title, f.w * 0.9, 'label', 'ink', 700, 2, what='заголовок панели')
        top += 22
        if sub:
            f.text(0, top + 14, sub, 'small', 'muted')
            top += 18
        top += 16
    if events:
        top += 40
    yax = max(f.tw(num(t, decimals), 'small') for t in ticks) + 12
    right_w = 0
    if table:
        right_w = 70 + max(f.tw(k, 'label') for k in names) + 76 * len(table['cols'])
    elif end_labels:
        right_w = max(f.tw(k, 'small', 700) + f.tw(num([v for v in series[k] if v is not None][-1], decimals), 'small', 700) + 30 for k in names)
    x0, x1 = yax, f.w - right_w - 10
    top = max(top, top_min or 0)
    base = top + height

    def X(i):
        return x0 + (x1 - x0) * i / (n - 1)

    def Y(v):
        return base - height * (v - lo) / (hi - lo)
    if bands:
        for j, (a, b, lab) in enumerate(bands):
            f.rect(X(a), top, X(b) - X(a), height, 'surface' if j % 2 == 0 else 'accent_pale')
            if lab:
                f.para(X(a) + 6, top + 18, lab, X(b) - X(a) - 10, 'note', 'muted', max_lines=2, what='подпись полосы')
    for t in ticks:
        f.line(x0, Y(t), x1, Y(t), 'line_soft' if t != 0 else 'line_strong', 1)
        f.text(x0 - 10, Y(t) + 5, num(t, decimals), 'small', 'muted', 400, 'end')
    if unit:
        f.text(0, top - 12, unit, 'small', 'muted')
    step = max(1, round(n / 10))
    for i in range(0, n, step):
        f.text(X(i), base + 22, str(x[i]), 'small', 'muted', 400, 'middle')
    if (n - 1) % step:
        f.text(X(n - 1), base + 22, str(x[-1]), 'small', 'muted', 400, 'middle')
    if events:
        for idx, lab in events:
            f.line(X(idx), top - 34, X(idx), base, 'line_strong', 1, '3 3')
            t = f.wrap(lab, 200, 'small', 400, 2, 'подпись события')
            f.text(X(idx) - 6, top - 32 + 14, t, 'small', 'ink', 400, 'end', lh=17)
    if gap_fill:
        a, b, lab = gap_fill
        pa, pb = series[a], series[b]
        pts_top = [(X(i), Y(pa[i])) for i in range(n) if pa[i] is not None and pb[i] is not None]
        pts_bot = [(X(i), Y(max(pb[i], min(pa[i], pb[i])))) for i in range(n) if pa[i] is not None and pb[i] is not None]
        f.poly(pts_top + pts_bot[::-1], 'accent_pale')
        if lab:
            k = max(range(n), key=lambda i: (pa[i] or 0) - (pb[i] or 0))
            f.text(X(k), (Y(pa[k]) + Y(pb[k])) / 2 + 5, lab, 'small', 'accent', 700, 'middle')
    order = [k for k in names if k not in hl_col] + [k for k in names if k in hl_col]
    ends = []
    for k in order:
        pts = [(X(i), Y(v)) for i, v in enumerate(series[k]) if v is not None]
        on = k in hl_col
        col = hl_col.get(k, 'grey')
        d = 'M' + ' L'.join(f'{px:.1f},{py:.1f}' for px, py in pts)
        dash = '6 4' if gap_fill and k == gap_fill[1] else None
        f.path(d, col, 3 if on else 1.8, dash=dash)
        lx, ly = pts[-1]
        if on:
            f.circle(lx, ly, 4.5, col)
        last_v = [v for v in series[k] if v is not None][-1]
        ends.append([ly, k, col, on, last_v, lx])
    if table:
        tx = x1 + 30
        cw = 76
        nx = tx + 30
        for j, c in enumerate(table['cols']):
            f.text(nx + max(f.tw(k, 'label') for k in names) + 20 + j * cw + cw - 8, top + 2, c, 'small', 'muted', 700, 'end')
        yy = top + 34
        for k in names:
            col = hl_col.get(k, 'grey')
            f.line(tx, yy - 5, tx + 22, yy - 5, col, 3 if k in hl_col else 2)
            f.text(nx, yy, k, 'label', 'ink', 700 if k in hl_col else 400)
            for j, v in enumerate(table['values'][k]):
                f.text(nx + max(f.tw(q, 'label') for q in names) + 20 + j * cw + cw - 8, yy, num(v, table.get('decimals', 1)), 'label', 'ink', 700 if k in hl_col else 400, 'end')
            f.line(nx, yy + 12, f.w, yy + 12, 'line_soft', 1)
            yy += 34
    elif end_labels:
        ends.sort(key=lambda e: e[0])
        gap = f.s('small') + 4
        for i in range(1, len(ends)):
            if ends[i][0] - ends[i - 1][0] < gap:
                ends[i][0] = ends[i - 1][0] + gap
        for ly, k, col, on, v, lx in ends:
            lab = num(v, decimals) if len(names) == 1 else f'{num(v, decimals)}  {k}'
            f.text(lx + 12, ly + 5, lab, 'small' if len(names) > 1 else 'label', col if on else 'muted', 700 if on else 400)
    return f.finish(base + 34, base=base, top=top)


def hstack(exhibits, gap=40, theme=None, name='Ряд рисунков'):
    """Несколько рисунков в ряд одним SVG (малые кратные: строй каждый с width=(W - gap*(n-1))/n)."""
    import re
    th = exhibits[0]
    total_w = sum(e.w for e in exhibits) + gap * (len(exhibits) - 1)
    # таблицы в ряду: линии под шапками на одной высоте (сдвигаем вниз ту, у которой шапка ниже ростом)
    rules = [e.rule for e in exhibits]
    if len(exhibits) > 1 and all(r is not None for r in rules):
        offs = [max(rules) - r for r in rules]
    else:
        offs = [0] * len(exhibits)
    h = max(e.h + o for e, o in zip(exhibits, offs))
    parts = []
    x = 0
    warns = []
    for e, o in zip(exhibits, offs):
        inner = re.sub(r'^<svg[^>]*>', '', e.svg)[:-6]
        parts.append(f'<svg x="{x}" y="{o}" width="{e.w}" height="{e.h}" viewBox="0 0 {e.w} {e.h}">{inner}</svg>')
        x += e.w + gap
        warns += e.warnings
    bases = [e.base for e in exhibits if e.base is not None]
    if len(bases) > 1 and max(bases) - min(bases) > 1:
        warns.append(f'оси рисунков в ряду не на одной горизонтали ({", ".join(f"{b:.0f}" for b in bases)}); собирай ряд через X.panels')
    style = re.search(r'style="([^"]*)"', exhibits[0].svg).group(1)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {h}" width="100%" role="img" aria-label="{name}" '
           f'style="{style}">' + ''.join(parts) + '</svg>')
    return Exhibit(svg, total_w, h, warns, name)


def panels(builders, gap=40, width=None, name='Панели'):
    """Графики в ряд на общей оси: шапки, верх поля и ось X у всех панелей на одной горизонтали.

    builders: [lambda **kw: X.columns(..., title='…', sub='…', **kw), lambda **kw: X.lines(..., **kw)]
    Функция вызывает каждый построитель дважды: сначала узнаёт, сколько места сверху нужно каждой панели
    (скобка роста, выноска, легенда), потом строит все с общим верхом поля. Высоту поля (height) задай одинаковую.
    """
    from .core import load_theme
    full = width or load_theme().width
    w = (full - gap * (len(builders) - 1)) / len(builders)
    first = [b(width=w) for b in builders]
    need_top = [e.top for e in first]
    if None in need_top:
        raise ValueError('panels: каждая панель должна уметь top_min (columns, lines)')
    top = max(need_top)
    exs = [b(width=w, top_min=top) for b in builders]
    return hstack(exs, gap=gap, name=name)
