#!/usr/bin/env python3
"""Render a research report from Markdown to a standalone HTML page.

    python3 md_to_html.py report.md [-o report.html] [--template PATH]

Handles the Markdown a report uses: YAML front matter (dropped, `title` and
`date` are read), headings, paragraphs, bold, italics, inline code, links,
bare URLs, bullet and numbered lists (one nesting level), tables, block
quotes, fenced code, Obsidian callouts (> [!note] Label), and citations [n]
linked to the numbered entries of the sources section. Standard library only.
"""

import argparse
import datetime as dt
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = HERE.parent / 'templates' / 'report.html'

CALLOUT_CLASS = {'note': 'accent', 'info': 'accent', 'abstract': 'accent', 'tip': 'ok', 'success': 'ok',
                 'check': 'ok', 'warning': 'warn', 'caution': 'warn', 'attention': 'warn',
                 'danger': 'bad', 'error': 'bad', 'bug': 'bad', 'failure': 'bad'}
SOURCES_RE = r'sources|bibliography|references|источники|библиография|список\s+источников|литература'
ANSWER_RE = r'answer|executive\s+summary|главное|резюме|ответ'
# a URL may contain one level of balanced parentheses (Wikipedia: .../Python_(language))
URL_RE = r'https?://(?:[^\s()<>\]]|\([^\s()<>]*\))+'


def front_matter(text: str) -> tuple:
    meta = {}
    m = re.match(r'^---\n(.*?)\n---\n', text, flags=re.S)
    if not m:
        return meta, text
    for line in m.group(1).splitlines():
        kv = re.match(r'^(\w[\w-]*):\s*(.*)$', line)
        if kv:
            meta[kv.group(1)] = kv.group(2).strip().strip('"\'')
    return meta, text[m.end():]


def slugify(s: str, used: set) -> str:
    base = re.sub(r'[^\w\s-]', '', s.lower(), flags=re.UNICODE).strip()
    base = re.sub(r'[\s_]+', '-', base)[:60] or 'section'
    slug, n = base, 2
    while slug in used:
        slug, n = f'{base}-{n}', n + 1
    used.add(slug)
    return slug


def split_trailing(url: str) -> tuple:
    """Split sentence punctuation and an unmatched closing parenthesis off the end of a bare URL."""
    end = len(url)
    while end and (url[end - 1] in '.,;:' or (url[end - 1] == ')' and url.count('(', 0, end) < url.count(')', 0, end))):
        end -= 1
    return url[:end], url[end:]


def inline(s: str) -> str:
    """Markdown inline syntax to HTML. Code spans are protected first."""
    codes = []

    def keep_code(m):
        codes.append(html.escape(m.group(1)))
        return f'\x00{len(codes) - 1}\x00'

    s = re.sub(r'`([^`]+)`', keep_code, s)
    links = []

    def keep_link(m):
        links.append((m.group(1), m.group(2)))
        return f'\x01{len(links) - 1}\x01'

    s = re.sub(r'\[([^\]]+)\]\((' + URL_RE + r'|#[^)\s]*|[^)\s:]+\.(?:md|html))\)', keep_link, s)  # no ':' in relative links: javascript:x.html
    urls = []

    def keep_url(m):
        url, tail = split_trailing(m.group(0))
        urls.append(url)
        return f'\x02{len(urls) - 1}\x02{tail}'

    # bare URLs are kept out of emphasis: https://x.org/_next_/a must not turn into <em>
    s = re.sub(r'(?<![\w"=/])' + URL_RE, keep_url, s)
    s = html.escape(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', s)
    s = re.sub(r'(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)', r'<em>\1</em>', s)

    def cite(m):
        nums = re.findall(r'\d+', m.group(1))
        return ''.join(f'<a class="cite" href="#ref-{n}">[{n}]</a>' for n in nums)

    s = re.sub(r'\[(\d+(?:\s*[,;]\s*\d+)*)\](?!\()', cite, s)
    s = re.sub(r'\x02(\d+)\x02', lambda m: '<a href="{0}">{0}</a>'.format(html.escape(urls[int(m.group(1))])), s)
    s = re.sub(r'\x01(\d+)\x01', lambda m: '<a href="{}">{}</a>'.format(
        html.escape(links[int(m.group(1))][1]), inline(links[int(m.group(1))][0])), s)
    s = re.sub(r'\x00(\d+)\x00', lambda m: f'<code>{codes[int(m.group(1))]}</code>', s)
    return s


def table(lines: list) -> str:
    def cells(line):
        return [c.strip() for c in line.strip().strip('|').split('|')]
    head = cells(lines[0])
    rows = [cells(l) for l in lines[2:]]
    out = ['<div class="tw"><table><thead><tr>']
    out += [f'<th>{inline(c)}</th>' for c in head]
    out.append('</tr></thead><tbody>')
    for r in rows:
        out.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)


