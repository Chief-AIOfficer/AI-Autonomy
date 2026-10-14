"""Проверка краёв готовой HTML-деки перед показом: низ, верх, правый и левый край. Запускать после сборки.

    python3 <папка скилла>/align/check.py <дека.html> [--slide .slide] [--rows ".g2,.g3"]

Что ищет:
  низ    соседние блоки одного ряда кончаются на разной высоте при разнице до 22% (выравнивание не сработало)
  верх   заголовки или первые блоки соседних колонок стоят на разной высоте
  право  цветной блок не доходит до правого края контента на 1–16 px
  лево   цветной блок отступает от левого края контента на 1–16 px
  перелив содержимое слайда заходит под строку источников (.src) или за низ слайда больше чем на 3 px
  кухня  служебное на слайде: пути и имена файлов (.md, _кухня, _source), «сверить с», «со слов», «канон»,
         «черновик до ответов», номера решений реестра (Н12)
  текст  длинное тире, точка с запятой, обращение на «ты», двоеточие в заголовке слайда (кроме «Гипотеза: …»)
Ключ --no-text отключает проверку кухни и текста (например, для внутренней деки).
Пустой отчёт значит, что края ровные. Код возврата 1, если что-то найдено.
Нужен Chrome, Chromium или Edge (путь можно задать переменной CHROME). Деку не меняет: работает с временной копией.
"""
import argparse, os, pathlib, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # папка скилла: поиск браузера общий с exhibits
from exhibits.preview import find_chrome  # noqa: E402
PROBE = r"""<script>addEventListener('load', () => (window.DECK_ALIGN_DONE || Promise.resolve()).then(() => {
const SEL = %(sel)s, ROWS = %(rows)s, out = [], TXT = [], AXES = /Матрица|Столбц|Линии|Пара с разницей|Мост|Рейтинг|Гантели|Две группы|Разрыв до цели|Тепловая|Стековые|Шкала/;
const fill = e => { if (e instanceof SVGElement) { const f = getComputedStyle(e).fill; return e.tagName !== 'svg' && f && f !== 'none' && !/rgb\(255, 255, 255\)/.test(f); }
  const c = getComputedStyle(e).backgroundColor; return c && c !== 'rgba(0, 0, 0, 0)' && c !== 'rgb(255, 255, 255)'; };
const vis = e => e.getBoundingClientRect().height > 0 && getComputedStyle(e).position !== 'absolute';
[...document.querySelectorAll(SEL)].forEach((s, k) => {
  const was = s.style.display, hid = getComputedStyle(s).display === 'none'; if (hid) s.style.display = 'flex';
  const body = s.querySelector('.body') || s, B = body.getBoundingClientRect(), sc = (B.width / body.offsetWidth) || 1;
  s.querySelectorAll(ROWS).forEach(g => {
    const kids = [...g.children].filter(vis); if (kids.length < 2) return; const rows = {};
    kids.forEach(c => { const t = Math.round(c.getBoundingClientRect().top / (6 * sc)); (rows[t] = rows[t] || []).push(c); });
    Object.values(rows).forEach(row => { if (row.length < 2) return;
      const bot = c => { const ch = [...c.children].filter(vis); return (fill(c) || !ch.length) ? c.getBoundingClientRect().bottom : Math.max(...ch.map(x => x.getBoundingClientRect().bottom)); };
      const top = Math.min(...row.map(c => c.getBoundingClientRect().top)), b = row.map(bot), mb = Math.max(...b), H = mb - top;
      const intended = c => c.dataset.deckAligned || (!fill(c) && !c.querySelector('table') && ![...c.children].some(fill));   // выровнено к середине или текст от верха
      b.forEach((v, i) => { const d = mb - v; if (!intended(row[i]) && d / H > 0.01 && d / H <= 0.22 && d / sc > 3) out.push(`низ   ${k + 1}: ${row[i].className || row[i].tagName} выше соседа на ${Math.round(d / sc)} px`); });
      const heads = row.map(c => { const f = fill(c) ? c : ([...c.children].filter(vis)[0] || c); return (fill(f) ? f : f).getBoundingClientRect().top; });   // блок с фоном меряется по краю, а не по тексту внутри
      const dt = (Math.max(...heads) - Math.min(...heads)) / sc; if (dt > 3 && !row.some(c => c.dataset.deckAligned)) out.push(`верх  ${k + 1}: первые блоки колонок расходятся на ${Math.round(dt)} px`);
    });
  });
  body.querySelectorAll('*').forEach(e => { if (/^(text|tspan|i|b|em|span)$/i.test(e.tagName) || !fill(e)) return; const r = e.getBoundingClientRect();
    if (r.width < 60 * sc || r.height < 10 * sc) return; if (e.closest('.mbr,.chain,.lbl')) return;
    const svg = e.closest('svg'); if (svg && (e.tagName === 'svg' || AXES.test(svg.getAttribute('aria-label') || ''))) return;   // у графиков с осями свои поля
    const dr = (B.right - r.right) / sc, dl = (r.left - B.left) / sc;
    if (dr > 0.8 && dr < 16) out.push(`право ${k + 1}: ${e.tagName}.${e.getAttribute('class') || ''} не доходит до края на ${dr.toFixed(1)} px`);
    if (!svg && dl > 0.8 && dl < 16 && !e.parentElement.closest('[class*=card],[class*=pth],[class*=qs],[class*=ec]')) out.push(`лево  ${k + 1}: ${e.tagName}.${e.getAttribute('class') || ''} отступает от края на ${dl.toFixed(1)} px`); });
  { // перелив: содержимое слайда заходит под строку источников или за низ слайда
    const S = s.getBoundingClientRect(), src = s.querySelector('.src'), Sr = src && src.getBoundingClientRect(); let worst = null;
    const lim = (Sr && Sr.height > 0) ? Math.min(Sr.top, S.bottom) : S.bottom;
    body.querySelectorAll('svg,img,table,figure,p,li,div').forEach(e => {
      if (src && (e === src || e.contains(src) || src.contains(e))) return;
      const r = e.getBoundingClientRect(); if (r.height < 4 || r.width < 4 || getComputedStyle(e).position === 'absolute') return;
      const d = (r.bottom - lim) / sc; if (d > 3 && (!worst || d > worst[0])) worst = [d, e]; });
    if (worst) out.push(`перелив ${k + 1}: ${worst[1].tagName}.${worst[1].getAttribute('class') || ''} заходит ${(Sr && Sr.height > 0) ? 'под строку источников' : 'за низ слайда'} на ${Math.round(worst[0])} px`); }
  const h2 = s.querySelector('h2'); TXT.push([k + 1, (h2 ? h2.textContent : ''), s.innerText || s.textContent]);
  if (hid) s.style.display = was;
});
const p = document.createElement('pre'); p.id = 'deck-align-report'; p.textContent = out.join('\n'); document.body.appendChild(p);
const q = document.createElement('pre'); q.id = 'deck-text'; q.textContent = JSON.stringify(TXT); document.body.appendChild(q);
}))</script></body>"""


