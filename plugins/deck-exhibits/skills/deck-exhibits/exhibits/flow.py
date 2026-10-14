"""Процессы и время: этапы со строками и воротами, Гант, дорожки событий, шкала вариантов, дерево драйверов,
карта сегментов, слои стека."""
from .core import Fig, FitError, need, num

DARK = {'accent', 'accent_dark', 'accent_mid', 'accent_soft', 'good', 'bad'}


def stages(phases, *, rows=None, gates=None, label_w=170, decision_row=None, cell_role='small', flat=False, theme=None, mode='показ', width=None):
    """Этапы шевронами и строки под ними: что делаем, результат, кто участвует. Тон нарастает к последнему этапу.

    phases: [{'title': 'Обследование', 'sub': '2 недели, октябрь'}] 2–6 штук.
    rows: [{'label': 'Что делаем', 'cells': ['текст' или ['пункт', 'пункт'], ...]}] по ячейке на этап.
          Пункты списка понимают **жирный ключ**. Без label у всех строк колонка подписей не рисуется (схема «вход → как → результат»).
    gates: [{'after': 0, 'label': 'Решение о запуске', 'items'?: [...]}] ворота-ромбы между этапами (after: индекс этапа, -1 = до первого).
    decision_row: подпись строки, которая выделяется акцентом (например, «Решение на выходе»).
    cell_role: кегль ячеек, 'small' или 'label' (крупнее, когда строк мало и на слайде есть место).
    flat: плоские блоки без шевронов и крупные заголовки (для цепочки доводов «риски → полномочия → практика», где нет хода времени).
    """
    f = Fig(theme, mode, width, 'Этапы')
    f.text_scheme = True
    clh = round(f.s(cell_role) * 1.35)
    n = len(phases)
    need(2 <= n <= 6, 'этапов 2–6; больше 5 читается тяжело (Миллерд)')
    lx = label_w if rows and any(r.get('label') for r in rows) else 0
    sw = (f.w - lx) / n
    # тон нарастает к последнему этапу, соседние этапы всегда разного тона
    tones = {2: ['accent', 'accent_dark'], 3: ['accent', 'accent_mid', 'accent_dark'],
             4: ['accent_soft', 'accent', 'accent_mid', 'accent_dark'],
             5: ['accent_light', 'accent_soft', 'accent', 'accent_mid', 'accent_dark'],
             6: ['accent_pale', 'accent_light', 'accent_soft', 'accent', 'accent_mid', 'accent_dark']}[n]
    y0 = 24 if gates else 0
    sh = 64
    gap_ = 12 if flat else 4
    bw_ = (f.w - lx - gap_ * (n - 1)) / n      # последний блок доходит ровно до правого края рисунка (правило стиля v3)
    for i, p in enumerate(phases):
        x = lx + i * (bw_ + gap_)
        tone = tones[i]
        tc = 'on_dark' if tone in DARK else 'ink'
        if flat:
            f.rect(x, y0, bw_, sh, tone)
            tx = x + 18
            f.para(tx, y0 + (34 if not p.get('sub') else 28), p['title'], sw - 48, 'head', tc, 700, 1, what='название этапа')
        else:
            f.seg(x, y0, bw_, sh, tone, first=(i == 0), last=(i == n - 1), tip=16)
            tx = x + (18 if i == 0 else 30)
            f.para(tx, y0 + 28, p['title'], sw - 54, 'label', tc, 700, 1, what='название этапа')
        if p.get('sub'):
            f.para(tx, y0 + 50, p['sub'], sw - 54, 'small', tc, 400, 1, what='срок этапа')
    if gates:
        for g in gates:
            gx = lx + (g['after'] + 1) * sw - 2
            gx = min(max(gx, lx + 10), f.w - 10)
            f.diamond(gx, y0 - 10, 9, 'accent')
    y = y0 + sh + 20
    if rows:
        for r in rows:
            dec = r.get('label') == decision_row and decision_row is not None
            f.line(0, y, f.w, y, 'line', 1)
            if r.get('label'):
                f.para(0, y + 28, r['label'], lx - 16, 'label', 'ink', 700, 2, what='подпись строки', lh=18)
            hmax = 24
            for i, cell in enumerate(r['cells']):
                cx = lx + i * sw + (18 if i == 0 else 30)
                cw = sw - (36 if i == 0 else 44)
                yy = y + 28
                if isinstance(cell, (list, tuple)):
                    for it in cell:
                        f.circle(cx + 3, yy - 5, 2.5, 'accent' if dec else 'muted')
                        if '**' in it:
                            yy += f.rich(cx + 14, yy, it, cw - 14, cell_role, 'ink', max_lines=3, lh=clh, what='пункт ячейки') + 9
                        else:
                            yy += f.para(cx + 14, yy, it, cw - 14, cell_role, 'accent' if dec else 'ink', 700 if dec else 400, 3, what='пункт ячейки', lh=clh) + 9
                    hmax = max(hmax, yy - y - 18)
                else:
                    if '**' in cell:
                        h = f.rich(cx, yy, cell, cw, cell_role, 'ink', max_lines=5, lh=clh, what='ячейка')
                    else:
                        h = f.para(cx, yy, cell, cw, cell_role, 'accent' if dec else 'ink', 700 if dec else 400, 5, what='ячейка', lh=clh)
                    hmax = max(hmax, h + 10)
            y += hmax + 26
        f.line(0, y, f.w, y, 'line', 1)
    if gates and any(g.get('items') or g.get('label') for g in gates):
        y += 18
        for g in gates:
            gx = lx + (g['after'] + 1) * sw - 2
            gw = min(sw - 16, 240)
            x0 = gx - gw if g['after'] >= 0 else gx       # плашка под этапом, который ворота закрывают
            x0 = min(max(x0, 0), f.w - gw)
            f.line(gx, y0, gx, y + 4, 'accent', 1, '2 3')
            t = f.wrap(g['label'], gw - 20, 'small', 700, 2, 'подпись ворот')
            hh = 16 + 18 * (t.count('\n') + 1)
            f.rect(x0, y + 4, gw, hh, 'accent_pale')
            f.text(x0 + gw / 2, y + 22, t, 'small', 'accent_dark', 700, 'middle', lh=18)
            yy = y + 4 + hh + 22
            for it in g.get('items', []):
                yy += f.para(x0 + 6, yy, '• ' + it, gw - 12, 'small', 'ink', max_lines=3, what='условие ворот', lh=18) + 6
    return f.finish()


