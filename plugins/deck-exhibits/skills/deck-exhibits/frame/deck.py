"""Минимальная рамка деки для экспонатов deck-exhibits: слайд 1280×720, заголовок-мысль, экспонат,
надстрочные сноски и строка источников, номер слайда (на титуле номера нет), навигация стрелками,
печать в PDF по слайду на страницу, проверка краёв.

Пример (файл дека.py рядом с декой, запуск одной командой `python3 дека.py`):

    import sys; sys.path.insert(0, '<папка скилла>/frame')
    from deck import Deck, X                      # X это пакет exhibits

    d = Deck('Материал к встрече')
    d.title('Как превратить ИИ-продукты в выручку', 'Материал к встрече, октябрь 2026')
    t = 'Рост замедлился с 26 до 17,7%[1]'
    d.slide(t, X.pair_delta([...], height=d.room(t, sources=[1]) - 40),
            sources=[('TAdviser500-2026', 'https://www.tadviser.ru/...')])
    d.build('слайды/дека.html')                   # HTML, PDF, кадры PNG и проверка краёв

Сноска: `[1]` в заголовке или в тексте `lead` становится надстрочной единицей и обязана иметь
источник номер 1 в `sources`. Источник: строка или пара (текст, ссылка). Сноска без источника роняет сборку.
Гипотеза: заголовок начинается со слов «Гипотеза: …» (так требует проверка align/check.py).
Цвета и шрифт берутся из темы deck-exhibits: рамка своих цветов не держит.
"""
import html
import os
import pathlib
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, SKILL)
import exhibits as X  # noqa: E402

W, H, PAD_X, PAD_TOP = 1280, 720, 56, 44      # поле контента 1168 px: ширина экспоната 1:1
TITLE_SIZE, TITLE_LH = 26, 32
_FN = re.compile(r'\[(\d{1,2})\]')
# короткое слово не остаётся в конце строки заголовка: предлоги, союзы, частицы
_SHORT = re.compile(r'(?<![\w-])(в|во|и|с|со|к|ко|о|об|у|а|но|на|по|за|до|от|из|не|ни|без|для|при|про|это|что|как) ', re.I)
LONG_DASH = chr(0x2014)  # emdash-ok: проверка, что его нет в деке


class DeckError(Exception):
    pass


