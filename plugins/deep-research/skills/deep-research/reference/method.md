# Method: phases 0–4

## 0. Tools: build the retrieval ladder from what is installed

Different machines have different tools. Before planning, check what exists: the built-ins (`WebSearch`, `WebFetch`) and any MCP servers (load their schemas with `ToolSearch`, one call listing every tool you expect to need). Sort what you find into capability classes and use the first available tool in each class.

| Capability | Built-in | Common MCP servers (use if installed) |
|---|---|---|
| Web search | `WebSearch` | Brave Search, Tavily `tavily_search`, Exa `web_search_exa`, Perplexity |
| Search engine results with operators (`site:`, geo, Yandex) | – | Bright Data `search_engine`, SerpAPI-style servers |
| Semantic search ("pages like this idea") | – | Exa, Bright Data `discover` |
| Answer a question about a page | `WebFetch` | – |
| Raw text of a page (quotes, tables, numbers) | `WebFetch` (summarized, not raw) | Bright Data `scrape_as_markdown`, Tavily `tavily_extract`, Firecrawl `scrape`, Jina Reader |
| Page behind bot protection, CAPTCHA, JS rendering | – | Bright Data `scrape_as_markdown` (Web Unlocker), Firecrawl |
| Raw text from this machine's own network (sites that refuse cloud IPs, Russian state and bank sites) | `python3 scripts/fetch_raw.py URL` | – |
| Page that needs a real browser or the user's login | – | Claude in Chrome (the user's own browser, see "The user's browser") |
| Crawl a whole site or documentation | – | Apify `website-content-crawler`, Firecrawl `crawl`, Tavily `tavily_crawl` |
| Reddit | none (built-ins are blocked by Reddit) | Bright Data `web_data_reddit_posts`, Apify `reddit-scraper-lite` |
| LinkedIn, company databases | – | Bright Data `web_data_linkedin_*`, `web_data_crunchbase_company` |
| Telegram channels | – | Apify `telegram-scraper` (recent posts only; for a full history ask the user to export the channel) |
| Academic papers | `WebSearch` with `allowed_domains: ["arxiv.org"]` | arXiv, Semantic Scholar servers |

**Order of preference within a class: free and built-in first, then prepaid services, then metered ones.** If the user's own instructions rank the services (for cost or other reasons), their ranking wins. Metered search APIs are used with their cheapest depth setting unless a cheaper call already failed. Do not call an autonomous "research" endpoint of a service (for example `tavily_research`) unless the user asks: it is a paid research run inside the research run.

**Subagents use the same ladder.** `WebSearch` works inside subagents when it is allowed in the user's settings; do not steer subagents to a paid tool by default. If a tool is denied inside a subagent, the subagent says so in its file and uses the next tool in the class.

**One stubborn page:** summarizing fetch, then raw text, then unlocker, then `scripts/fetch_raw.py`, then the user's browser. An empty or negative answer from the summarizing fetch is where you start climbing, not where you stop. For a site that already failed in this run (Russian state sites, banks, cbr.ru, cntd.ru), start at `fetch_raw.py`: cloud fetchers run on foreign data-center IPs that these sites refuse, and they do not trust the Russian Trusted Root CA.

**URLs with non-ASCII characters** (Cyrillic paths, `.рф` hosts) are encoded before any fetch tool gets them: `python3 scripts/fetch_raw.py URL --encode-only`. Bright Data rejects them unencoded, and some sites answer 404.

**`fetch_raw.py` verdicts** say where to go next: `ok` read the text file it names; `network` the site drops foreign IPs (the user can route the domain outside their VPN, otherwise the browser); `antibot` or `blocked` the browser; `not_found` search for the new address. It paces requests to one host (4–12 s by default) across parallel collectors; do not lower the delay. When the system DNS cannot resolve a name (some `.gov.ru` fail through foreign resolvers behind a VPN), it resolves the name through Yandex DNS-over-HTTPS with `curl` and says so in the `dns` field.

### The user's browser

If Claude in Chrome is available, it is the last rung: a real browser, the user's network and the user's own logins (paid subscriptions included). It is slow and there is one of it, so:

- **Only the orchestrator drives it, never a collector.** Collectors that hit `antibot`, `blocked` or a paywall add the URL to a "Needs browser" list at the end of their file and move on. After collection the orchestrator opens that list in one pass.
- **Read like a person.** One tab, pages one at a time, 20–60 s between pages of one site, a scroll or two before reading, at most about 15 pages of one site per run. Accounts get flagged for crawling; losing the user's subscription costs more than a missing source.
- **Never type a password or accept terms.** If a page wants a login, ask the user to log in themselves in that browser and wait.
- A page read in the browser is cited like any other: URL, date, verbatim quote.

Write the ladder you built into `_work/01_brief.md` (section "Tools") so collectors and verifiers get the same one.

## 1. Brief

A request like "look into X" has no finish line: nothing says when the research is done or what it is for. Research without a decision to serve has no bottom. The brief turns the request into a question with a checkable answer.

