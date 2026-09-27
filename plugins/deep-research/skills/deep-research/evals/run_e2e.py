#!/usr/bin/env python3
"""
Run one end-to-end eval case through the deep-research skill in a headless
`claude -p` session (a subagent cannot run the skill: it cannot spawn the
skill's collectors and verifiers).

  python3 run_e2e.py --case E05 --trial t1 --run /path/to/runs/20260927_label

Writes into <run>/<case>/<trial>/:
  report.md        the final report the session was told to write
  result.json      claude -p JSON result (cost equivalent, turns, session_id)
  transcript.txt   path to the session transcript (.jsonl) for reading
  prompt.txt       the exact prompt sent

The prompt contains only the case question and mode, never key_facts or
known_errors. --skill-dir lets you run an older version checked out with
`git worktree add /tmp/dr-old <commit>`.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from score import get_case  # noqa: E402

ALLOWED_TOOLS = [
    'Read', 'Write', 'Edit', 'Glob', 'Grep', 'Agent', 'ToolSearch',
    'WebSearch', 'WebFetch',
    'Bash(python3:*)', 'Bash(mkdir:*)', 'Bash(date:*)', 'Bash(ls:*)', 'Bash(wc:*)',
    'Bash(cat:*)', 'Bash(grep:*)', 'Bash(head:*)', 'Bash(tail:*)', 'Bash(cd:*)',
    'mcp__brightData__*', 'mcp__tavily-mcp__*', 'mcp__apify__*',
]

PROMPT = """Проведи исследование скиллом deep-research. Прочитай {skill}/SKILL.md и следуй ему и его файлам reference/ (скрипты бери из {skill}/scripts/).

Режим: {mode}.
Вопрос: {question}

Условия прогона:
- Работай автономно, уточняющих вопросов не задавай: допущения запиши в отчёт.
- Папку прогона создай внутри {work} (а не в папке по умолчанию).
- Итоговый отчёт в Markdown сохрани ровно по пути {report}, HTML собери рядом скриптом скилла.
"""


def transcript_path(cwd: Path, session_id: str) -> Path:
    # Claude Code replaces every character that is not an ASCII letter or digit, Cyrillic included
    slug = re.sub(r'[^A-Za-z0-9]', '-', str(cwd))
    return Path.home() / '.claude' / 'projects' / slug / f'{session_id}.jsonl'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--case', required=True)
    ap.add_argument('--trial', default='t1')
    ap.add_argument('--run', required=True)
    ap.add_argument('--skill-dir', default=str(HERE.parent))
    ap.add_argument('--model', default='opus')
    ap.add_argument('--timeout-min', type=int, default=90)
    a = ap.parse_args()

    case = get_case(a.case)
    out = Path(a.run).expanduser() / a.case / a.trial
    work = out / 'work'
    work.mkdir(parents=True, exist_ok=True)
    report = out / 'report.md'
    prompt = PROMPT.format(skill=a.skill_dir, mode=case['mode'], question=case['question'],
                           work=work, report=report)
    (out / 'prompt.txt').write_text(prompt, encoding='utf-8')

    cmd = ['claude', '-p', prompt, '--model', a.model, '--output-format', 'json',
           '--add-dir', str(out), '--add-dir', a.skill_dir,
           '--allowedTools', *ALLOWED_TOOLS]
    t0 = time.time()
    try:
        # claude -p stops waiting for background subagents after 600 s by default and
        # exits without a report; the skill's collectors often run longer.
        env = dict(os.environ, CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS='0')
        proc = subprocess.run(cmd, cwd=out, capture_output=True, text=True, timeout=a.timeout_min * 60, env=env)
        stdout, rc = proc.stdout, proc.returncode
        err = proc.stderr[-2000:]
    except subprocess.TimeoutExpired as e:
        stdout, rc, err = (e.stdout or b'').decode() if isinstance(e.stdout, bytes) else (e.stdout or ''), -1, 'timeout'
    minutes = round((time.time() - t0) / 60, 1)

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError:
        result = {'raw_stdout_tail': stdout[-2000:]}
    result.update({'returncode': rc, 'stderr_tail': err, 'minutes': minutes,
                   'skill_dir': a.skill_dir, 'model': a.model})
    (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if result.get('session_id'):
        (out / 'transcript.txt').write_text(str(transcript_path(out, result['session_id'])) + '\n', encoding='utf-8')

    print(json.dumps({'case': a.case, 'trial': a.trial, 'returncode': rc, 'minutes': minutes,
                      'report_exists': report.exists(),
                      'cost_equivalent_usd': result.get('total_cost_usd'),
                      'turns': result.get('num_turns')}, ensure_ascii=False))
    sys.exit(0 if report.exists() else 1)


if __name__ == '__main__':
    main()