def gantt(periods, tasks, *, label_w=300, milestones=None, today=None, period_label=None, groups=None, theme=None, mode='показ', width=None):
    """Дорожная карта Гантом: полосы работ по периодам, вехи ромбами, «сегодня» пунктиром.

    periods: ['Нед 1', ..., 'Нед 8'] или месяцы; координаты задач в индексах периодов, дробные можно.
    tasks: [{'label': 'Обследование', 'start': 0, 'end': 2, 'kind'?: 'main'|'side'|'accent', 'note'?: '2 недели', 'group'?: 'Наши работы'}]
    milestones: [(4.5, 'Решение о закупке')]; today: позиция пунктира.
    """
    f = Fig(theme, mode, width, 'Гант')
    need(1 <= len(tasks) <= 14, 'работ 1–14; больше: группировать')
    n = len(periods)
    grouped = any(t.get('group') for t in tasks)
    gl = 120 if grouped else 0
    lx = gl + label_w
    cw = (f.w - lx) / n

    def X(v):
        return lx + v * cw
    top = 30
    for k, p in enumerate(periods):
        f.text(X(k) + cw / 2, 18, str(p), 'small', 'muted', 700, 'middle')
        if k:
            f.line(X(k), top, X(k), top + len(tasks) * 40, 'line_soft', 1)
    f.line(0, top, f.w, top, 'ink', 1.2)
    y = top
    cur = None
    kinds = {'main': 'accent_dark', 'side': 'grey', 'accent': 'accent'}
    for t in tasks:
        if grouped and t.get('group') != cur:
            if cur is not None:
                f.line(0, y, f.w, y, 'line_strong', 1)
            cur = t.get('group')
            f.para(0, y + 26, cur, gl - 12, 'small', 'muted', 700, 2, what='группа работ', lh=17)
        col = kinds[t.get('kind', 'main')]
        f.para(gl, y + 26, t['label'], label_w - 12, 'label', 'ink', 700 if t.get('kind') == 'accent' else 400, 1, what='работа')
        xa, xb = X(t['start']), X(t['end'])
        f.rect(xa + 2, y + 12, xb - xa - 4, 18, col)
        if t.get('note'):
            nx = xb + 8
            if nx + f.tw(t['note'], 'small') > f.w:
                f.text(xa - 8, y + 26, t['note'], 'small', 'ink', 400, 'end')
            else:
                f.text(nx, y + 26, t['note'], 'small', 'ink')
        f.line(gl, y + 40, f.w, y + 40, 'line_soft', 1)
        y += 40
    f.line(0, y, f.w, y, 'line_strong', 1)
    if today is not None:
        f.line(X(today), top - 6, X(today), y, 'accent', 1.5, '4 3')
        f.text(X(today) + 6, y + 18, 'сегодня', 'note', 'accent', 700)
    if milestones:
        f.text(0, y + 40, 'Вехи', 'label', 'muted', 700)
        for v, lab in milestones:
            xx = min(max(X(v), lx + 9), f.w - 9)   # ромб на краю шкалы целиком внутри рисунка
            f.diamond(xx, y + 34, 9, 'accent')
            f.line(xx, top, xx, y + 24, 'accent', 1, '2 3')
            anchor = 'end' if xx > f.w - 80 else 'start' if xx < lx + 60 else 'middle'
            f.para(min(xx + (6 if anchor == 'end' else 0), f.w), y + 66, lab, 190, 'small', 'ink', 700, 2, anchor=anchor, what='веха', lh=18)
        y += 100
    return f.finish(y + 4)