### Four axes of an adequate question

Before writing the brief, check the request on four axes:

1. **Decision.** What the person will do with the answer: pick a vendor, write a course module, go or no-go on a market, answer a regulator. Not "understand the market", but "shortlist three platforms for our case and say why".
2. **Boundaries.** Time window, geography, segment, and the angle (for engineers, for a board, for a buyer).
3. **Form.** What the answer looks like: a comparison table with named columns, a recommendation with its grounds, a list of options with trade-offs. The form sets the size of the job.
4. **Neutral wording.** The question does not ask to confirm an answer. "Prove that remote work beats the office" becomes "what the evidence says on remote versus office productivity, both sides, weighted by study quality". A model will confirm any loaded hypothesis it is handed; a loaded question is the first source of bad research.

An axis is empty when the request gives nothing for it and the context of the conversation does not either. Check the conversation before calling an axis empty: a person who has spent an hour on a course plan does not need to be asked what the research is for.

### Gate: ask before planning (deep and ultradeep)

The gate depends on the mode and on whether a person is present.

- **deep or ultradeep, a person is present, at least one axis is empty or the wording is loaded:** stop before the plan and send one message with up to three questions, the most important first. The decision question always comes first when that axis is empty; phrase it as "what will you do with the answer", with two or three concrete options the request suggests. For loaded wording, show the neutral version and ask which one to research. End the message with the defaults you will use if the person answers "go" or "doesn't matter", so a one-word reply is enough. Then wait.
- **deep or ultradeep, all four axes filled:** no questions, go to the plan.
- **quick or standard:** no gate. Fill empty axes with the most likely reading and write it down as an assumption. Ask only if the request is ambiguous in a way that changes the research (which market, which period), two questions at most.
- **Loaded wording, any mode:** research the neutral version. Without a gate, say in the method section that the question was reworded and how; the Answer section reports what the evidence shows on both sides, including where it does not support the hypothesis the person brought.
- **No person present** (a background or scripted run, or the person said "no questions"): no gate in any mode. Fill the axes as assumptions. In deep and ultradeep, an assumed decision is stated in the first line of the report's Answer section ("The decision this research serves is assumed: …"), not only in the method section, so a reader who stops at the top knows what the answer was aimed at.

**Stakes check.** The answer to the decision question also checks the mode. If it shows a low-stakes use ("just curious", "to get oriented") and the mode is deep or ultradeep, offer the lower mode in one line and use what the person picks. Do not downgrade silently.

The gate and the plan checkpoint (phase 2, step 6) are two separate stops by design: the gate settles why the research is done, the checkpoint settles how. The plan is built on the decision, so asking about the decision after the plan means rebuilding it. Planning makes no searches, so the two stops come a few minutes apart at the start of the run.

### The brief

Write `_work/01_brief.md` in the run folder and treat it as frozen:

