"""Расстановка по двум осям: матрица 2×2, карта позиционирования с облаками групп, карта рисков."""
import math

from xml.sax.saxutils import escape
from .core import Fig, need, num

QTONE = {'good': 'good_pale', 'warn': 'surface', 'bad': 'bad_pale', 'accent': 'accent_pale', 'none': 'bg', 'grey': 'surface'}


def _hull(pts):
    pts = sorted(set(pts))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _label_box(f, cx, cy, s, anc, role='small', weight=400, real=False):
    """Рамка подписи. real=False: как раньше, вся строка одной линией (по ней ищется место без наложений,
    чтобы старые раскладки не сдвинулись); real=True: строки через \\n как их рисует Fig.text (для проверки клетки)."""
    sz = f.s(role)
    lines = str(s).split('\n') if real else [s]
    w = max(f.tw(ln, role, weight) for ln in lines)
    x0 = cx - (w if anc == 'end' else w / 2 if anc == 'middle' else 0)
    return (x0, cy - sz * 0.78, x0 + w, cy + sz * 0.22 + (len(lines) - 1) * round(sz * 1.3))


def _inside(box, cell, tol=2, vtol=2):
    """Подпись внутри клетки. По вертикали допускается свес vtol (полстроки): нижняя строка, чуть свисающая
    за горизонтальную границу, ещё читается как подпись своей клетки; сдвиг вбок через вертикальную границу нет."""
    return cell is None or (box[0] >= cell[0] - tol and box[2] <= cell[2] + tol and box[1] >= cell[1] - vtol and box[3] <= cell[3] + vtol)


def _place_label(f, x, y, s, r, role='small', weight=400, obstacles=(), cell=None):
    """Подпись точки: справа, слева, сверху, снизу; первая позиция без наложения на подписи и на чужие точки.
    cell: (x0, y0, x1, y1) клетки матрицы, где стоит точка. Если прежнее место подписи выходит за клетку
    (подпись через границу читается как принадлежность соседней зоне), ищется место внутри клетки по настоящей
    рамке многострочной подписи; не нашлось, остаётся прежнее место (вызывающий предупредит)."""
    sz = f.s(role)
    cands = [(x + r + 6, y + sz * 0.35, 'start'), (x - r - 6, y + sz * 0.35, 'end'),
             (x, y - r - 6, 'middle'), (x, y + r + sz + 2, 'middle')]
    hit = lambda box, others: any(min(box[2], b[2]) - max(box[0], b[0]) > 1 and min(box[3], b[3]) - max(box[1], b[1]) > 1 for b in others)
    old = None
    for cx, cy, anc in cands:   # прежнее правило: вся подпись одной линией
        box = _label_box(f, cx, cy, s, anc, role, weight)
        if box[0] < 0 or box[2] > f.w:
            continue
        if not hit(box, list(f.boxes) + list(obstacles)):
            old = (cx, cy, anc)
            break
    old = old or cands[0]
    vt = round(sz * 0.65)
    if cell is None or _inside(_label_box(f, old[0], old[1], s, old[2], role, weight, real=True), cell, vtol=vt):
        return old
    n = len(str(s).split('\n'))
    lift = (n - 1) * round(sz * 1.3)
    for cx, cy, anc in cands[:2] + [(x, y - r - 6 - lift, 'middle'), cands[3]]:   # сверху многострочная подпись поднимается целиком
        box = _label_box(f, cx, cy, s, anc, role, weight, real=True)
        if box[0] < 0 or box[2] > f.w or not _inside(box, cell, vtol=vt):
            continue
        if not hit(box, list(f.boxes) + list(obstacles)):
            return cx, cy, anc
    return old


