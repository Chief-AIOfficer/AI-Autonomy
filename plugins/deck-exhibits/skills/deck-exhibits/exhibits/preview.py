"""Просмотр: лист рисунков в HTML со вшитым шрифтом и кадр PNG через headless Chrome.
Смотреть глазами каждый рисунок до отдачи (правило стиля v3); предупреждения печатаются под рисунком."""
import base64
import pathlib
import html
import os
import shutil
import subprocess

from .core import load_theme

_CHROME_PATHS = (
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
)


def find_chrome():
    """Браузер для кадров и PDF: переменная окружения CHROME, затем PATH, затем обычные места на macOS и Windows."""
    env = os.environ.get('CHROME')
    if env and os.path.exists(env):
        return env
    for name in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome', 'msedge', 'microsoft-edge'):
        p = shutil.which(name)
        if p:
            return p
    for p in _CHROME_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError('не найден Chrome, Chromium или Edge: установи браузер или укажи путь в переменной окружения CHROME')


try:   # старое имя для сборок, которые берут путь к браузеру из exhibits.preview.CHROME
    CHROME = find_chrome()
except FileNotFoundError:
    CHROME = _CHROME_PATHS[0]


def font_face(theme=None):
    th = theme or load_theme()
    with open(th.font_file, 'rb') as fh:
        b64 = base64.b64encode(fh.read()).decode()
    return (f"@font-face{{font-family:'{th.family}';src:url(data:font/ttf;base64,{b64}) format('truetype');"
            f"font-weight:100 900;font-display:block}}")


def sheet(items, path, title='Приёмы', theme=None, slide=False):
    """items: [(подпись, Exhibit)]. slide=True обрамляет рисунок полем слайда 1280×720 для проверки пропорций."""
    th = theme or load_theme()
    blocks = []
    for cap, ex in items:
        warn = ''.join(f'<li>{html.escape(w)}</li>' for w in ex.warnings)
        warn = f'<ul class="w">{warn}</ul>' if warn else '<p class="ok">проверки: чисто</p>'
        blocks.append(f'<section><h2>{html.escape(cap)}</h2><div class="fig">{ex.svg}</div>{warn}</section>')
    doc = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>{font_face(th)}
body{{margin:0;background:#E9E9E9;font-family:'{th.family}',{th.fallback};color:{th.c('ink')}}}
section{{background:#fff;width:{th.width}px;margin:24px auto;padding:56px 56px 24px}}
h2{{font-size:13px;font-weight:700;color:{th.c('muted')};margin:0 0 28px;letter-spacing:.02em}}
.w{{color:{th.c('bad')};font-size:13px;margin:16px 0 0}} .ok{{color:{th.c('muted')};font-size:12px;margin:16px 0 0}}
</style></head><body>{''.join(blocks)}</body></html>"""
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(doc)
    return path


def shot(html_path, png_path, width=1300, height=None):
    """Кадр страницы целиком. Высоту по умолчанию берём с запасом, Chrome обрежет пустое не сам, поэтому задаём явно."""
    height = height or 4000
    subprocess.run([find_chrome(), '--headless=new', '--disable-gpu', '--hide-scrollbars', f'--window-size={width},{height}',
                    f'--screenshot={png_path}', '--virtual-time-budget=3000', pathlib.Path(html_path).resolve().as_uri()],
                   capture_output=True, timeout=90)
    return png_path