- **Question**, in one sentence, neutrally worded, and **the decision it feeds**.
- **Reader**: who acts on the report and what they already know.
- **Boundaries**: in scope, out of scope, time window, geography.
- **Form of the answer**: what the Answer section and any comparison table must contain.
- **Evidence rules**: what counts as a primary source for this topic (the text of a law, a vendor's own documentation, the paper, the dataset), and that marketing pages are claims, not evidence.
- **Assumptions** you made instead of asking, and for each axis whether it came from the person or was assumed.
- **Tools**: the ladder from phase 0.

If later evidence forces a change to the brief, record the amendment and why in the report's method section; do not drift silently.

## 2. Plan

1. **Subquestions.** Break the question into 3–8 subquestions that together answer it. Tag each by difficulty:
   - *simple*: one checkable fact, one obvious primary source;
   - *moderate*: several facts, a comparison, one domain;
   - *hard*: contested, cross-domain, recent, non-English, or where sources are known to disagree.
2. **Perspectives.** Name 3–5 viewpoints that would ask different questions (practitioner, skeptic, regulator, buyer, researcher; whatever fits) and add the subquestions each would raise that are missing. A single decomposition inherits one viewpoint's blind spots.
3. **Answer hypotheses (only when the answer is a course of action or a choice).** Questions like "what should I do", "how can X be done", "which option for Y" have a failure of their own: the run collects sources for the first answers that came to mind and never sees the rest of the field. Before collecting, widen the field in your notes, one angle per pass (in a single pass the angles blur into one frame), 5–8 candidate answers each:
   - *the craft*: how practitioners of this exact role or task approach it, including the established frameworks of the field;
   - *the neighbour*: how an adjacent field or role solves the same kind of problem;
   - *the resource shift*: what the answer looks like with half the time or money, and with twice as much;
   - *the reversal*: what if the obvious approach is wrong, or the goal is the opposite; what from that still applies.

   Swap an angle when the topic needs another (for a message or positioning, "the audience is hostile" beats the resource shift). Then write the selection criteria from the brief's decision, before sorting, not after: criteria written after the list describe the option you already like. Keep 4–8 candidates; each becomes a subquestion ("does evidence support X, for whom, when"). The dropped ones go to the method section with one line of reason each.
4. **Organizations to sweep.** For every subquestion about what a specific organization says, measures, sells, charges or requires, list that organization's own properties: product docs, engineering blog, marketing blog, help center, changelog, press releases, a regulator's database of acts. For a regulator, list every kind of document it issues, not only the binding ones: laws and regulations, instructions, information and methodological letters, recommendations, explanations and FAQ, consultation papers. What a regulator "recommends" usually lives in a letter, not in an act. They will be searched directly (see "When to stop").
5. **Collectors.** Group subquestions into collectors that do not overlap. Each collector gets: the brief path, the subquestions it owns, what it must not cover (owned by another collector), the tool ladder, the output file path (`<run>/_work/03_collect_<ID>_<topic>.md`, see the layout in SKILL.md), and the output format below.
6. **Checkpoint (deep and ultradeep, only when a person is present).** One short message: the brief, the subquestions with tags, the collectors, rough cost (number of agents, expected time). One question: all at once or in waves. Then wait. In autonomous runs skip it and note that in the method section.

## 3. Collect

### Collector prompt

Every collector prompt contains:

- The objective: its subquestions, and the brief path to read first.
- The boundaries: what other collectors own.
- The tool ladder from the brief, in order.
- The output file, full path, and this instruction verbatim: **"Create the result file at the start and append as you go, after each verified finding; do not keep findings in memory until the end. A half-finished file is better than an empty one after a crash."**
- The finding format:

```
### F-<collector>.<n> One-line claim
- Source: title, URL, date, type (paper / official docs / law / dataset / repo / news / blog / marketing / forum)
- Quote: verbatim, 1–3 sentences, in the source language
- Status: measured (with the number) / stated by the source / opinion
- Relevance: one line on what it means for the brief
```

- A closing section "Not found" with what was searched and with which queries and tools.
- A section "Needs browser" with URLs that returned `antibot`, `blocked` or a paywall on every rung the collector may use.
- A short final answer: count of findings and the 3 strongest. The findings stay in the file; the orchestrator reads the file, not a pasted dump.

Collectors run on a cheaper model than the orchestrator when the work is searching and copying quotes; judgment-heavy synthesis and verification stay on a strong model.

### When to stop searching

Stop per subquestion, not per run.

**Effort floor (do not stop before it).** Agents without a sense of budget stop early and plateau. Before calling a subquestion answered:
- *simple*: at least 3 searches and the primary source opened;
- *moderate*: at least 8 tool calls and 3 sources opened, including the primary one;
- *hard*: at least 15 tool calls, sources from at least two independent owners, and one search in the other language (English for a Russian topic, Russian for a foreign one when the reader is Russian-speaking).

**Organization sweep.** If the subquestion is about what an organization says or does, search each of its properties from the plan directly (`site:` queries or the site's own search) before calling it answered, even when secondary sources look sufficient. The page that limits or reverses a claim is often on a different property than the page everyone quotes.

**Saturation, the normal stop.** The subquestion has an answer with a source, and the last batch produced fewer than two claims that are genuinely new rather than restatements.

**Stuck is not saturated.** Two batches in a row with no new relevant source means the search is stuck, not that the answer does not exist. Change the approach, not only the wording: use the domain's own terms (the act number, the standard's name, the product's official name) and the other language; switch tool class (search-engine results with operators, the organization's own site search, a crawl); go to the primary source directly instead of searching about it. If still nothing: write "not found by this search" with the queries and tools, and move on. Do not loop on the same ineffective action.

**Source counts and minutes are not stop criteria.** More sources and longer reports do not make a report better grounded.

### Reflection between batches

Before each new batch, write four lines in your working notes:
- answered: which subquestions have a sourced answer;
- open: which do not, and whether each is below its effort floor, stuck, or simply not searched yet;
- saturated: angles to stop spending on;
- next: the specific queries and tools, or "stop, move to cross-check".

## 4. Cross-check

**Independence.** Count corroboration by independent owners, not by pages. One press release reprinted by twelve outlets is one source. Two pages of the same organization are one source. A secondary article that only restates a primary one adds nothing to the count; cite the primary.

**Primary first.** A claim about a law rests on the text of the act; about a product, on the vendor's docs; about a study, on the paper. Where a primary source exists, a secondary one may point to it but does not replace it. Contested claims, or claims without a single primary source, need three independent sources.

**Contradictions are records, not averages.** When sources disagree, write a record in `_work/04_crosscheck_contradictions.md`: the two claims, their sources, the dimension of the disagreement (definition, period, population, measurement, causal claim, or a flat contradiction), a candidate explanation, and status (open, resolved, cannot be resolved). The report shows open ones; a claim involved in an open contradiction cannot have high confidence.

**Confidence per claim.** High: primary source, verbatim passage, no open contradiction. Medium: one good secondary source, or a primary source with a gap (a number read off a chart, a period not stated). Low: single weak source, opinion, or open contradiction. Low-confidence claims appear in the report as such, never as settled fact.
