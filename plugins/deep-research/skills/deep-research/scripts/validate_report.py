#!/usr/bin/env python3
"""Check a research report before delivery.

    python3 validate_report.py report.md [--mode standard]

Errors (exit 1): a required section is missing; a citation [n] has no entry in
the sources section; the sources section uses ranges or placeholders; the
text contains placeholders; the report is over the mode's length ceiling.
Warnings: answer section outside 200-400 words, sources listed but never cited,
source entries without a URL.
Section names are accepted in English or Russian.
"""

import argparse
import re
import sys
from pathlib import Path

CEILING = {'quick': 2500, 'standard': 6000, 'deep': 10000, 'ultradeep': 15000}

SECTIONS = {
    'answer': r'answer|executive\s+summary|summary|главное|резюме|краткое\s+резюме|ответ',
    'method_intro': r'question\s+and\s+method|introduction|вопрос\s+и\s+метод|введение|вопрос',
    'findings': r'findings|main\s+analysis|находки|основной\s+анализ|анализ',
    'conclusions': r'conclusions|synthesis|выводы|синтез',
    'limitations': r'limitations|ограничения',
    'sources': r'sources|bibliography|references|источники|библиография|список\s+источников|литература',
    'method': r'method|methodology|метод|методология',
}
REQUIRED = ('answer', 'method_intro', 'findings', 'conclusions', 'limitations', 'sources', 'method')

PLACEHOLDERS = [
    r'\bTODO\b', r'\bTBD\b', r'\bFIXME\b', r'lorem ipsum', r'\[citation needed\]',
    r'\[(?:ссылка|источник)\s+нужн', r'\bXXX\b', r'<\s*(?:вставить|insert)',
]


def split_sections(text: str) -> list:
    """[(heading_text, body)] for level-2 headings."""
    parts = re.split(r'^##\s+(?!#)(.+)$', text, flags=re.M)
    return [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def classify(heading: str):
    # A heading may carry both languages ("Answer. Главное"); first match in REQUIRED order wins,
    # except that 'method' must not swallow "Question and method".
    h = heading.lower()
    for key in ('method_intro', 'answer', 'findings', 'conclusions', 'limitations', 'sources', 'method'):
        if re.search(r'(?:^|[\s.:(/-])(?:' + SECTIONS[key] + r')(?:$|[\s.:)/,-])', ' ' + h + ' '):
            return key
    return None


def words(s: str) -> int:
    return len(re.findall(r'\w+', s, flags=re.UNICODE))


def validate(text: str, mode: str = 'standard') -> tuple:
    errors, warnings = [], []
    sections = split_sections(text)
    found = {}
    for heading, body in sections:
        key = classify(heading)
        if key and key not in found:
            found[key] = body

    for key in REQUIRED:
        if key not in found:
            errors.append(f'missing section: {key}')

    if 'answer' in found:
        n = words(found['answer'])
        if n < 200 or n > 400:
            warnings.append(f'answer section has {n} words (aim for 200-400)')

    sources = found.get('sources', '')
    body_text = text.replace(sources, '') if sources else text
    cited = {int(n) for grp in re.findall(r'\[(\d+(?:\s*[,;]\s*\d+)*)\]', body_text)
             for n in re.findall(r'\d+', grp)}
    listed = {}
    for m in re.finditer(r'^\s*\[(\d+)\]\s*(.*)$', sources, flags=re.M):
        listed[int(m.group(1))] = m.group(2)
    if re.search(r'^\s*\[\d+\s*[-–]\s*\d+\]', sources, flags=re.M):
        errors.append('sources section lists a range like [3-50]; list every source')
    missing = sorted(cited - set(listed))
    if missing:
        errors.append(f'cited but not in sources: {missing}')
    unused = sorted(set(listed) - cited)
    if unused:
        warnings.append(f'in sources but never cited: {unused}')
    no_url = sorted(n for n, entry in listed.items() if not re.search(r'https?://', entry))
    if no_url:
        warnings.append(f'source entries without a URL: {no_url}')

    for pat in PLACEHOLDERS:
        if re.search(pat, text, flags=re.I):
            errors.append(f'placeholder text matches /{pat}/')

    total = words(body_text)
    ceiling = CEILING[mode]
    if total > ceiling:
        errors.append(f'{total} words, over the {mode} ceiling of {ceiling}')

    return errors, warnings, {'words': total, 'cited': len(cited), 'sources': len(listed)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('report')
    ap.add_argument('--mode', choices=tuple(CEILING), default='standard')
    a = ap.parse_args()
    text = Path(a.report).read_text(encoding='utf-8')
    errors, warnings, stats = validate(text, a.mode)
    print(f"{stats['words']} words, {stats['cited']} sources cited, {stats['sources']} listed")
    for w in warnings:
        print(f'WARNING: {w}')
    for e in errors:
        print(f'ERROR: {e}')
    print('FAILED' if errors else 'PASSED')
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