class Deck:
    def __init__(self, name, theme=None, mode='показ'):
        self.name = name
        self.th = X.load_theme(theme) if theme else X.load_theme()
        self.mode = mode
        self.slides = []          # (kind, title, body_html, sources)
        self.warnings = []

    # ---------- слайды ----------
    def title(self, title, sub=''):
        """Титул: тёмный фон, без номера страницы."""
        self.slides.append(('title', title, sub, []))

    def slide(self, title, exhibit=None, sources=None, lead=None, html_body=None):
        """Слайд: заголовок-мысль, под ним экспонат (Exhibit из X) или готовый HTML, внизу источники.
        lead: одна строка под заголовком (не подзаголовок над ним). Сноски [n] допустимы в title и lead."""
        sources = list(sources or [])
        n = len(self.slides) + 1
        used = {int(m) for s in (title, lead or '') for m in _FN.findall(s)}
        missing = sorted(k for k in used if k > len(sources))
        if missing:
            raise DeckError(f'слайд {n}: сноски {missing} без источника в sources')
        unused = [k for k in range(1, len(sources) + 1) if k not in used]
        if unused and used:
            self.warnings.append(f'слайд {n}: источники {unused} не отмечены сноской')
        body = ''
        if lead:
            body += f'<p class="lead">{self._fn(lead)}</p>'
        if exhibit is not None:
            for w in exhibit.warnings:
                self.warnings.append(f'слайд {n}, экспонат: {w}')
            body += f'<div class="fig">{exhibit.svg}</div>'
            room = self._room(title, lead, sources)
            if exhibit.h > room:
                self.warnings.append(f'слайд {n}: экспонат высотой {round(exhibit.h)} px, места {round(room)} px. '
                                     f'Ужми экспонат (height, max_h) или сократи заголовок')
        if html_body:
            body += html_body
        self.slides.append(('slide', title, body, sources))

    # ---------- сборка ----------
    def html(self):
        th, c = self.th, self.th.c
        out = []
        total = len(self.slides)
        for k, (kind, title, body, sources) in enumerate(self.slides, 1):
            if kind == 'title':
                sub = f'<div class="sub">{self._fn(body)}</div>' if body else ''
                out.append(f'<section class="slide title-slide"><h1 class="t">{self._fn(title)}</h1>{sub}</section>')
                continue
            src = ''
            if sources:
                items = []
                for i, s in enumerate(sources, 1):
                    text, url = (s if isinstance(s, (tuple, list)) else (s, None))
                    t = html.escape(text)
                    if url:
                        t = f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{t}</a>'
                    items.append(f'<span><sup>{i}</sup>{t}</span>')
                src = '<div class="src">' + ''.join(items) + '</div>'
            out.append(f'<section class="slide"><h2 class="t">{self._fn(title)}</h2><div class="body">{body}</div>'
                       f'<footer>{src}<div class="pg">{k} / {total}</div></footer></section>')
        css = CSS % {
            'ink': c('ink'), 'muted': c('muted'), 'line': c('line'), 'acc': c('accent'), 'dark': c('accent_dark'),
            'pale': c('accent_light'), 'on': c('on_dark'), 'bg': c('bg'), 'fam': th.family, 'fb': th.fallback,
            'W': W, 'H': H, 'px': PAD_X, 'pt': PAD_TOP, 'ts': TITLE_SIZE, 'tl': TITLE_LH}
        align = open(os.path.join(SKILL, 'align', 'align.js'), encoding='utf-8').read()
        return ('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{html.escape(self.name)}</title><style>{X.font_face(th)}{css}</style></head><body>'
                + ''.join(out) + NAV + f'<script>{align}</script></body></html>')

    def build(self, path, pdf=True, png=True, check=True):
        """Пишет HTML; по умолчанию ещё PDF (слайд на страницу), кадры PNG в папку <имя>_кадры и отчёт проверки краёв."""
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        doc = self.html()
        if LONG_DASH in doc:
            self.warnings.append('в деке длинное тире: замени на короткое')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(doc)
        print(f'{len(self.slides)} слайдов -> {path}')
        chrome = None
        if pdf or png or check:
            try:
                chrome = X.find_chrome()
            except FileNotFoundError as e:
                self.warnings.append(str(e) + '. PDF, кадры и проверка краёв пропущены')
        uri = pathlib.Path(path).as_uri()
        if chrome and pdf:
            out = os.path.splitext(path)[0] + '.pdf'
            subprocess.run([chrome, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                            '--virtual-time-budget=3000', f'--print-to-pdf={out}', uri], capture_output=True, timeout=120)
            print('PDF ->', out if os.path.exists(out) else 'не получился')
        if chrome and png:
            d = os.path.splitext(path)[0] + '_кадры'
            os.makedirs(d, exist_ok=True)
            for k in range(1, len(self.slides) + 1):
                subprocess.run([chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', f'--window-size={W},{H}',
                                '--virtual-time-budget=2000', f'--screenshot={os.path.join(d, f"s{k:02d}.png")}',
                                f'{uri}#{k}'], capture_output=True, timeout=60)
            print('кадры ->', d)
        if chrome and check:
            r = subprocess.run([sys.executable, os.path.join(SKILL, 'align', 'check.py'), path],
                               capture_output=True, text=True)
            print('проверка краёв:', (r.stdout or r.stderr).strip())
        for w in self.warnings:
            print('ВНИМАНИЕ:', w)
        return path

    # ---------- служебное ----------
    def _fn(self, s):
        return _SHORT.sub(lambda m: m.group(1) + '\u00a0', _FN.sub(r'<sup>\1</sup>', s or ''))

    def room(self, title, lead=None, sources=()):
        """Сколько px по высоте остаётся экспонату под этим заголовком: передай в height или max_h приёма."""
        return self._room(title, lead, list(sources))

    def _lines(self, s, size, width):
        words, lines, cur = _FN.sub('', re.sub('<[^>]+>', '', s)).split(), 1, 0.0
        sp = self.th.metrics.width(' ', size)
        for w in words:
            ww = self.th.metrics.width(w, size) * 1.04   # заголовок жирный: запас на насыщенность
            if cur and cur + sp + ww > width:
                lines, cur = lines + 1, ww
            else:
                cur = cur + sp + ww if cur else ww
        return lines

    def _room(self, title, lead, sources):
        used = PAD_TOP + self._lines(title, TITLE_SIZE, W - 2 * PAD_X) * TITLE_LH + 20
        if lead:
            used += self._lines(lead, 17, W - 2 * PAD_X) * 24 + 12
        used += 46 + (12 * max(0, (len(sources) - 1) // 3))   # подвал: источники и номер
        return H - used


CSS = '''
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#E4E6EA}
body{color:%(ink)s;font:16px/1.4 "%(fam)s",%(fb)s;font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased;
     height:100vh;overflow:hidden;display:flex;align-items:center;justify-content:center}
.slide{display:none;flex:none;width:%(W)spx;height:%(H)spx;background:%(bg)s;padding:%(pt)spx %(px)spx 0;flex-direction:column;
       position:relative;overflow:hidden;transform:scale(var(--fit,1));transform-origin:center}
.slide.on{display:flex}
.t{font-size:%(ts)spx;line-height:%(tl)spx;font-weight:700;letter-spacing:-.01em;margin-bottom:20px}
.lead{font-size:17px;line-height:24px;color:%(muted)s;margin:-8px 0 12px}
.body{flex:1;min-height:0;display:flex;flex-direction:column}
.fig{width:100%%}
sup{font-size:.6em;line-height:0;vertical-align:super;margin-left:1px;color:%(acc)s;font-weight:700}
footer{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding:10px 0 18px;border-top:1px solid %(line)s}
.src{font-size:12px;line-height:1.45;color:%(muted)s;display:flex;flex-wrap:wrap;gap:2px 18px}
.src sup{color:%(muted)s}
.src a{color:%(acc)s;text-decoration:none;border-bottom:1px dotted %(acc)s}
.pg{font-size:12px;color:%(muted)s;white-space:nowrap;margin-left:auto}
.title-slide{justify-content:center;padding:0 96px;background:%(dark)s;color:%(on)s}
.title-slide .t{font-size:42px;line-height:1.16;margin-bottom:28px;color:%(on)s}
.title-slide .sub{font-size:18px;line-height:1.5;color:%(pale)s;border-top:1px solid %(pale)s;padding-top:16px}
@page{size:%(W)spx %(H)spx;margin:0}
@media print{html,body{height:auto!important;overflow:visible!important;display:block!important;background:#fff!important}
  .slide{display:flex!important;transform:none!important;break-after:page;page-break-after:always}}
'''

NAV = '''<script>
const sl=[...document.querySelectorAll('.slide')];let i=0;
function fit(){document.body.style.setProperty('--fit',Math.min(innerWidth/1280,innerHeight/720))}
function go(k){i=Math.max(0,Math.min(sl.length-1,k));sl.forEach((s,j)=>s.classList.toggle('on',j===i));try{history.replaceState(null,'','#'+(i+1))}catch(e){}}
addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();go(i+1)}
  if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();go(i-1)}if(e.key==='Home')go(0);if(e.key==='End')go(sl.length-1)});
addEventListener('click',e=>{if(e.target.closest('a'))return;go(e.clientX>innerWidth/2?i+1:i-1)});
addEventListener('resize',fit);fit();go((parseInt(location.hash.slice(1))||1)-1);
</script>'''
