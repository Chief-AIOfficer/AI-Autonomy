"""Ядро приёмов: тема, замер текста по файлу шрифта, холст SVG, числа по-русски, проверки.

Функции приёмов рисуют только через Fig и называют цвета ролями темы ('accent', 'muted').
Литерал цвета в обход темы невозможен: Fig.c() падает на неизвестной роли.
"""
import math
import re
from decimal import Decimal, ROUND_HALF_UP
import os
import struct
import tomllib
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
DEFAULT_THEME = os.path.join(SKILL, 'themes', 'v3_golos.toml')

NBSP_NARROW = ' '
MINUS = '−'


class FitError(ValueError):
    """Текст или данные не влезают в приём. Сокращать текст или менять приём, не резать молча."""


class DataError(ValueError):
    """Данные не подходят приёму по форме."""


# ---------- шрифт: ширины глифов из TTF без сторонних библиотек ----------

class FontMetrics:
    def __init__(self, path):
        with open(path, 'rb') as fh:
            b = fh.read()
        n = struct.unpack('>H', b[4:6])[0]
        tables = {}
        for i in range(n):
            tag, _, off, ln = struct.unpack('>4sIII', b[12 + 16 * i:28 + 16 * i])
            tables[tag.decode('latin-1')] = (off, ln)
        self.upm = struct.unpack('>H', b[tables['head'][0] + 18:tables['head'][0] + 20])[0]
        num_hm = struct.unpack('>H', b[tables['hhea'][0] + 34:tables['hhea'][0] + 36])[0]
        o = tables['hmtx'][0]
        adv = [struct.unpack('>H', b[o + 4 * i:o + 4 * i + 2])[0] for i in range(num_hm)]
        self.cmap = self._cmap(b, tables['cmap'][0])
        self.adv = adv
        self.default = adv[self.cmap.get(ord('n'), 0)] if adv else self.upm // 2

    @staticmethod
    def _cmap(b, base):
        n = struct.unpack('>H', b[base + 2:base + 4])[0]
        best = None
        for i in range(n):
            pid, eid, off = struct.unpack('>HHI', b[base + 4 + 8 * i:base + 12 + 8 * i])
            fmt = struct.unpack('>H', b[base + off:base + off + 2])[0]
            if fmt == 12:
                best = (12, base + off)
                break
            if fmt == 4 and best is None:
                best = (4, base + off)
        m = {}
        fmt, o = best
        if fmt == 12:
            ngroups = struct.unpack('>I', b[o + 12:o + 16])[0]
            for g in range(ngroups):
                s, e, gid = struct.unpack('>III', b[o + 16 + 12 * g:o + 28 + 12 * g])
                for cp in range(s, e + 1):
                    m[cp] = gid + cp - s
        else:
            segx2 = struct.unpack('>H', b[o + 6:o + 8])[0]
            seg = segx2 // 2
            ends = struct.unpack(f'>{seg}H', b[o + 14:o + 14 + segx2])
            starts = struct.unpack(f'>{seg}H', b[o + 16 + segx2:o + 16 + 2 * segx2])
            deltas = struct.unpack(f'>{seg}h', b[o + 16 + 2 * segx2:o + 16 + 3 * segx2])
            ro_off = o + 16 + 3 * segx2
            ranges = struct.unpack(f'>{seg}H', b[ro_off:ro_off + segx2])
            for k in range(seg):
                for cp in range(starts[k], ends[k] + 1):
                    if cp == 0xFFFF:
                        continue
                    if ranges[k] == 0:
                        gid = (cp + deltas[k]) & 0xFFFF
                    else:
                        p = ro_off + 2 * k + ranges[k] + 2 * (cp - starts[k])
                        gid = struct.unpack('>H', b[p:p + 2])[0]
                        if gid:
                            gid = (gid + deltas[k]) & 0xFFFF
                    m[cp] = gid
        return m

    def width(self, s, size):
        tot = 0
        for ch in s:
            g = self.cmap.get(ord(ch))
            tot += self.adv[g] if g is not None and g < len(self.adv) else self.default
        return tot * size / self.upm


