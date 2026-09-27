# Report: phases 5, 7, 8

## 5. Draft

Write the report in the language of the question. Write it to `report.md` in the run folder section by section (one write or edit per section), so a long report never depends on a single huge output.

### Structure

Section names may be in English or in the report's language; the validator accepts both (Russian names in brackets).

1. **Answer** (Главное / Резюме). 200–400 words that stand on their own: the answer to the question first, then the 3–5 findings it rests on, then one line on confidence and the biggest open gap. A reader who stops here must be able to act. No references to later sections ("see finding 3"), no internal labels or codes, no jargon the reader has not been given.
2. **Question and method** (Вопрос и метод). The question, the decision it feeds, boundaries, assumptions, and in two or three sentences how the research was done.
3. **Findings** (Находки). 3–8 findings, each a heading that states the finding as a sentence, then the argument from evidence. As long as the evidence needs, no longer.
4. **Conclusions** (Выводы). What follows across findings: patterns, tensions, implications. The author's judgment is allowed here and is worded as judgment.
5. **Limitations** (Ограничения). What was not found by this search (with the queries), open contradictions, claims marked unverified, where evidence is thin or one-sided.
6. **Recommendations** (Рекомендации), when the question calls for action. Each says what to do and what it rests on; an effect that was not measured is not presented as measured.
7. **Sources** (Источники / Библиография). Every `[n]` used in the text, one per line: `[n] Author or organization (year). "Title". Publisher. URL (accessed YYYY-MM-DD)`. No ranges, no "and others".
8. **Method** (Метод). Mode, tools used, collectors and what each covered, verification counts per verdict, what verification changed, anything skipped and why.

### Writing rules

- Every factual sentence carries its citation `[n]` in the same sentence. Opinion and inference are worded as such ("this suggests", "in my judgment").
- Numbers keep the unit and scope of the source: what was measured, on what, when. A number read off a chart is labelled as such.
- Mostly prose. Lists for things that really are lists; tables for comparisons.
- No padding: every paragraph carries a fact, a comparison or a conclusion. Do not restate the question or other sections.
- Low-confidence claims are shown as low confidence. "Not found by this search" is written as such.

### Length ceilings

| Mode | Ceiling | Usual |
|---|---|---|
| quick | 2,500 words | 800–2,000 |
| standard | 6,000 | 2,500–5,000 |
| deep | 10,000 | 4,000–8,000 |
| ultradeep | 15,000 | 8,000–12,000 |

### Callouts

Use Obsidian callout syntax for the few things a reader must not miss; they render in Obsidian and in the HTML:

```
> [!note] Label
> Text.
```

Types: `note` (neutral), `tip` or `success` (a positive finding), `warning` (a caveat), `danger` (a refuted belief or a serious risk). Two or three per report at most.

## 7. Critique (deep and ultradeep)

After verification, a fresh subagent reads the whole report as a skeptical expert in the field and answers: what important aspect is missing; which conclusion is stronger than its evidence; which source is weaker than the report treats it; what an informed opponent would say. If the critique reveals a real gap in knowledge (not just wording), go back to collection with targeted queries, time-boxed, and send any new claims through verification. Record what the critique changed in the method section.

## 8. Deliver

```bash
# once, at the start of the run
python3 <skill>/scripts/init_run.py "<Topic>" [--dir <parent folder>] [--mode deep]

# at the end
python3 <skill>/scripts/validate_report.py <run>/report.md --mode <mode>
python3 <skill>/scripts/check_links.py <run>/report.md
python3 <skill>/scripts/md_to_html.py <run>/report.md
```

`<skill>` is the folder this file lives in, one level up. `validate_report.py` fails on missing sections, citations without a bibliography entry, placeholders, or a report over the mode's ceiling; fix and re-run. `check_links.py` fails on dead links; sites that refuse scripts are listed for a manual check instead (the verifiers already opened them). `md_to_html.py` writes `report.html` next to `report.md`.

Deliver both files. In the final message give the paths, the answer in two or three sentences, and the verification counts.
