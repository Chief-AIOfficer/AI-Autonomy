#!/usr/bin/env python3
"""
Eval harness helpers for the deep-research skill.

The skill runs are agentic, so this script does not launch them. It does the
deterministic parts around them:

  check           regex hints for key facts / known errors in one report
  judge-prompt    assemble the prompt for one LLM grader (groundedness,
                  coverage, source_quality) for one report
  verifier-prompt assemble the phase 6 verifier prompt for one verifier case
  verifier-score  compare verifier verdicts with the expected ones
  summary         aggregate grades of a run folder into summary.md

Run layout (outside the skill repo):
  <any folder outside the repo>/<YYYYMMDD>_<label>/
      E01/t1/report.md   E01/t1/grades.jsonl   E01/t1/check.json
      verifier/results.jsonl
See README.md for the protocol.
"""

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRADERS = ('groundedness', 'coverage', 'source_quality')
NOT_FOUND_RE = re.compile(r'не найден\w* (этим|в этом) поиск|not found by this search', re.I)
CITATION_RE = re.compile(r'\[(\d+)\]')


def load_jsonl(path: Path) -> list:
    with open(path, encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def get_case(case_id: str, path: Path = HERE / 'cases.jsonl') -> dict:
    for c in load_jsonl(path):
        if c['id'] == case_id:
            return c
    raise SystemExit(f'Unknown case {case_id} in {path.name}')


def check(case: dict, report: str) -> dict:
    """Deterministic hints. They point graders at places to look; they are not a verdict."""
    def hits(items, key):
        out = []
        for it in items:
            hint = it.get('hint')
            found = bool(hint and re.search(hint, report, re.I))
            out.append({key: it[key], 'hint': hint, 'hint_found': found if hint else None})
        return out

    return {
        'case': case['id'],
        'key_facts': hits(case.get('key_facts', []), 'fact'),
        'known_errors': hits(case.get('known_errors', []), 'error'),
        'citations': len(set(CITATION_RE.findall(report))),
        'words': len(report.split()),
        'not_found_phrase': bool(NOT_FOUND_RE.search(report)),
    }


def judge_prompt(case: dict, report: str, grader: str) -> str:
    if grader not in GRADERS:
        raise SystemExit(f'grader must be one of {GRADERS}')
    fields = {
        'groundedness': ('question', 'known_errors'),
        'coverage': ('question', 'key_facts', 'expect'),
        'source_quality': ('question', 'ground_truth'),
    }[grader]
    case_view = {k: case.get(k) for k in fields}
    rubric = (HERE / 'graders' / f'{grader}.md').read_text(encoding='utf-8')
    return (f'{rubric}\n\n## Кейс\n\n```json\n{json.dumps(case_view, ensure_ascii=False, indent=2)}\n```\n\n'
            f'## Отчёт\n\n{report}\n')


SKILL_GATES = HERE.parent / 'reference' / 'verification.md'


def skill_verifier_template() -> str:
    """The verifier prompt the skill actually uses (between markers in verification.md)."""
    text = SKILL_GATES.read_text(encoding='utf-8')
    m = re.search(r'<!-- VERIFIER_PROMPT_START -->\n(.*?)<!-- VERIFIER_PROMPT_END -->', text, re.S)
    if not m:
        raise SystemExit('Verifier prompt markers not found in reference/verification.md')
    return m.group(1).strip()


def verifier_prompt(case: dict) -> str:
    return skill_verifier_template().format(**case)


def verifier_score(results: list, cases: list) -> dict:
    expected = {c['id']: c['expected'] for c in cases}
    rows = []
    for r in results:
        exp = expected.get(r['id'])
        if exp is None:
            continue
        rows.append({'id': r['id'], 'verdict': r.get('verdict'), 'expected': exp,
                     'pass': r.get('verdict') in exp})
    passed = sum(r['pass'] for r in rows)
    return {'passed': passed, 'total': len(rows), 'rate': round(passed / len(rows), 3) if rows else None,
            'missing': sorted(set(expected) - {r['id'] for r in rows}), 'rows': rows}


def summary(run_dir: Path) -> str:
    per_case = {}
    for grades in sorted(run_dir.glob('E*/t*/grades.jsonl')):
        case_id = grades.parent.parent.name
        for g in load_jsonl(grades):
            per_case.setdefault(case_id, {}).setdefault(g['grader'], []).append(float(g['score']))

    lines = [f'# Итог прогона {run_dir.name}', '',
             '| Кейс | ' + ' | '.join(GRADERS) + ' | прогонов |', '|---|' + '---|' * (len(GRADERS) + 1)]
    overall = {g: [] for g in GRADERS}
    for case_id, by_grader in sorted(per_case.items()):
        cells = []
        for g in GRADERS:
            vals = by_grader.get(g, [])
            overall[g].extend(vals)
            cells.append(f'{statistics.mean(vals):.2f}' + (f' (±{statistics.pstdev(vals):.2f})' if len(vals) > 1 else '')
                         if vals else 'n/a')
        trials = max(len(v) for v in by_grader.values())
        lines.append(f'| {case_id} | ' + ' | '.join(cells) + f' | {trials} |')
    lines.append('| **среднее** | ' + ' | '.join(f'{statistics.mean(v):.2f}' if v else 'n/a'
                                                 for v in overall.values()) + ' | |')

    vres = run_dir / 'verifier' / 'results.jsonl'
    if vres.exists():
        vs = verifier_score(load_jsonl(vres), load_jsonl(HERE / 'verifier_cases.jsonl'))
        lines += ['', f'Проверяющий фазы 5.5: {vs["passed"]}/{vs["total"]} вердиктов совпали с эталоном.']
        lines += [f'- {r["id"]}: {r["verdict"]}, ожидалось {"/".join(r["expected"])}' for r in vs['rows'] if not r['pass']]
    lines += ['', 'Число это сигнал, а не приговор: перед выводом прочитать 2-3 транскрипта и grades.jsonl провалившихся кейсов.']
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('check'); p.add_argument('--case', required=True); p.add_argument('--report', required=True)
    p = sub.add_parser('judge-prompt'); p.add_argument('--case', required=True); p.add_argument('--report', required=True)
    p.add_argument('--grader', required=True, choices=GRADERS)
    p = sub.add_parser('verifier-prompt'); p.add_argument('--case', required=True)
    p = sub.add_parser('verifier-score'); p.add_argument('--results', required=True)
    p = sub.add_parser('summary'); p.add_argument('--run', required=True)
    a = ap.parse_args()

    if a.cmd == 'check':
        print(json.dumps(check(get_case(a.case), Path(a.report).read_text(encoding='utf-8')), ensure_ascii=False, indent=2))
    elif a.cmd == 'judge-prompt':
        print(judge_prompt(get_case(a.case), Path(a.report).read_text(encoding='utf-8'), a.grader))
    elif a.cmd == 'verifier-prompt':
        print(verifier_prompt(get_case(a.case, HERE / 'verifier_cases.jsonl')))
    elif a.cmd == 'verifier-score':
        res = verifier_score(load_jsonl(Path(a.results)), load_jsonl(HERE / 'verifier_cases.jsonl'))
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(0 if res['total'] and res['passed'] == res['total'] else 1)
    elif a.cmd == 'summary':
        run = Path(a.run).expanduser()
        text = summary(run)
        (run / 'summary.md').write_text(text, encoding='utf-8')
        print(text)


if __name__ == '__main__':
    main()