def lanes(lanes_, *, scale=None, kinds=None, label_w=230, theme=None, mode='показ', width=None):
    """Дорожки событий: малые кратные таймлайнов, по дорожке на страну, команду или продукт; цвет маркера = тип события.

    lanes_: [{'name': 'Индия', 'note': 'От общенационального к точечному', 'events': [(0.1, '25 мар', 'Общий карантин', 'start'), ...]}]
            позиция события от 0 до 1 по шкале; дата и подпись над осью.
    kinds: {'start': ('Начало ограничений', 'accent_dark'), 'ease': ('Смягчение', 'accent_light')}
    """
    f = Fig(theme, mode, width, 'Дорожки событий')
    need(1 <= len(lanes_) <= 5, 'дорожек 1–5')
    x0, x1 = label_w + 24, f.w - 20
    y = 0
    for ln in lanes_:
        ev = sorted(ln['events'], key=lambda e: e[0])
        need(len(ev) <= 8, f'«{ln["name"]}»: событий не больше восьми')
        lh = 120
        f.rect(0, y, label_w, lh - 14, 'surface')
        f.text(16, y + 30, ln['name'], 'head', 'accent_dark', 700)
        if ln.get('note'):
            f.para(16, y + 54, ln['note'], label_w - 32, 'small', 'muted', max_lines=3, what='пояснение дорожки', lh=17)
        ay = y + lh - 40
        f.line(x0, ay, x1, ay, 'ink', 1.2)
        slot = (x1 - x0) / max(len(ev), 1)
        for pos, date, lab, kind in ev:
            xx = x0 + (x1 - x0) * pos
            f.circle(xx, ay, 4, 'ink')
            f.text(xx, ay + 36, date, 'small', 'ink', 400, 'middle')
            col = kinds[kind][1] if kinds and kind in kinds else 'accent'
            f.poly([(xx - 6, ay + 18), (xx, ay + 8), (xx + 6, ay + 18)], col)
            f.para(xx, ay - 46, lab, min(slot - 6, 150), 'small', col if col != 'accent_light' else 'accent_soft', 700, 3, anchor='middle', what='событие', lh=16)
        y += lh + 10
    if kinds:
        lx = x0
        for k, (lab, col) in kinds.items():
            f.rect(lx, y, 12, 12, col)
            f.text(lx + 18, y + 11, lab, 'small', 'muted')
            lx += 40 + f.tw(lab, 'small')
        y += 20
    return f.finish(y + 4)