def list_block(lines: list) -> str:
    """Bullet or numbered list with one nesting level (indent >= 2 spaces)."""
    def tag(line):
        return 'ol' if re.match(r'\s*\d+[.)]\s', line) else 'ul'

    out, stack = [], []
    for line in lines:
        indent = len(line) - len(line.lstrip(' '))
        level = 1 if indent >= 2 else 0
        item = re.sub(r'^\s*(?:[-*+]|\d+[.)])\s+', '', line)
        t = tag(line)
        while len(stack) > level + 1:
            out.append(f'</li></{stack.pop()}>')
        if len(stack) == level + 1:
            out.append('</li>')
        else:
            out.append(f'<{t}>')
            stack.append(t)
        out.append(f'<li>{inline(item)}')
    while stack:
        out.append(f'</li></{stack.pop()}>')
    return ''.join(out)


def blockquote(lines: list) -> str:
    body = [re.sub(r'^>\s?', '', l) for l in lines]
    m = re.match(r'\[!(\w+)\][+-]?\s*(.*)$', body[0]) if body else None
    if m:
        kind = CALLOUT_CLASS.get(m.group(1).lower(), 'accent')
        label = m.group(2) or m.group(1).capitalize()
        inner = render_blocks(body[1:], sources=False)
        return f'<div class="note {kind}"><div class="lbl">{inline(label)}</div>{inner}</div>'
    return f'<blockquote>{render_blocks(body, sources=False)}</blockquote>'


def render_blocks(lines: list, sources: bool, ids: set = None, toc: list = None) -> str:
    out, i = [], 0
    ids = ids if ids is not None else set()
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith('```'):
            j = i + 1
            while j < len(lines) and not lines[j].startswith('```'):
                j += 1
            out.append('<pre><code>' + html.escape('\n'.join(lines[i + 1:j])) + '</code></pre>')
            i = j + 1
            continue
        h = re.match(r'^(#{1,4})\s+(.+?)\s*#*$', line)
        if h:
            level, title = len(h.group(1)), h.group(2)
            slug = slugify(title, ids)
            if level == 2 and toc is not None:
                toc.append((slug, title))
            out.append(f'<h{level} id="{slug}">{inline(title)}</h{level}>')
            i += 1
            continue
        if re.match(r'^\s*\|.*\|\s*$', line) and i + 1 < len(lines) and re.match(r'^\s*\|?\s*:?-{2,}', lines[i + 1]):
            j = i
            while j < len(lines) and re.match(r'^\s*\|.*\|\s*$', lines[j]):
                j += 1
            out.append(table(lines[i:j]))
            i = j
            continue
        if line.startswith('>'):
            j = i
            while j < len(lines) and lines[j].startswith('>'):
                j += 1
            out.append(blockquote(lines[i:j]))
            i = j
            continue
        if re.match(r'^\s*(?:[-*+]|\d+[.)])\s+', line) and not (sources and re.match(r'^\s*\[\d+\]', line)):
            j = i
            while j < len(lines) and (re.match(r'^\s*(?:[-*+]|\d+[.)])\s+', lines[j])
                                      or (lines[j].startswith('  ') and lines[j].strip())):
                j += 1
            out.append(list_block(lines[i:j]))
            i = j
            continue
        if re.match(r'^-{3,}\s*$|^\*{3,}\s*$', line):
            out.append('<hr>')
            i += 1
            continue
        if sources and re.match(r'^\s*\[(\d+)\]', line):
            n = re.match(r'^\s*\[(\d+)\]', line).group(1)
            rest = re.sub(r'^\s*\[\d+\]\s*', '', line)
            out.append(f'<p id="ref-{n}"><strong>[{n}]</strong> {inline(rest)}</p>')
            i += 1
            continue
        j = i
        para = []
        while j < len(lines) and lines[j].strip() and not re.match(
                r'^(#{1,4}\s|```|>|\s*(?:[-*+]|\d+[.)])\s+|\s*\|.*\|\s*$)', lines[j]):
            para.append(lines[j].strip())
            j += 1
        if not para:  # a line no rule consumed; render it as text rather than loop forever
            para, j = [line.strip()], i + 1
        out.append(f'<p>{inline(" ".join(para))}</p>')
        i = j
    return '\n'.join(out)


