# Phase 6: independent verification

Runs in every mode. The writer of a report is the worst judge of it: a model asked to re-check its own reasoning in the same context tends to confirm it. So verification is done by fresh agents that see the claim and the source, never the draft or the reasoning behind it.

Failures this phase exists to catch, in order of how often they appear in deep research systems:
1. Text that cites a real, relevant page that does not actually say what the sentence says.
2. A true statement with a qualifier missing: "half the cost" measured on an easy subset, when the same page says the result reverses on hard tasks.
3. Modality drift: "recommends" reported as "requires", "evaluates" as "approves", a market benchmark reported as a vendor's price.
4. Conclusions that need a claim nobody confirmed.

And the opposite failure: verifiers discarding true claims because one tool could not find the passage. The protocol guards against both.

## Step 1. Queue the claims

From the draft, take every claim that (a) is in the answer at the top, the conclusions or the recommendations, (b) contains a number, date, legal norm, name or ranking, or (c) a recommendation depends on. Quick: all such claims, at least 5. Standard: at least 10. Deep and ultradeep: all.

**Make each one atomic and self-contained** before queueing. One row, one checkable statement. Split compound sentences. Replace pronouns and implicit context with the subject, the metric, the period, the population or benchmark subset, and who states it. Keep the qualifiers the draft uses: they are part of what must be confirmed.

Write `verify_queue.jsonl`, one JSON object per line: `id`, `claim`, `cited_url`, and for derived numbers `inputs` and `formula`.

## Step 2. Verifiers

One subagent per 5–8 claims, in parallel, on a model strong enough to judge negation, periods and populations (not the smallest one). Each receives only its queue rows and the prompt below, filled per claim. `{{` and `}}` stand for single braces (the template is Python-formatted by `evals/score.py`, so edits here are exactly what the eval set measures).

<!-- VERIFIER_PROMPT_START -->
You are an independent verifier. You have NOT seen the report this claim comes from; that is deliberate.
Your job is to find what in this claim is NOT supported by the source, and what the source says nearby that changes its meaning. Do not look for reasons to agree.

Claim ({id}): {claim}
Cited source: {cited_url}

Steps:
1. Open the page yourself. Order by cost: the built-in fetch first; if it fails, is vague, or you need exact text, a prepaid raw-text tool (for example Bright Data scrape_as_markdown); a metered API (for example Tavily extract) only if both failed, at its basic depth. A summarizing fetch tool may misreport what a page says, so never rely on its "not found". For arXiv try the /html/ version, then the PDF.
2. Find the passage the claim rests on and copy it verbatim.
3. Read around it before judging: the whole paragraph, the next paragraph, the section it belongs to. Then scan the page for qualifiers that limit or reverse it: "however", "but", "only", "except", "on the harder", "reversed", "does not", "limitation", "caveat", "in contrast", and any Limitations section. Quote any qualifier you find.
4. Check meaning, not words: negation; modality (must or required vs recommended or may; approves vs evaluates; prohibits vs advises against; a price or offer vs a market benchmark; in force vs adopted vs repealed); which metric; which period; which population, subset, model or country; whether the source says it or only cites someone else; whether a number is in the text or read off a chart.
5. For derived numbers, recompute from the source inputs and show the arithmetic.

Verdict, exactly one:
- confirmed: a verbatim passage supports the claim as worded, and nothing nearby limits it.
- partial: part is supported and part is not, or the claim is broader than the source (say which part).
- misleading: literally supported, but a qualifier on the same page changes what a reader would conclude (quote the qualifier).
- refuted: a verbatim passage contradicts the claim.
- not_verifiable: the page did not load, or the passage was not found after two different tools.

Reply with one line of JSON: {{"id":"{id}","verdict":"...","quote":"...","qualifier":"...","note":"..."}}
<!-- VERIFIER_PROMPT_END -->

Each verifier writes its lines to `verify_results_<batch>.jsonl` as it goes.

## Step 3. Apply the verdicts

- `confirmed`: keep.
- `partial`: narrow the claim to what the passage supports.
- `misleading`: rewrite the claim with the quoted qualifier in the same sentence. Moving the qualifier to a limitations section only is not enough.
- `refuted`: remove or correct the claim; note the contradicting passage in the limitations.
- `not_verifiable`: keep it, mark it inline `[не проверено]` or `[unverified]` in the language of the report, and list it among the uncertainties. Never delete a claim for this reason alone, and never state it as fact in the answer at the top.

Then re-read the `refuted` and `not_verifiable` lists yourself, opening the sources. Verifiers also throw out true claims; a single tool's failure to find a passage is the usual reason.

## Step 4. Section grounding check (deep and ultradeep only)

Queued claims are a sample. The most common failure of deep research systems is text that is not wrong, just not resting on what it cites. In deep and ultradeep, one more pass reads the answer at the top and every finding in full. One subagent per one or two sections, in parallel. Each receives only the section text and the URLs that section cites, with this prompt:

<!-- SECTION_CHECK_PROMPT_START -->
You check whether a section of a research report rests on the sources it cites. You did not write it.
For every sentence that states a fact (a number, a date, a name, a ranking, a cause, a comparison, a claim about what a source says), decide: grounded (a cited source says it; quote the passage), ungrounded (no cited source says it; say what you searched), or stretched (a source says something narrower or weaker; quote it and say how the sentence goes beyond it). Skip sentences that are plainly the author's own judgment and are worded as such.
Open the sources yourself: built-in fetch first, then a prepaid raw-text tool, a metered API last and at its basic depth. Look for what is NOT supported; do not look for reasons to agree.
Reply with JSON lines, one per factual sentence: {{"sentence":"...","verdict":"grounded|ungrounded|stretched","quote":"...","url":"...","note":"..."}}

Section:
{section}

Sources cited in this section:
{sources}
<!-- SECTION_CHECK_PROMPT_END -->

Rewrite every `stretched` sentence to what the source supports. Rewrite every `ungrounded` sentence as the author's own judgment, worded as such, or remove it. Do not attach a new citation to it unless that citation has gone through step 2.

In quick and standard this step is skipped (it adds roughly a third to the cost of a run); say so in the method section.

## Step 5. Do the conclusions follow?

One more subagent receives the conclusions and recommendations plus the list of confirmed claims (not the full draft). For each conclusion it answers: follows from confirmed claims; overstated (what to narrow); rests on something not in the list; or is the author's judgment (fine if worded as such). It also flags any effect or benefit stated without a measurement behind it. Rewrite accordingly: a conclusion resting on an unconfirmed claim becomes a hypothesis.

## Step 6. Log it

In the report's method section: number of claims checked and the counts per verdict; for the section check, counts of grounded, stretched and ungrounded sentences; what changed in the report because of verification. If the phase could not run at all, the report's title and first line say `UNVERIFIED DRAFT`.
