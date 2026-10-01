#!/usr/bin/env python3
"""Прогон кейсов скилла через `claude -p` и механическая оценка результата.

    python3 run.py --run ~/evals-runs/20261001_v3 --case A01
    python3 run.py --run ~/evals-runs/20261001_v3 --all --jobs 2
    python3 run.py --run ~/evals-runs/20261001_v3 --score-only

Каждый кейс получает отдельную папку <run>/<id>/: prompt.txt, output.md,
result.json (ответ claude -p), score.json. Профиль автора кладётся в
<id>/.claude/anti-ai-writing/profile.md только у кейсов с полем profile;
модели велено не искать профиль за пределами этой папки.

Механика проверяет то, что проверяется без суждения: ошибки check.py,
сохранность фактов (must_keep), отсутствие запрещённого (must_not), новые
числа, которых не было во входе, близость к исходнику у кейсов «не трогать».
Голос и уместность правки оцениваются чтением выходов.
"""

import argparse
import difflib
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(SKILL / "scripts"))
import check  # noqa: E402

PROMPT = """Прочитай {skill}/SKILL.md и следуй ему; справочники из {skill}/references открывай, когда SKILL.md велит.
Профиль автора ищи только в текущей папке (.claude/anti-ai-writing/profile.md). В домашней папке не ищи.
Канал: {channel}.

Задача: {task}

Текст:
<<<
{text}
>>>

{deliver}"""

DELIVER = {
    "audit": "Запиши разбор в файл {out}.",
    "default": "Запиши в файл {out} только итоговый текст, ровно в том виде, в каком его получит читатель: без заголовков, пояснений и разбора. Отчёт о правке, если он нужен, дай в ответе, не в файле.",
}

NUM = re.compile(r"\d+(?:[.,]\d+)?")


def load_cases():
    with open(HERE / "cases.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_case(case, run_dir, model, skill_dir, timeout_min):
    d = run_dir / case["id"]
    d.mkdir(parents=True, exist_ok=True)
    if case.get("profile"):
        p = d / ".claude" / "anti-ai-writing"
        p.mkdir(parents=True, exist_ok=True)
        (p / "profile.md").write_text(case["profile"], encoding="utf-8")
    out = d / "output.md"
    deliver = DELIVER.get(case["mode"], DELIVER["default"]).format(out=out)
    prompt = PROMPT.format(skill=skill_dir, channel=case["channel"], task=case["task"], text=case["text"], deliver=deliver)
    (d / "prompt.txt").write_text(prompt, encoding="utf-8")
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "json",
           "--add-dir", str(skill_dir), "--allowedTools", "Read", "Write", "Bash(python3:*)"]
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=timeout_min * 60)
        stdout, rc, err = proc.stdout, proc.returncode, proc.stderr[-2000:]
    except subprocess.TimeoutExpired:
        stdout, rc, err = "", -1, "timeout"
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError:
        result = {"raw_stdout_tail": stdout[-2000:]}
    result.update({"returncode": rc, "stderr_tail": err, "minutes": round((time.time() - t0) / 60, 1), "model": model})
    (d / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return score_case(case, run_dir)


def score_case(case, run_dir):
    d = run_dir / case["id"]
    out = d / "output.md"
    if not out.exists():
        s = {"id": case["id"], "ok": False, "fail": ["нет output.md"]}
        (d / "score.json").write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        return s
    text = out.read_text(encoding="utf-8")
    fail, note = [], []
    for pat in case.get("must_keep", []):
        if not re.search(pat, text):
            fail.append(f"пропало: {pat}")
    for pat in case.get("must_not", []):
        if re.search(pat, text):
            fail.append(f"осталось или появилось: {pat}")
    if case["mode"] != "audit":
        errors = [f for f in check.check(text, case["channel"]) if f["level"] == "error"]
        if errors:
            fail.append("check.py: " + "; ".join(f"{f['rule']} ({f['fragment']})" for f in errors[:5]))
        new_nums = sorted(set(NUM.findall(text)) - set(NUM.findall(case["text"])))
        if new_nums:
            fail.append(f"новые числа: {', '.join(new_nums)}")
        if case.get("decision_must"):
            k = case.get("decision_within", 1)
            head = " ".join(re.split(r"(?<=[.!?])\s+", text.strip())[:k])
            if not re.search(case["decision_must"], head, re.I):
                fail.append(f"решение не в первых {k} фразах: {head[:100]}")
        sim = difflib.SequenceMatcher(None, case["text"], text.strip()).ratio()
        note.append(f"близость к исходнику {sim:.2f}")
        if case.get("min_similarity") and sim < case["min_similarity"]:
            fail.append(f"переписан хороший текст: близость {sim:.2f} < {case['min_similarity']}")
    s = {"id": case["id"], "ok": not fail, "fail": fail, "note": note}
    (d / "score.json").write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    return s


def main():
    ap = argparse.ArgumentParser(description="Прогон кейсов anti-ai-writing")
    ap.add_argument("--run", required=True, help="папка прогона вне репозитория")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--case", action="append", help="id кейса, можно несколько раз")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--score-only", action="store_true", help="пересчитать оценки по готовым output.md")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--skill-dir", default=str(SKILL), help="папка скилла; для сравнения версий укажите старую копию")
    ap.add_argument("--jobs", type=int, default=2, help="параллельных claude -p, не больше 2")
    ap.add_argument("--timeout-min", type=int, default=10)
    a = ap.parse_args()

    run_dir = Path(a.run).expanduser()
    cases = load_cases()
    if a.case:
        cases = [c for c in cases if c["id"] in a.case]
    if a.score_only:
        results = [score_case(c, run_dir) for c in cases if (run_dir / c["id"]).exists()]
    else:
        with ThreadPoolExecutor(max_workers=min(a.jobs, 2)) as ex:
            results = list(ex.map(lambda c: run_case(c, run_dir, a.model, a.skill_dir, a.timeout_min), cases))
    passed = 0
    for s in sorted(results, key=lambda s: s["id"]):
        passed += s["ok"]
        extra = "" if s["ok"] else " | " + " | ".join(s["fail"])
        print(f"{s['id']}: {'OK' if s['ok'] else 'FAIL'} {' '.join(s.get('note', []))}{extra}")
    print(f"Прошло {passed} из {len(results)}")
    (run_dir / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