def spectrum(options, *, ends=('Всё делаем сами', 'Всё отдаём партнёру'), verdict=None, current=None, theme=None, mode='показ', width=None):
    """Шкала вариантов: от одного края к другому, варианты метками-указателями, под каждым суть и следствие.

    options: [{'title': 'Свой продукт', 'text': 'Всё разрабатываем внутри', 'effect': '**Полный контроль**, но медленно'}] 3–5.
    current: индекс варианта, где мы сейчас (метка акцентом).
    verdict: вывод полосой внизу.
    """
    f = Fig(theme, mode, width, 'Шкала вариантов')
    f.text_scheme = True
    n = len(options)
    need(3 <= n <= 5, 'вариантов 3–5')
    cw = f.w / n
    f.poly([(0, 0), (f.w, 22), (f.w, 34), (0, 34)], 'accent_pale')
    f.poly([(0, 0), (f.w, 34), (0, 34)], 'accent_dark')
    f.text(12, 26, ends[0], 'small', 'on_dark', 700)
    f.text(f.w - 12, 18, ends[1], 'small', 'accent_dark', 700, 'end')
    roman = ['I', 'II', 'III', 'IV', 'V']
    ybody = 0
    for i, o in enumerate(options):
        cx = i * cw + cw / 2
        on = current == i
        col = 'accent' if on else 'accent_dark'
        f.circle(cx, 72, 20, col)
        f.poly([(cx - 9, 86), (cx + 9, 86), (cx, 102)], col)
        f.text(cx, 78, roman[i], 'label', 'on_dark', 700, 'middle', check=False)
        h = f.para(cx, 132, o['title'], cw - 24, 'label', 'ink', 700, 2, anchor='middle', what='вариант', lh=19)
        h2 = f.para(cx, 132 + h + 14, o['text'], cw - 30, 'small', 'muted', max_lines=4, anchor='middle', what='суть варианта', lh=18)
        ybody = max(ybody, 132 + h + 14 + h2)
    y = ybody + 26
    for i, o in enumerate(options):
        cx = i * cw + cw / 2
        f.poly([(cx - 12, y), (cx, y + 10), (cx + 12, y), (cx + 12, y + 6), (cx, y + 16), (cx - 12, y + 6)], 'accent')
        if o.get('effect'):
            f.rich(i * cw + 14, y + 44, o['effect'], cw - 28, 'small', 'ink', key_color='accent', max_lines=4, lh=18, what='следствие')
    y += 44 + 4 * 18 + 10
    if verdict:
        f.rect(0, y, f.w, 44, 'accent_dark')
        f.text(f.w / 2, y + 28, verdict, 'label', 'on_dark', 700, 'middle')
        y += 44
    return f.finish(y + 2)