KITCHEN = [(r'_кухня|_source|_сборка|_audit', 'путь рабочей папки'), (r'[\w./-]+\.md\b', 'имя файла .md'),
           (r'сверить с [А-ЯЁ]', '«сверить с …»'), (r'со слов [А-ЯЁ]', '«со слов …»'), (r'\bканон', '«канон»'),
           (r'черновик до ответов', '«черновик до ответов»'), (r'\bН\d{1,2}\b', 'номер решения реестра')]
KITCHEN_OK = re.compile(r'reference/[\w./-]+\.md|CLAUDE\.md|SKILL\.md|\[тема\][\w./-]*\.md')   # файлы скилла, которые слушатель собирает сам


def text_issues(slides):
    out = []
    for n, title, body in slides:
        clean = KITCHEN_OK.sub('', body)
        for pat, what in KITCHEN:
            for mm in re.finditer(pat, clean):
                out.append(f'кухня {n}: {what}: «{clean[max(0, mm.start() - 30):mm.end() + 20].strip()}»')
        for ch, what in ((chr(0x2014), 'длинное тире'), (';', 'точка с запятой')):
            if ch in body:
                i = body.index(ch)
                out.append(f'текст {n}: {what}: «{body[max(0, i - 30):i + 20].strip()}»')
        if re.search(r'(?<![А-Яа-яЁё])(ты|тебе|тебя|твой|твоя|твои)(?![А-Яа-яЁё])', body):
            out.append(f'текст {n}: обращение на «ты»')
        if ':' in re.sub(r'^\s*Гипотеза:', '', title):   # «Гипотеза: …» разрешено (deck-and-analysis-quality §1)
            out.append(f'текст {n}: двоеточие в заголовке «{title.strip()[:60]}»')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('html')
    ap.add_argument('--slide', default='.slide')
    ap.add_argument('--rows', default='.g2,.g2w,.g3,.g4')
    ap.add_argument('--no-text', action='store_true', help='не проверять кухню и текст')
    a = ap.parse_args()
    h = open(a.html, encoding='utf-8').read()
    h = h.replace('</body>', PROBE % {'sel': repr(a.slide), 'rows': repr(a.rows)}, 1)
    d = tempfile.mkdtemp()
    tmp = os.path.join(d, 'probe.html')
    open(tmp, 'w', encoding='utf-8').write(h)
    o = subprocess.run([find_chrome(), '--headless=new', '--disable-gpu', '--window-size=1280,720', '--virtual-time-budget=9000',
                        '--dump-dom', pathlib.Path(tmp).resolve().as_uri()], capture_output=True, text=True).stdout
    m = re.search(r'<pre id="deck-align-report">(.*?)</pre>', o, re.S)
    rep = (m.group(1).strip() if m else 'отчёт не получен: проверь путь к Chrome и что в деке есть слайды')
    t = re.search(r'<pre id="deck-text">(.*?)</pre>', o, re.S)
    if t and not a.no_text:
        import json, html as _h
        extra = text_issues(json.loads(_h.unescape(t.group(1))))
        rep = '\n'.join(x for x in [rep, *extra] if x)
    print(rep or ('края ровные' if a.no_text else 'края ровные, кухни и ошибок текста нет'))
    sys.exit(1 if rep else 0)


if __name__ == '__main__':
    main()