# ---------- тема ----------

class Theme:
    def __init__(self, path=DEFAULT_THEME):
        with open(path, 'rb') as fh:
            d = tomllib.load(fh)
        self.path = path
        self.name = d['meta']['name']
        self.width = d['canvas']['width']
        self.gap = d['canvas']['gap']
        self.pad = d['canvas']['pad']
        self.radius = d['canvas'].get('radius', 0)
        f = d['font']
        self.family, self.fallback = f['family'], f['fallback']
        self.font_file = os.path.normpath(os.path.join(os.path.dirname(path), f['file']))
        self.bold_factor = f.get('bold_factor', 1.05)
        self.sizes = d['size']
        col = dict(d['color'])
        self.ramp = col.pop('ramp')
        self.series = col.pop('series')
        self.colors = col
        for r in self.ramp + self.series:
            if r not in col:
                raise KeyError(f'тема {self.name}: роль {r} из ramp/series не задана в [color]')
        self.metrics = FontMetrics(self.font_file)

    def c(self, role):
        if role is None or role == 'none':
            return 'none'
        if role not in self.colors:
            raise KeyError(f'нет цветовой роли «{role}» в теме {self.name}; литералы цвета запрещены')
        return self.colors[role]

    def size(self, mode, role):
        if isinstance(role, (int, float)):
            return role
        return self.sizes[mode][role]

    def text_w(self, s, size, weight=400):
        w = self.metrics.width(s, size)
        return w * (self.bold_factor if weight >= 600 else 1)


_THEMES = {}


def load_theme(path=None):
    path = path or DEFAULT_THEME
    if path not in _THEMES:
        _THEMES[path] = Theme(path)
    return _THEMES[path]


# ---------- числа по-русски ----------

def num(v, d=0, unit='', sign=False, pct=False):
    """12345.6 -> '12 345,6'; знак минус настоящий; узкий пробел в тысячах; единица через пробел, % слитно."""
    if v is None:
        return '–'
    q = Decimal(str(abs(v))).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    s = f'{q:,.{d}f}'.replace(',', NBSP_NARROW).replace('.', ',')
    if v < 0 and float(s.replace(NBSP_NARROW, '').replace(',', '.')) != 0:
        s = MINUS + s
    elif sign and v > 0:
        s = '+' + s
    if pct or unit == '%':
        return s + '%'
    return f'{s} {unit}' if unit else s


# ---------- холст ----------

class Exhibit:
    def __init__(self, svg, w, h, warnings, name, base=None, top=None, rule=None):
        self.svg, self.w, self.h, self.warnings, self.name = svg, w, h, warnings, name
        self.rule = rule   # y линии под шапкой таблицы: X.hstack ставит таблицы в ряду по ней
        # base: y оси графика, top: y верха поля графика; по ним X.panels и X.hstack ставят графики на одну горизонталь
        self.base, self.top = base, top

    def __str__(self):
        return self.svg

    def save(self, path):
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(self.svg)
        return path