def driver_tree(tree, *, classes=None, row_h=None, widths=None, max_h=470, legend=True, dashed_label='гипотеза, цифры нет',
                theme=None, mode='показ', width=None):
    """Дерево драйверов слева направо: корень, ветки, оператор на стыке (× + −), единицы в скобках.

    tree: {'label': 'Выручка [млн ₽]', 'op': '×', 'children': [...]} или 'ops': ['×', '−'] между соседними ветками;
          у узла 'cls' (класс из classes: цвет несёт владельца или вид), 'dashed': True (пунктирная рамка),
          'kind': 'assume' (лист-допущение светлее). В подписи допустим **жирный** (метка ML и т. п.).
    classes: {'core': ('ядро', 'accent_pale'), 'com': ('коммерция', 'cat_3')} легенда классов в пустом углу под корнем.
    dashed_label: подпись пунктира в легенде (что значит пунктирная рамка).
    row_h: высота листа; по умолчанию 52 при малом дереве и компактно при большом.
    widths: ширины колонок по уровням, последняя колонка (листья) получает остаток.
    Глубина до 4. Число листьев не ограничено числом: дерево проверяется по высоте (max_h), не влезло: FitError с подсказкой разбить.
    """
    f = Fig(theme, mode, width, 'Дерево драйверов')
    levels = []

    def depth(nd, d=0):
        levels.append(d)
        for c in nd.get('children', []):
            depth(c, d + 1)
    depth(tree)
    D = max(levels) + 1
    need(D <= 4, 'глубина дерева до 4 уровней')

    def leaves(nd):
        ch = nd.get('children', [])
        return 1 if not ch else sum(leaves(c) for c in ch)
    L = leaves(tree)
    rh = row_h or (52 if L <= 8 else round(f.s('small') * 1.35) + 12)
    gap_x = 34
    if widths:
        ws = list(widths) + [None] * (D - len(widths))
    else:
        ws = [min(200, (f.w - (D - 1) * gap_x) / D)] * (D - 1) + [None]
    xs = [0]
    for d in range(D - 1):
        xs.append(xs[-1] + ws[d] + gap_x)
    ws[D - 1] = f.w - xs[D - 1]
    gap_grp = 8                       # зазор между группами листьев у разных родителей
    pos = {}
    cur = [0.0]

    def place(nd, d):
        ch = nd.get('children', [])
        if not ch:
            cy = cur[0] + rh / 2
            cur[0] += rh + (4 if rh >= 30 else 3)
        else:
            if all(not c.get('children') for c in ch) and cur[0] > 0:
                cur[0] += gap_grp
            cys = [place(c, d + 1) for c in ch]
            cy = (cys[0] + cys[-1]) / 2
        pos[id(nd)] = (xs[d], cy, ws[d])
        return cy
    place(tree, 0)
    H = cur[0]
    if H > max_h:
        raise FitError(f'{f.name}: {L} листьев дают высоту {H:.0f}px при пределе {max_h}px; '
                       f'сократи подписи до одной строки, уменьши row_h или разбей дерево на два')
    classes = classes or {}
    if classes:
        plain = set()

        def walk(nd, d):
            ch = nd.get('children', [])
            if d and not nd.get('cls'):
                plain.add(('accent' if d == 1 else 'surface') if ch else ('accent_light' if nd.get('kind') == 'assume' else 'accent_pale'))
            for c in ch:
                walk(c, d + 1)
        walk(tree, 0)
        f.check_classes({lab: role for lab, role in classes.values()}, sorted(plain))

    def draw(nd, d):
        x, cy, bw = pos[id(nd)]
        ch = nd.get('children', [])
        if d == 0:
            tone = 'accent_dark'
        elif nd.get('cls'):
            tone = classes[nd['cls']][1]
        elif ch:
            tone = 'accent' if d == 1 else 'surface'
        else:
            tone = 'accent_light' if nd.get('kind') == 'assume' else 'accent_pale'
        tc = 'on_dark' if tone in DARK else 'ink'
        role = 'small'
        lab = nd['label']
        lh = round(f.s(role) * 1.25)
        if '**' in lab:
            nl = f.rich_lines(lab, bw - 18, role, 2, 'узел дерева')
        else:
            nl = f.wrap(lab, bw - 18, role, 700 if d < 2 or ch else 400, 3, 'узел дерева').count('\n') + 1
        h = max(rh, lh * nl + (8 if rh < 30 else 16))   # плашка не выше шага строки: листья не налезают
        f.rect(x, cy - h / 2, bw, h, tone, stroke='line_strong' if nd.get('dashed') else None, dash='4 3' if nd.get('dashed') else None)
        ty = cy - (nl - 1) * lh / 2 + f.s(role) * 0.35
        if '**' in lab:
            f.rich(x + 9, ty, lab, bw - 18, role, tc, max_lines=2, lh=lh, what='узел дерева')
        else:
            f.para(x + 9, ty, lab, bw - 18, role, tc, 700 if d < 2 or ch else 400, 3, what='узел дерева', lh=lh)
        if ch:
            jx = x + bw + gap_x / 2
            f.line(x + bw, cy, jx, cy, 'line_strong', 1)
            ys = [pos[id(c)][1] for c in ch]
            f.line(jx, min(ys), jx, max(ys), 'line_strong', 1)
            for c in ch:
                f.line(jx, pos[id(c)][1], pos[id(c)][0], pos[id(c)][1], 'line_strong', 1)
            ops = nd.get('ops') or ([nd['op']] * (len(ch) - 1) if nd.get('op') else [])
            if nd.get('op') and len(ch) > 1 and not nd.get('ops'):
                ops_at = [(min(ys) + max(ys)) / 2]
                ops = [nd['op']]
            else:
                ops_at = [(ys[k] + ys[k + 1]) / 2 for k in range(len(ops))]
            for o, oy in zip(ops, ops_at):
                f.circle(jx, oy, 9, 'bg', 'line_strong', 1.2)
                f.text(jx, oy + 4.5, o, 'small', 'ink', 700, 'middle', check=False)
            for c in ch:
                draw(c, d + 1)
    draw(tree, 0)
    if legend and classes:
        # легенда в пустой колонке корня, под ним
        _, ry, rw = pos[id(tree)]
        items = list(classes.values()) + ([(dashed_label, 'dashed')] if _any_dashed(tree) else [])
        lw_ = rw - 24 + gap_x - 6
        hs = [max(22, 16 * f.wrap(lab, lw_, 'note', 400, 2, 'легенда дерева').count('\n') + 22) for lab, _ in items]
        yy = max(ry + 60, H - sum(hs) + 12)
        for (lab, role_), hk in zip(items, hs):
            if role_ == 'dashed':
                f.rect(0, yy - 11, 16, 13, 'bg', stroke='line_strong', dash='3 2')
            else:
                f.rect(0, yy - 11, 16, 13, role_, stroke='line' if role_ in ('bg', 'surface') else None)
            f.para(24, yy, lab, lw_, 'note', 'muted', 400, 2, what='легенда дерева', lh=16)
            yy += hk
        H = max(H, yy - 12)                # рисунок растёт под легенду, а не режет её
    elif legend and any(_kinds(tree)):
        f.rect(0, H + 14, 14, 14, 'accent_pale')
        f.text(20, H + 25, 'считаем из данных', 'note', 'muted')
        f.rect(170, H + 14, 14, 14, 'accent_light')
        f.text(190, H + 25, 'допущение', 'note', 'muted')
        H += 30
    return f.finish(H + 4)