def matrix_2x2(points, *, x_label, y_label, quadrants=None, split=(0.5, 0.5), groups=None, ends=('низко', 'высоко'), y_ends=None,
               numbered=False, classes=None, height=440, theme=None, mode='показ', width=None):
    """Расстановка по двум осям.

    points: [{'label', 'x', 'y', 'cls'?, 'n'?}] x и y от 0 до 1 (доля оси) или в своих единицах при заданных scale.
    quadrants: {'tl': ('Название', 'good'|'warn'|'bad'|'accent'|'grey'|'none'), 'tr':..., 'bl':..., 'br':...} тон клетки по смыслу зоны.
    groups: {'Западная Европа': [метки точек]} облака групп с подписью жирным (карта позиционирования).
    numbered: точки кружками с номером вместо подписей (для карты рисков; номер из 'n').
    classes: {'cls': ('подпись в легенде', роль цвета)} цвет точки несёт один смысл.
    ends: подписи концов оси X; y_ends: оси Y (по умолчанию как ends). Для «срок × влияние»: ends=('быстро', 'долго'), y_ends=('низко', 'высоко').
    """
    y_ends = y_ends or ends
    f = Fig(theme, mode, width, 'Матрица 2×2')
    need(1 <= len(points) <= 25, 'точек 1–25')
    lw = max(f.tw(e, 'small') for e in (y_ends or ends)) + 16 + f.s('label') + 22 + (round(f.s('label') * 1.25) if f.tw(' '.join(y_label.split()), 'label', 700) > height + 40 else 0)   # подпись оси Y повёрнута на 90°: место только под концы оси и строку подписи
    top = 10
    if classes:
        f.check_classes({lab: role for lab, role in classes.values()},
                        ['accent'] if any(not p.get('cls') for p in points) else [])
        lx_, rows_ = lw, 1
        for lab_, _ in classes.values():
            if lx_ + 30 + f.tw(lab_, 'small') > f.w:
                lx_, rows_ = lw, rows_ + 1
            lx_ += 50 + f.tw(lab_, 'small')
        top = 18 + 22 * rows_
    x0, x1 = lw, f.w - 10
    y0, y1 = top, top + height
    sx, sy = split

    def X(v):
        return x0 + (x1 - x0) * v

    def Y(v):
        return y1 - (y1 - y0) * v
    if quadrants:
        cells = {'tl': (0, sy, sx, 1), 'tr': (sx, sy, 1, 1), 'bl': (0, 0, sx, sy), 'br': (sx, 0, 1, sy)}
        for k, (a, b, c, d) in cells.items():
            if k in quadrants:
                name, tone = quadrants[k]
                f.rect(X(a) + 2, Y(d) + 2, X(c) - X(a) - 4, Y(b) - Y(d) - 4, QTONE[tone])
                ty = Y(d) + 24 if k in ('tl', 'tr') else Y(b) - 14
                f.text((X(a) + X(c)) / 2, ty, name, 'label', 'ink', 700, 'middle')
    else:
        f.line(X(sx), y0, X(sx), y1, 'line', 1, '4 3')
        f.line(x0, Y(sy), x1, Y(sy), 'line', 1, '4 3')
    f.arrow(x0 - 8, y1 + 8, x0 - 8, y0 - 6, 'line_strong', 1.2, 8)
    f.arrow(x0 - 8, y1 + 8, x1, y1 + 8, 'line_strong', 1.2, 8)
    # подпись оси Y идёт вдоль оси, повёрнута на 90° против часовой стрелки (правило стиля v3)
    # одной строкой, если влезает вдоль оси, иначе максимум в две строки
    yl = f.wrap(' '.join(y_label.split()), (y1 - y0) + 40, 'label', 700, 2, 'подпись оси Y').split('\n')
    sz = f.s('label')
    cy_ = (y0 + y1) / 2
    # вплотную к оси: подпись по центру, слова концов оси стоят у её концов и ей не мешают;
    # если подпись дотягивается до концов, отходит левее них
    ax_ = x0 - 8
    long_ = max(f.tw(l, 'label', 700) for l in yl) / 2 > (y1 - y0) / 2 - 24
    base_ = (sz if long_ else ax_ - 12) - (len(yl) - 1) * round(sz * 1.25)
    for k_, ln_ in enumerate(yl):
        cx_ = base_ + k_ * round(sz * 1.25)
        f.el.append(f'<text x="{cx_:.1f}" y="{cy_:.1f}" text-anchor="middle" transform="rotate(-90 {cx_:.1f} {cy_:.1f})" '
                    f'style="font-size:{sz}px;font-weight:700" fill="{f.c("ink")}">{escape(ln_)}</text>')
    f.text(x0 - 16, y0 + 10, y_ends[1], 'small', 'muted', 400, 'end')
    f.text(x0 - 16, y1, y_ends[0], 'small', 'muted', 400, 'end')
    f.text((x0 + x1) / 2, y1 + 40, x_label, 'label', 'ink', 700, 'middle')
    f.text(x0, y1 + 28, ends[0], 'small', 'muted')
    f.text(x1, y1 + 28, ends[1], 'small', 'muted', 400, 'end')
    by_label = {p['label']: p for p in points}
    clouds = []
    if groups:
        tones = ['accent_pale', 'grey_light', 'surface', 'accent_pale']
        pad = 26
        for gi, (gname, labs) in enumerate(groups.items()):
            pts = [(X(by_label[l]['x']), Y(by_label[l]['y'])) for l in labs]
            hull = _hull(pts)
            tone = tones[gi % len(tones)]
            if len(hull) == 1:
                f.circle(hull[0][0], hull[0][1], pad, tone)
            else:
                d = 'M' + ' L'.join(f'{px:.1f},{py:.1f}' for px, py in hull) + ' Z'
                f.el.append(f'<path d="{d}" fill="{f.c(tone)}" stroke="{f.c(tone)}" stroke-width="{2 * pad}" stroke-linejoin="round"/>')
            xs_, ys_ = [p[0] for p in pts], [p[1] for p in pts]
            clouds.append((gname, (min(xs_) - pad, min(ys_) - pad, max(xs_) + pad, max(ys_) + pad)))
    dots = [(X(p['x']) - 9, Y(p['y']) - 9, X(p['x']) + 9, Y(p['y']) + 9) for p in points]
    for pi, p in enumerate(points):
        cx, cy = X(p['x']), Y(p['y'])
        col = classes[p['cls']][1] if classes and p.get('cls') else 'accent'
        if numbered:
            f.circle(cx, cy, 13, col)
            f.text(cx, cy + 5, str(p.get('n', '')), 'small', 'on_dark', 700, 'middle', check=False)
            f.boxes.append((cx - 13, cy - 13, cx + 13, cy + 13, str(p.get('n'))))
        elif groups:
            f.text(cx, cy + 5, p['label'], 'small', 'ink', 400, 'middle')
        else:
            f.circle(cx, cy, 7, col)
            others = [d for k, d in enumerate(dots) if k != pi]
            # клетка точки: (лево, верх, право, низ) в пикселях рисунка
            cell = (x0 if p['x'] < sx else X(sx), y0 if p['y'] >= sy else Y(sy), X(sx) if p['x'] < sx else x1, Y(sy) if p['y'] >= sy else y1)
            tx, ty, anc = _place_label(f, cx, cy, p['label'], 7, obstacles=others, cell=cell)
            f.text(tx, ty, p['label'], 'small', 'ink', 400, anc)
            if not _inside(_label_box(f, tx, ty, p['label'], anc, real=True), cell, vtol=round(f.s('small') * 0.65)):
                f.warn.append(f'подпись «{p["label"][:30]}» переходит в соседнюю клетку: сдвинь точку от границы или сократи подпись')
            lb = f.boxes[-1]
            if any(min(lb[2], d[2]) - max(lb[0], d[0]) > 1 and min(lb[3], d[3]) - max(lb[1], d[1]) > 1 for d in others):
                f.warn.append(f'подпись «{p["label"][:30]}» задевает соседнюю точку: раздвинь точки или сократи подпись')
    for gname, (bx0, by0, bx1, by1) in clouds:
        w = f.tw(gname, 'label', 700)
        sz = f.s('label')
        cands = [((bx0 + bx1) / 2 - w / 2, by0 - 8), ((bx0 + bx1) / 2 - w / 2, by1 + sz + 4),
                 (bx1 + 6, (by0 + by1) / 2 + 5), (bx0 - w - 6, (by0 + by1) / 2 + 5)]
        others = [c[1] for c in clouds if c[0] != gname]
        pick = cands[0]
        for lx_, ly_ in cands:
            box = (lx_, ly_ - sz * 0.78, lx_ + w, ly_ + sz * 0.22)
            if box[0] < x0 or box[2] > x1 or box[1] < y0 - 4 or box[3] > y1:
                continue
            hit = any(min(box[2], b[2]) - max(box[0], b[0]) > 1 and min(box[3], b[3]) - max(box[1], b[1]) > 1 for b in f.boxes + others)
            if not hit:
                pick = (lx_, ly_)
                break
        f.text(pick[0], pick[1], gname, 'label', 'ink', 700)
    if classes:
        lx, ly = x0, 12
        for cls, (lab, col) in classes.items():
            if lx + 30 + f.tw(lab, 'small') > f.w:
                lx, ly = x0, ly + 22
            f.circle(lx + 8, ly, 8, col)
            f.text(lx + 22, ly + 5, lab, 'small', 'ink')
            lx += 50 + f.tw(lab, 'small')
    return f.finish()


