"""Собирает из catalog.py: INDEX.md (выбор приёма), cards/<приём>.md (рецепты), _preview/catalog.html (каталог с образцами).
Запуск: python3 build_docs.py [--no-html]"""
import base64
import glob
import html
import inspect
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'tests'))
import catalog as C  # noqa: E402
import exhibits as X  # noqa: E402
import demo as D  # noqa: E402

MSG = {m[0]: m for m in C.MESSAGES}


def manifest():
    return C.SAMPLES


def sample_line(m, i):
    r = m.get(i, {})
    return f"- `{i}` {r.get('firm', '')} {r.get('year', '')}: {r.get('title', '')}. {r.get('take', '')}\n  смотреть: {r.get('url', '')}"


def demo_src(name):
    src = inspect.getsource(D.DEMOS[name])
    return '\n'.join(l for l in src.splitlines() if not l.startswith('@demo'))


def build_index():
    L = ['# Приёмы подачи: как выбрать', '',
         '> Файл собран `build_docs.py` из `catalog.py`. Руками не править.', '',
         'Читать на этапе «ТЗ на слайд» для каждого слайда с экспонатом. Порядок:', '',
         '1. **Что говорит слайд?** Найди тип сообщения в таблице 1 по заголовку-выводу слайда.',
         '2. **Какая форма у данных?** Из кандидатов типа выбери по таблице 2: сигналы в ТЗ, «не брать, если», потолки.',
         '3. **Запиши в ТЗ** строку «Экспонат: <приём> (стиль), почему: <одна фраза про сообщение и данные>».',
         '4. **Открой карточку** `cards/<приём>.md`: вход, параметры, правила, пример вызова, образцы.',
         '5. Ничего не подходит: процедура «новый тип слайда» (2–3 варианта пользователю словами, выбранный пишется функцией в `exhibits/`, см. SKILL.md).', '',
         '## Таблица 1. Тип сообщения → кандидаты', '', '| Тип | Что говорит слайд | Приёмы |', '|---|---|---|']
    for mid, name, says in C.MESSAGES:
        cands = [p['id'] for p in C.P if mid in p['msg']]
        L.append(f"| {name} | {says} | {', '.join(f'`{c}`' for c in cands) or '–'} |")
    L += ['', '## Таблица 2. Приёмы', '', '| Приём | Что говорит | Сигналы в ТЗ | Не брать, если | Потолки |', '|---|---|---|---|---|']
    for p in C.P:
        L.append(f"| `{p['id']}` {p['name']} | {p['says']} | {p['signals']} | {p['not_when']} | {p['limits']} |")
    L += ['', '## Как разрешить спор двух приёмов', '']
    L += [f'- **{a}**: {b}' for a, b in C.TIEBREAK]
    L += ['', '## Общие правила (из отбора образцов и стиля v3)', '']
    L += [f'- {t}' for t in C.ANTI_LESSONS]
    L += ['- Один акцент на слайд: цвет получает то, о чём заголовок; остальное серое.',
          '- Подписи у данных вместо легенды и осей, где серий три и меньше.',
          '- Числа по-русски, единица один раз (функции делают сами через `num`).',
          '- Источник на каждом слайде с данными: строкой под экспонатом, это работа слайда, не функции.', '',
          '## Приёмы без кода', '']
    L += [f'- **{n}** (`{i}`): {why}' for n, i, why in C.NO_CODE]
    return '\n'.join(L) + '\n'