def _any_dashed(nd):
    return nd.get('dashed') or any(_any_dashed(c) for c in nd.get('children', []))


def _kinds(nd):
    yield nd.get('kind') == 'assume'
    for c in nd.get('children', []):
        yield from _kinds(c)


def segment_map(segments, *, metrics=(), metric_labels=(), label_w=150, row_label='Состав', theme=None, mode='показ', width=None):
    """Карта сегментов: колонки-сегменты, под шапкой строки метрик плашками, ниже плитки состава. «Вселенная» продуктов по группам.

    segments: [{'title': 'Вычисления и чипы', 'icon'?: 'cpu', 'metrics': ['$40 | $70', '~20%'], 'items': ['Подложки', ...], 'hl'?: True}]
    metric_labels: подписи строк метрик слева.
    """
    f = Fig(theme, mode, width, 'Карта сегментов')
    f.text_scheme = True
    n = len(segments)
    need(2 <= n <= 6, 'сегментов 2–6')
    gap = 8
    cw = (f.w - label_w - gap * (n - 1)) / n
    th = max(f.wrap(s['title'], cw - 20, 'label', 700, 3, 'сегмент').count('\n') + 1 for s in segments)
    hh = 30 + th * 19 + (30 if any(s.get('icon') for s in segments) else 0)
    for i, s in enumerate(segments):
        x = label_w + i * (cw + gap)
        tone = 'accent_dark' if s.get('hl') or not any(q.get('hl') for q in segments) else 'accent_soft'
        f.rect(x, 0, cw, hh, tone)
        yy = 26
        if s.get('icon'):
            f.icon(s['icon'], x + cw / 2, 22, 24, 'on_dark')
            yy = 58
        f.text(x + cw / 2, yy, f.wrap(s['title'], cw - 20, 'label', 700, 3, 'сегмент'), 'label', 'on_dark', 700, 'middle', lh=19)
    f.text(0, hh / 2 + 5, 'Сегменты', 'label', 'ink', 700)
    y = hh + 8
    for k, ml in enumerate(metric_labels):
        f.para(0, y + 25, ml, label_w - 12, 'small', 'ink', 700, 2, what='метрика', lh=17)
        for i, s in enumerate(segments):
            x = label_w + i * (cw + gap)
            f.rect(x, y, cw, 38, 'accent_pale' if k == 0 else 'surface')
            f.text(x + cw / 2, y + 24, s['metrics'][k], 'label', 'ink', 700, 'middle')
        y += 46
    f.text(0, y + 24, row_label, 'small', 'muted', 700)
    f.line(label_w - 16, y, label_w - 16, y + 10, 'line', 1)
    ybot = y
    for i, s in enumerate(segments):
        x = label_w + i * (cw + gap)
        yy = y
        for it in s['items']:
            t = f.wrap(it, cw - 16, 'small', 400, 2, 'плитка состава')
            h = 14 + 17 * (t.count('\n') + 1)
            f.rect(x, yy, cw, h, 'surface')
            f.text(x + cw / 2, yy + 20, t, 'small', 'ink', 400, 'middle', lh=17)
            yy += h + 6
        ybot = max(ybot, yy)
    return f.finish(ybot)