def risk_map(risks, classes, *, x_label='Влияние', y_label='Вероятность', theme=None, mode='показ', width=None):
    """Список рисков слева с номерами и карта «вероятность × влияние» справа; цвет означает управляемость.

    risks: [{'name': 'Каннибализация', 'desc': 'Перетекание продаж в цифровой канал', 'x': 0.8, 'y': 0.85, 'cls': 'manage'}]
    classes: {'avoid': ('Можно избежать', 'accent_light'), 'manage': ('Можно снизить', 'accent_dark'), 'out': ('Вне контроля', 'accent')}
    """
    from .lines import hstack
    from .core import load_theme
    full = width or (theme or load_theme()).width
    W = full * 0.55
    f = Fig(theme, mode, W, 'Риски списком')
    need(2 <= len(risks) <= 9, 'рисков 2–9; больше: таблица рисков в приложении')
    nw = 200
    y = 30
    f.text(0, 16, 'Риск', 'small', 'muted', 700)
    f.text(nw + 30, 16, 'Описание', 'small', 'muted', 700)
    f.line(0, 24, W - 20, 24, 'line_strong', 1)
    for i, r in enumerate(risks, 1):
        col = classes[r['cls']][1]
        t = f.wrap(r['name'], nw - 46, 'label', 700, 2, 'название риска')
        d = f.wrap(r.get('desc', ''), W - nw - 60, 'small', 400, 3, 'описание риска')
        rh = max(52, 16 + max(t.count('\n') + 1, d.count('\n') + 1) * 19)
        f.rect(0, y + 4, nw, rh - 8, col)
        f.circle(18, y + rh / 2, 12, 'bg')
        f.text(18, y + rh / 2 + 5, str(i), 'small', 'ink', 700, 'middle', check=False)
        tc = 'on_dark' if col in {'accent', 'accent_dark', 'accent_mid', 'accent_soft'} else 'ink'
        f.text(40, y + rh / 2 + 5 - 9 * t.count('\n'), t, 'label', tc, 700, lh=18)
        f.text(nw + 30, y + rh / 2 + 5 - 9.5 * d.count('\n'), d, 'small', 'ink', lh=19)
        f.line(nw + 20, y + rh, W - 20, y + rh, 'line', 1, '3 3')
        y += rh
    left = f.finish(y + 4)
    pts = [{'label': r['name'], 'x': r['x'], 'y': r['y'], 'cls': r['cls'], 'n': i} for i, r in enumerate(risks, 1)]
    right = matrix_2x2(pts, x_label=x_label, y_label=y_label, numbered=True, classes=classes, height=max(y - 120, 260),
                       theme=theme, mode=mode, width=full - W - 10)
    return hstack([left, right], 10)