def build_card(p, m):
    fn = getattr(X, p['fn'])
    sig = str(inspect.signature(fn))
    L = [f"# {p['name']} (`{p['id']}`)", '', '> Собрано `build_docs.py` из `catalog.py` и кода функции. Руками не править.', '',
         f"**Что говорит слайд.** {p['says']}", '',
         f"**Брать, когда в ТЗ:** {p['signals']}.", '',
         f"**Не брать, если:** {p['not_when']}.", '',
         f"**Данные на вход:** {p['data']}.", '',
         f"**Потолки:** {p['limits']}.", '',
         f"**Типы сообщения:** {', '.join(MSG[x][1] for x in p['msg'])}.", '',
         '## Правила оформления', '']
    L += [f'- {r}' for r in p['rules']]
    L += ['', '## Вызов', '', '```python', 'import sys; sys.path.insert(0, SKILL_DIR)   # SKILL_DIR: папка скилла, см. SKILL.md',
          'import exhibits as X', f"ex = X.{p['fn']}{sig}", 'ex.svg        # строка SVG, ширина 1168 px при 1:1 со слайдом 1280×720',
          'ex.warnings   # наложения, выход за край, мелкий кегль: пусто = чисто', '```', '',
          '## Параметры (из кода)', '', '```', inspect.getdoc(fn) or '', '```', '', '## Пример', '']
    for d in p['demos']:
        L += [f'`{d}` (кадр: `python3 tests/demo.py {d}`)', '', '```python', demo_src(d), '```', '']
    L += ['## Образцы (публичные слайды, описаны словами)', '']
    L += [sample_line(m, i) for i in p['samples']]
    if p['anti']:
        L += ['', '## Антипримеры («Не то»)', '']
        L += [sample_line(m, i) for i in p['anti']]
    return '\n'.join(L) + '\n'