def layers(layers_, *, title_right=None, theme=None, mode='показ', width=None):
    """Слои стека пирамидой слева и ряды справа (компании, системы, примеры), выровненные по слоям.

    layers_: [{'name': 'Корпоративный уровень', 'inner': 'ERP, бизнес-системы', 'right': ['1С', 'SAP', 'Галактика'], 'hl'?: True}] сверху вниз, 2–5.
    right: плашки в один-два ряда; не влезли: FitError. hl: слой, о котором заголовок, получает акцент, остальные серые.
    """
    f = Fig(theme, mode, width, 'Слои стека')
    f.text_scheme = True
    n = len(layers_)
    need(2 <= n <= 5, 'слоёв 2–5')
    lw = 190
    pw = f.w * 0.42
    lh = 76
    top = 30 if title_right else 0
    tones = ['accent_pale', 'accent_light', 'accent_soft', 'accent_mid', 'accent_dark'][-n:]
    if any(L.get('hl') for L in layers_):
        # один акцент: выделенный слой цветом, остальные серым
        tones = ['accent' if L.get('hl') else 'grey_light' for L in layers_]
    for i, L in enumerate(layers_):
        y = top + i * lh
        # ширина как одна линейная функция высоты по всей пирамиде: боковые грани всех слоёв на одной прямой
        W = lambda yy: pw * ((yy - top) / lh + 0.35) / (n + 0.35)
        w0, w1 = W(y), W(y + lh - 4)
        cx = lw + pw / 2
        f.poly([(cx - w0 / 2, y), (cx + w0 / 2, y), (cx + w1 / 2, y + lh - 4), (cx - w1 / 2, y + lh - 4)], tones[i])
        tc = 'on_dark' if tones[i] in DARK else 'ink'
        if L.get('inner'):
            f.para(cx, y + lh / 2 + 4, L['inner'], max(w0, 120) - 10, 'small', tc, 400, 2, anchor='middle', what='слой внутри', lh=16)
        f.para(0, y + lh / 2 + 4, L['name'], lw - 16, 'label', 'ink', 700, 2, what='имя слоя', lh=18)
        f.line(0, y + lh - 2, f.w, y + lh - 2, 'line', 1)
        rx = lw + pw + 30
        rows_, cur, xx = [], [], rx
        for item in L.get('right', []):
            w = f.tw(item, 'small', 700) + 22
            if cur and xx + w > f.w:
                rows_.append(cur)
                cur, xx = [], rx
            if xx + w > f.w:
                raise FitError(f'{f.name}: пункт «{item[:40]}» шире колонки справа; сократи')
            cur.append((item, xx, w))
            xx += w + 8
        if cur:
            rows_.append(cur)
        if len(rows_) > 2:
            raise FitError(f'{f.name}: пункты слоя «{L["name"]}» не влезают в два ряда; оставь до {sum(len(r) for r in rows_[:2])} или сократи')
        for k, row in enumerate(rows_):
            yy = y + lh / 2 - 15 + (k - (len(rows_) - 1) / 2) * 33
            for item, x_, w in row:
                f.rect(x_, yy, w, 28, 'surface')
                f.text(x_ + w / 2, yy + 19, item, 'small', 'ink', 700, 'middle')
    if title_right:
        f.text(lw + pw + 30, 16, title_right, 'small', 'muted', 700)
    return f.finish(top + n * lh)