def render(md: str, template: str, source_name: str = 'report.md') -> str:
    meta, body = front_matter(md)
    lines = body.splitlines()
    title = meta.get('title')
    if lines and re.match(r'^#\s+', lines[0].strip()) and not lines[0].startswith('##'):
        title = title or lines[0].lstrip('#').strip()
        lines = lines[1:]
    else:
        for k, l in enumerate(lines):
            if re.match(r'^#\s+[^#]', l):
                title = title or l.lstrip('#').strip()
                lines = lines[:k] + lines[k + 1:]
                break
    title = title or 'Research report'

    # split by level-2 headings so the answer and sources sections get their own styling
    chunks, cur = [], []
    for l in lines:
        if re.match(r'^##\s+(?!#)', l) and cur:
            chunks.append(cur)
            cur = []
        cur.append(l)
    if cur:
        chunks.append(cur)

    ids, toc, parts = set(), [], []
    for chunk in chunks:
        head = chunk[0] if re.match(r'^##\s+', chunk[0]) else ''
        is_sources = bool(re.search(SOURCES_RE, head, flags=re.I))
        is_answer = bool(re.search(ANSWER_RE, head, flags=re.I))
        rendered = render_blocks(chunk, sources=is_sources, ids=ids, toc=toc)
        cls = 'sources' if is_sources else 'answer' if is_answer else ''
        parts.append(f'<section class="{cls}">{rendered}</section>' if cls else rendered)

    toc_html = ''
    if len(toc) >= 3:
        toc_html = ('<nav class="toc"><div class="lbl">Содержание</div><ol>'
                    + ''.join(f'<li><a href="#{s}">{inline(t)}</a></li>' for s, t in toc) + '</ol></nav>')
    lang = 'ru' if re.search(r'[а-яё]', body[:4000], flags=re.I) else 'en'
    date = meta.get('date') or dt.date.today().isoformat()
    fields = {
        'lang': lang,
        'title': html.escape(title),
        'kicker': 'Исследование' if lang == 'ru' else 'Research',
        'meta': html.escape(' · '.join(x for x in (date, meta.get('mode', '')) if x)),
        'toc': toc_html,
        'content': '\n'.join(parts),
        'footer': html.escape(f'Собрано из {source_name}' if lang == 'ru' else f'Rendered from {source_name}'),
    }
    out = template
    for k, v in fields.items():
        out = out.replace('{{' + k + '}}', v)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('report')
    ap.add_argument('-o', '--out')
    ap.add_argument('--template', default=str(DEFAULT_TEMPLATE))
    a = ap.parse_args()
    src = Path(a.report)
    out = Path(a.out) if a.out else src.with_suffix('.html')
    try:
        page = render(src.read_text(encoding='utf-8'), Path(a.template).read_text(encoding='utf-8'), src.name)
    except OSError as e:
        sys.exit(f'Cannot read input: {e}')
    out.write_text(page, encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