class Fig:
    """Холст одного рисунка. Все размеры в px при масштабе 1:1 со слайдом."""

    def __init__(self, theme=None, mode='показ', width=None, name='рисунок'):
        self.th = theme or load_theme()
        if mode not in self.th.sizes:
            raise ValueError(f'режим {mode}: есть только {list(self.th.sizes)}')
        self.mode = mode
        self.w = width or self.th.width
        self.name = name
        self.el = []
        self.boxes = []          # (x0, y0, x1, y1, текст) для проверки наложений
        self.marks = []          # (x0, x1, что) фигуры: проверка выхода за левый и правый край
        self.texts = []          # тексты абзацев: проверка «цифры утонули в тексте»
        self.text_scheme = False  # True у текстовых приёмов (таблица, этапы, пункты, столпы, рамка)
        self.warn = []
        self.max_y = 0

    # роли
    def c(self, role):
        return self.th.c(role)

    def s(self, role):
        return self.th.size(self.mode, role)

    def tw(self, s, role='label', weight=400):
        return self.th.text_w(s, self.s(role), weight)

    # примитивы
    def _grow(self, y):
        self.max_y = max(self.max_y, y)

    def rect(self, x, y, w, h, fill, title=None, stroke=None, dash=None, rx=0):
        t = f'<title>{escape(title)}</title>' if title else ''
        st = f' stroke="{self.c(stroke)}" stroke-width="1.2"' if stroke else ''
        if dash:
            st += f' stroke-dasharray="{dash}"'
        rx = min(rx, self.th.radius)   # скругление только в пределах темы
        r = f' rx="{rx}"' if rx else ''
        self.el.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{max(h, 0):.1f}"{r} '
                       f'fill="{self.c(fill)}"{st}>{t}</rect>')
        self.marks.append((x, x + max(w, 0), title or 'прямоугольник'))
        self._grow(y + h)

    def line(self, x1, y1, x2, y2, col='line', w=1, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.el.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{self.c(col)}" stroke-width="{w}"{d}/>')
        self._grow(max(y1, y2))

    def poly(self, pts, fill, stroke=None, opacity=None):
        st = f' stroke="{self.c(stroke)}" stroke-width="1.2"' if stroke else ''
        op = f' fill-opacity="{opacity}"' if opacity is not None else ''
        self.el.append('<polygon points="%s" fill="%s"%s%s/>' % (' '.join(f'{x:.1f},{y:.1f}' for x, y in pts), self.c(fill), st, op))
        self.marks.append((min(p[0] for p in pts), max(p[0] for p in pts), 'фигура'))
        self._grow(max(p[1] for p in pts))

    def path(self, d, stroke='accent', w=2, fill=None, dash=None, opacity=None):
        ds = f' stroke-dasharray="{dash}"' if dash else ''
        op = f' fill-opacity="{opacity}"' if opacity is not None else ''
        self.el.append(f'<path d="{d}" stroke="{self.c(stroke) if stroke else "none"}" stroke-width="{w}" '
                       f'fill="{self.c(fill) if fill else "none"}" stroke-linejoin="round" stroke-linecap="round"{ds}{op}/>')

    def circle(self, cx, cy, r, fill, stroke=None, sw=1.5):
        st = f' stroke="{self.c(stroke)}" stroke-width="{sw}"' if stroke else ''
        self.el.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{self.c(fill)}"{st}/>')
        self.marks.append((cx - r, cx + r, 'круг'))
        self._grow(cy + r)

    def arc(self, cx, cy, r, frac, fill, start=0.0):
        """Сектор круга: доля frac от угла start (доли оборота, 0 = верх, по часовой)."""
        if frac >= 0.999:
            return self.circle(cx, cy, r, fill)
        a0 = 2 * math.pi * start - math.pi / 2
        a1 = 2 * math.pi * (start + frac) - math.pi / 2
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        big = 1 if frac > 0.5 else 0
        self.el.append(f'<path d="M{cx:.1f},{cy:.1f} L{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 {big} 1 {x1:.1f},{y1:.1f} Z" fill="{self.c(fill)}"/>')

    def ring(self, cx, cy, r, frac, fill, rest='grey_light', width=14):
        """Кольцо-доля: дуга frac акцентом, остаток серым."""
        self.circle(cx, cy, r, 'none', rest, width)
        if frac <= 0:
            return
        if frac >= 0.999:
            return self.circle(cx, cy, r, 'none', fill, width)
        a0 = -math.pi / 2
        a1 = 2 * math.pi * frac - math.pi / 2
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        big = 1 if frac > 0.5 else 0
        self.el.append(f'<path d="M{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 {big} 1 {x1:.1f},{y1:.1f}" stroke="{self.c(fill)}" '
                       f'stroke-width="{width}" fill="none"/>')

    def arrow(self, x1, y1, x2, y2, col='line_strong', w=1.5, head=10):
        a = math.atan2(y2 - y1, x2 - x1)
        bx, by = x2 - head * math.cos(a), y2 - head * math.sin(a)
        self.line(x1, y1, bx, by, col, w)
        hw = head / 2
        p = [(x2, y2), (bx + hw * math.sin(a), by - hw * math.cos(a)), (bx - hw * math.sin(a), by + hw * math.cos(a))]
        self.poly(p, col)

    def diamond(self, cx, cy, r=8, fill='accent'):
        self.poly([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill)

    def seg(self, x, y, w, h, fill, first=False, last=False, tip=14):
        """Сегмент полосы этапов (шеврон): справа скос, слева выемка, кроме первого."""
        n = 0 if first else tip
        r = 0 if last else tip
        self.poly([(x, y), (x + w - r, y), (x + w, y + h / 2), (x + w - r, y + h), (x, y + h), (x + n, y + h / 2)], fill)

    def elbow(self, x1, y1, x2, y2, yt, col='line_strong', w=1, head=7):
        """Ломаная под прямым углом от одного значения к другому: вверх от (x1, y1) до yt, поперёк до x2, вниз со стрелкой до y2.
        Так в стиле MBB показывают изменение между столбцами; косые стрелки и выноски не используем."""
        self.line(x1, y1, x1, yt, col, w)
        self.line(x1, yt, x2, yt, col, w)
        self.arrow(x2, yt, x2, y2, col, w, head)

    def bracket(self, x1, x2, y, col='line_strong', up=True, tick=8, w=1.2):
        """Горизонтальная скобка над (up) или под парой столбцов."""
        d = tick if up else -tick
        self.line(x1, y + d, x1, y, col, w)
        self.line(x1, y, x2, y, col, w)
        self.line(x2, y, x2, y + d, col, w)

    # текст
    def text(self, x, y, s, role='label', color='ink', weight=400, anchor='start', lh=None, check=True, italic=False):
        """Строки через \\n. y это базовая линия первой строки. Возвращает высоту блока."""
        size = self.s(role)
        if size < self.s('min'):
            self.warn.append(f'кегль {size} ниже минимума режима {self.mode}: «{s[:30]}»')
        lh = lh or round(size * 1.3)
        lines = str(s).split('\n')
        sty = f"font-size:{size}px;font-weight:{weight}" + (';font-style:italic' if italic else '')
        for i, ln in enumerate(lines):
            yy = y + i * lh
            self.el.append(f'<text x="{x:.1f}" y="{yy:.1f}" text-anchor="{anchor}" style="{sty}" fill="{self.c(color)}">{escape(ln)}</text>')
            if check and ln.strip():
                wdt = self.th.text_w(ln, size, weight)
                x0 = x - (wdt if anchor == 'end' else wdt / 2 if anchor == 'middle' else 0)
                self.boxes.append((x0, yy - size * 0.78, x0 + wdt, yy + size * 0.22, ln))
        self._grow(y + (len(lines) - 1) * lh + size * 0.3)
        return (len(lines) - 1) * lh + size

    def wrap(self, s, max_w, role='label', weight=400, max_lines=None, what='текст'):
        """Перенос по словам под ширину. Не влезло в max_lines: FitError с подсказкой длины.
        Предлоги, союзы и числа с единицами не отрываются от следующего слова (неразрывный пробел)."""
        size = self.s(role)
        out = []
        for para in tie(str(s)).split('\n'):
            cur = ''
            for word in [w for w in para.split(' ') if w]:
                trial = (cur + ' ' + word).strip()
                if self.th.text_w(trial, size, weight) <= max_w:
                    cur = trial
                    continue
                if not cur:
                    raise FitError(f'{self.name}: слово «{word}» шире места {max_w:.0f}px в «{what}»')
                out.append(cur)
                cur = word
                if self.th.text_w(cur, size, weight) > max_w:
                    raise FitError(f'{self.name}: слово «{word}» шире места {max_w:.0f}px в «{what}»')
            out.append(cur)
        if max_lines and len(out) > max_lines:
            per = max_w / max(self.th.text_w('о', size, weight), 1)
            raise FitError(f'{self.name}: {what} «{s[:40]}…» занимает {len(out)} строк(и) при лимите {max_lines}; '
                           f'сократи примерно до {int(per * max_lines * 0.9)} знаков')
        return '\n'.join(out)

    def para(self, x, y, s, max_w, role='label', color='ink', weight=400, max_lines=None, anchor='start', lh=None, what='текст'):
        """wrap + text. Возвращает высоту блока. Разметку **жирного** не понимает: для неё rich."""
        if '**' in str(s):
            raise ValueError(f'{self.name}: {what} «{str(s)[:40]}…» с разметкой **: здесь простой текст, жирные ключи только там, где функция рисует через rich')
        t = self.wrap(s, max_w, role, weight, max_lines, what)
        self.texts.append(str(s))
        return self.text(x, y, t, role, color, weight, anchor, lh)

    def rich(self, x, y, s, max_w, role='label', color='ink', key_color=None, max_lines=None, lh=None, what='текст'):
        """Абзац с жирными ключами: **ключ** остальное. Возвращает высоту."""
        self.texts.append(str(s))
        size = self.s(role)
        lh = lh or round(size * 1.35)
        words = []          # (слово, жирное, приклеено к предыдущему без пробела)
        bold = False
        prev = ''
        for chunk in tie(str(s)).replace('**', '\x00').split('\x00'):
            parts = [x.rstrip('\u00a0') for x in chunk.split(' ') if x.strip('\u00a0')]
            for i, w in enumerate(parts):
                glue = i == 0 and bool(words) and not chunk[0].isspace() and bool(prev) and not prev[-1].isspace()
                words.append((w, bold, glue))
            if chunk:
                prev = chunk
            bold = not bold
        lines, cur, cur_w = [], [], 0
        sp = self.th.text_w(' ', size)
        for w, b, glue in words:
            ww = self.th.text_w(w, size, 700 if b else 400)
            if glue and cur:
                pw, pb, pww, pg = cur[-1]
                if cur_w + ww <= max_w:
                    cur.append((w, b, ww, True))
                    cur_w += ww
                    continue
            if cur and cur_w + sp + ww > max_w:
                lines.append(cur)
                cur, cur_w = [], 0
            if ww > max_w:
                raise FitError(f'{self.name}: слово «{w}» шире места в «{what}»')
            cur.append((w, b, ww, False))
            cur_w += (sp if cur_w else 0) + ww
        if cur:
            lines.append(cur)
        if max_lines and len(lines) > max_lines:
            raise FitError(f'{self.name}: {what} занимает {len(lines)} строк(и) при лимите {max_lines}; сократи')
        for i, ln in enumerate(lines):
            yy = y + i * lh
            parts = []
            for k, (w, b, _, g) in enumerate(ln):
                fill = self.c(key_color or color) if b else self.c(color)
                lead = '' if (k == 0 or g) else ' '
                parts.append(f'<tspan font-weight="{700 if b else 400}" fill="{fill}">{lead}{escape(w)}</tspan>')
            self.el.append(f'<text x="{x:.1f}" y="{yy:.1f}" style="font-size:{size}px" xml:space="preserve">{"".join(parts)}</text>')
            lw = sum(p[2] for p in ln) + sp * sum(1 for k, p in enumerate(ln) if k and not p[3])
            self.boxes.append((x, yy - size * 0.78, x + lw, yy + size * 0.22, ' '.join(p[0] for p in ln)))
        self._grow(y + (len(lines) - 1) * lh + size * 0.3)
        return (len(lines) - 1) * lh + size

    def rich_lines(self, s, max_w, role='label', max_lines=None, what='текст'):
        """Сколько строк займёт rich: тот же перенос, но без рисования (для расчёта высоты заранее)."""
        state = (len(self.el), len(self.boxes), len(self.marks), self.max_y)
        h = self.rich(0, 0, s, max_w, role, max_lines=max_lines, what=what)
        del self.el[state[0]:], self.boxes[state[1]:], self.marks[state[2]:]
        self.max_y = state[3]
        size = self.s(role)
        return round((h - size) / round(size * 1.35)) + 1

    def panel_head(self, title, sub=None):
        """Заголовок панели и единицы под ним, внутри рисунка (малые кратные). Возвращает высоту шапки."""
        if not title:
            return 0
        h = self.para(0, 18, title, self.w * 0.95, 'label', 'ink', 700, 2, what='заголовок панели')
        y = h + 8
        if sub:
            self.text(0, y + 14, sub, 'small', 'muted')
            y += 22
        return y + 12

    def plate(self, cx, y, s, fill='accent', color='on_dark', role='label', pad=8, weight=700, anchor='middle'):
        """Плашка с текстом. y это базовая линия текста. Возвращает (x0, x1)."""
        size = self.s(role)
        w = self.th.text_w(s, size, weight) + 2 * pad
        x0 = cx - w / 2 if anchor == 'middle' else cx if anchor == 'start' else cx - w
        self.rect(x0, y - size - 1, w, size + 9, fill)
        self.text(x0 + w / 2, y + 1, s, role, color, weight, 'middle', check=False)
        self.boxes.append((x0, y - size - 1, x0 + w, y + 8, s))
        return x0, x0 + w

    # иконки
    def icon(self, name, cx, cy, size=28, color='ink', bg=None, bg_r=None, ring=None):
        """Иконка Lucide по имени, центр в (cx, cy). bg: заливка круга под ней, ring: обводка круга."""
        d = icons()
        if name not in d:
            import difflib
            near = difflib.get_close_matches(name, list(d), 5, 0.5)
            raise KeyError(f'нет иконки «{name}»; похожие: {near}. Список: icons/lucide-sprite.svg')
        r = bg_r or size * 0.95
        if bg:
            self.circle(cx, cy, r, bg)
        if ring:
            self.circle(cx, cy, r, 'none', ring, 1.6)
        k = size / 24
        self.el.append(f'<g transform="translate({cx - size / 2:.1f},{cy - size / 2:.1f}) scale({k:.3f})" fill="none" '
                       f'stroke="{self.c(color)}" stroke-width="{1.7 / k:.2f}" stroke-linecap="round" stroke-linejoin="round">{d[name]}</g>')
        self._grow(cy + max(size / 2, r if (bg or ring) else 0))

    # различимость классов
    def check_classes(self, named, others=(), min_de=8):
        """named: {подпись: роль} классов легенды; others: роли без легенды на том же рисунке.
        Два цвета ближе min_de по ΔE (CIE76) читаются как один: класс теряет смысл."""
        items = [(lab, role) for lab, role in named.items()] + [(None, r) for r in others]
        seen = set()
        for i, (la, ra) in enumerate(items):
            for lb, rb in items[i + 1:]:
                if ra == rb or (la is None and lb is None) or (ra, rb) in seen:
                    continue
                seen.add((ra, rb))
                de = delta_e(self.c(ra), self.c(rb))
                if de < min_de:
                    what = ' и '.join(f'«{x}»' if x else 'узлы без класса' for x in (la, lb))
                    self.warn.append(f'классы почти одного цвета: {what} ({ra} и {rb}, ΔE {de:.0f}); '
                                     f'возьми роли подальше, например cat_2 или cat_3')

    # итог
    def finish(self, height=None, overlap_ok=False, base=None, top=None, rule=None):
        h = math.ceil(height or self.max_y + 4)
        warns = list(self.warn)
        for (x0, y0, x1, y1, s) in self.boxes:
            if x0 < -1 or x1 > self.w + 1 or y0 < -1 or y1 > h + 1:
                warns.append(f'подпись за краем рисунка: «{s[:40]}» ({x0:.0f}..{x1:.0f} × {y0:.0f}..{y1:.0f}, поле {self.w}×{h})')
        if self.text_scheme:
            # слайд должен читаться без чтения: три и больше чисел с единицами в тексте просятся в график
            facts = sorted({m.group(0).strip() for t in self.texts for m in _FACT.finditer(t.replace('**', ''))})
            if len(facts) >= 3:
                warns.append(f'цифры утонули в тексте ({", ".join(facts[:5])}): покажи их графиком '
                             f'(было → стало: pair_delta, ряд: columns, рейтинг: bar_ranked), текст оставь для смысла')
        for (x0, x1, what) in self.marks:
            if x0 < -1 or x1 > self.w + 1:
                warns.append(f'{what} за краем рисунка ({x0:.0f}..{x1:.0f}, ширина {self.w})')
                break
        if not overlap_ok:
            b = self.boxes
            for i in range(len(b)):
                for j in range(i + 1, len(b)):
                    p, q = b[i], b[j]
                    ix = min(p[2], q[2]) - max(p[0], q[0])
                    iy = min(p[3], q[3]) - max(p[1], q[1])
                    if ix > 2 and iy > 2:
                        warns.append(f'подписи наезжают: «{p[4][:30]}» и «{q[4][:30]}»')
        font = f"font-family:'{self.th.family}',{self.th.fallback};font-variant-numeric:tabular-nums"
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {h}" width="100%" role="img" '
               f'aria-label="{escape(self.name)}" style="{font}">' + ''.join(self.el) + '</svg>')
        return Exhibit(svg, self.w, h, warns, self.name, base, top, rule)


_SHORT = re.compile(r'(?<![\w\u00a0])([а-яёa-z]{1,2}|[А-ЯЁA-Z]|\d+[.,]?\d*|не|ни|без|для|над|под|при|про|через) (?=\S)')


_FACT = re.compile(r'(?:[−+]|минус |плюс )?\d[\d\u202f\u00a0]*(?:[.,]\d+)?(?:[–-]\d+)?[\s\u00a0]?'
                   r'(?:%|п\.\s?п\.|раза?\b|мин\w*|час\w*|рабочих дн\w*|дн\w*|млн|млрд|трлн|тыс\b|₽|руб\w*|коп\w*|\$|€)')
_TAIL = re.compile(r' (\S{1,3}[.,;:!?»)]?)$')
_PARTICLE = re.compile(r' (ли|же|бы)(?=[\s.,;:!?»)]|$)')


def tie(s):
    """Неразрывный пробел после коротких слов и чисел: «к ИИ», «в 2026», «12 млрд» не рвутся на строки.
    Частицы «ли», «же», «бы» держатся за предыдущее слово: «есть ли» не рвётся."""
    s = _PARTICLE.sub('\u00a0\\1', _SHORT.sub(lambda m: m.group(1) + '\u00a0', s))
    # короткое последнее слово абзаца («РР», «ИТ», «АО») не остаётся одно на строке
    return '\n'.join(_TAIL.sub('\u00a0\\1', ln) for ln in s.split('\n'))


_ICONS = {}


def icons():
    """Символы Lucide (ISC) из icons/lucide-sprite.svg: имя -> внутренности <symbol>."""
    if not _ICONS:
        path = os.path.join(SKILL, 'icons', 'lucide-sprite.svg')
        with open(path, encoding='utf-8') as fh:
            src = fh.read()
        for m in re.finditer(r'<symbol id="([^"]+)"[^>]*>(.*?)</symbol>', src, re.S):
            _ICONS[m.group(1)] = re.sub(r'\s+', ' ', m.group(2)).strip()
    return _ICONS


def _lab(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = lambda c: ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
    r, g, b = lin(r), lin(g), lin(b)
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def delta_e(c1, c2):
    """Разница двух цветов #RRGGBB по CIE76: меньше 8 на бледных заливках глазом почти не различить."""
    return math.dist(_lab(c1), _lab(c2))


def need(cond, msg):
    if not cond:
        raise DataError(msg)


def nice_max(v):
    """Верх шкалы: ближайшее «круглое» сверху."""
    if v <= 0:
        return 1
    e = 10 ** math.floor(math.log10(v))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * e >= v:
            return m * e
    return 10 * e