def build_html(m):
    th = X.load_theme()
    os.makedirs(os.path.join(HERE, '_preview'), exist_ok=True)
    nav, secs = [], []
    for p in C.P:
        figs = []
        for d in p['demos']:
            ex = D.DEMOS[d]()
            figs.append(f'<figure class="fig">{ex.svg}<figcaption>{html.escape(d)}</figcaption></figure>')
        samp = ''.join(
            f'<li><b>{html.escape(m.get(i, {}).get("firm", ""))}</b> {html.escape(m.get(i, {}).get("title", ""))} '
            f'<a href="{html.escape(m.get(i, {}).get("url", ""))}">смотреть</a></li>' for i in p['samples'])
        anti = ''.join(
            f'<li class="anti">Не то: {html.escape(m.get(i, {}).get("title", ""))} <a href="{html.escape(m.get(i, {}).get("url", ""))}">смотреть</a></li>'
            for i in p['anti'])
        rules = ''.join(f'<li>{html.escape(r)}</li>' for r in p['rules'])
        nav.append(f'<a href="#{p["id"]}">{html.escape(p["name"])}</a>')
        secs.append(f'''<section id="{p["id"]}"><header><h2>{html.escape(p["name"])}</h2><code>{p["id"]}</code></header>
<p class="says">{html.escape(p["says"])}</p>
<dl><dt>Брать, когда</dt><dd>{html.escape(p["signals"])}</dd><dt>Не брать, если</dt><dd>{html.escape(p["not_when"])}</dd>
<dt>Потолки</dt><dd>{html.escape(p["limits"])}</dd></dl><ul class="rules">{rules}</ul>
<h3>Как рисует функция</h3><div class="figs">{"".join(figs)}</div>
<h3>Образцы</h3><ul class="smps">{samp}{anti}</ul></section>''')
    lessons = ''.join(f'<li>{html.escape(t)}</li>' for t in C.ANTI_LESSONS)
    nocode = ''.join(f'<li><b>{html.escape(n)}</b>: {html.escape(w)}</li>' for n, _, w in C.NO_CODE)
    face = X.preview.font_face(th)
    c = th.colors
    doc = f'''<title>Каталог приёмов</title>
<style>{face}
:root{{--bg:#F4F4F2;--card:#FFFFFF;--ink:{c["ink"]};--muted:{c["muted"]};--line:{c["line"]};--acc:{c["accent"]};--bad:{c["bad"]}}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#15171A;--card:#1E2125;--ink:#E8EAED;--muted:#A0A4AA;--line:#3A3E44;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#15171A;--card:#1E2125;--ink:#E8EAED;--muted:#A0A4AA;--line:#3A3E44;color-scheme:dark}}
body{{background:var(--bg);color:var(--ink);font:15px/1.5 'Golos Text',Arial,sans-serif;margin:0}}
.wrap{{max-width:1320px;margin:0 auto;padding-inline:16px;padding-block:32px 80px}}
h1{{font-size:32px;margin:0 0 8px;text-wrap:balance}} .lead{{color:var(--muted);max-width:70ch;margin:0 0 24px}}
nav{{display:flex;flex-wrap:wrap;gap:6px 14px;margin:0 0 28px;font-size:14px}} nav a{{color:var(--acc);text-decoration:none}}
.box{{background:var(--card);border-radius:8px;padding:20px 24px;margin:0 0 24px}} .box h2{{font-size:18px;margin:0 0 8px}}
section{{background:var(--card);border-radius:8px;padding:24px;margin:0 0 28px}}
section header{{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}} section h2{{font-size:22px;margin:0}}
code{{color:var(--muted);font-size:13px}} .says{{font-size:17px;margin:8px 0 12px}}
dl{{display:grid;grid-template-columns:140px 1fr;gap:4px 16px;margin:0 0 12px;font-size:14px}} dt{{color:var(--muted);font-weight:700}} dd{{margin:0}}
.rules{{font-size:14px;margin:0 0 16px;padding-left:20px}} h3{{font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);margin:20px 0 10px}}
.figs{{display:grid;gap:16px}} .fig{{margin:0;background:#FFFFFF;padding:24px;border-radius:6px;overflow-x:auto}}
.fig svg{{min-width:640px}} .fig figcaption{{font-size:12px;color:#656565;margin-top:8px}}
.smps{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}} .smp{{margin:0;min-width:0}}
.smp img{{width:100%;border-radius:4px;border:1px solid var(--line);display:block}} .smp figcaption{{font-size:12px;color:var(--muted);margin-top:6px}}
.anti img{{opacity:.55;border-color:var(--bad)}} .anti figcaption{{color:var(--bad)}}
@media (max-width:640px){{dl{{grid-template-columns:1fr}}}}
</style>
<div class="wrap"><h1>Каталог приёмов подачи</h1>
<p class="lead">31 приём подачи. У каждого: когда брать и когда нет, как его рисует функция на тестовых данных и ссылки на образцы. Цвета и шрифт берутся из темы, поэтому все рисунки в одном стиле.</p>
<nav>{"".join(nav)}</nav>
<div class="box"><h2>Что отклонено и почему</h2><ul>{lessons}</ul></div>
{"".join(secs)}
<div class="box"><h2>Без кода пока</h2><ul>{nocode}</ul></div></div>'''
    path = os.path.join(HERE, '_preview', 'catalog.html')
    open(path, 'w', encoding='utf-8').write(doc)
    return path


if __name__ == '__main__':
    m = manifest()
    open(os.path.join(HERE, 'INDEX.md'), 'w', encoding='utf-8').write(build_index())
    os.makedirs(os.path.join(HERE, 'cards'), exist_ok=True)
    for p in C.P:
        open(os.path.join(HERE, 'cards', f"{p['id']}.md"), 'w', encoding='utf-8').write(build_card(p, m))
    print('INDEX.md и', len(C.P), 'карточек')
    if '--shots' in sys.argv:
        for p in C.P:
            for d in p['demos']:
                ex = D.DEMOS[d]()
                h = X.sheet([(d, ex)], os.path.join(HERE, '_preview', f'demo_{d}.html'))
                X.shot(h, os.path.join(HERE, '_preview', f'demo_{d}.png'), 1300, ex.h + 200)
                os.remove(h)
        print('кадры демо в _preview/')
    if '--no-html' not in sys.argv:
        print(build_html(m))
