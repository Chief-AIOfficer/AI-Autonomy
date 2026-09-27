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
| Crawl a whole site or documentation | – | Apify `website-content-crawler`, Firecrawl `crawl`, Tavily `tavily_crawl` |
| Reddit | none (built-ins are blocked by Reddit) | Bright Data `web_data_reddit_posts`, Apify `reddit-scraper-lite` |
| LinkedIn, company databases | – | Bright Data `web_data_linkedin_*`, `web_data_crunchbase_company` |
| Telegram channels | – | Apify `telegram-scraper` (recent posts only; for a full history ask the user to export the channel) |
| Academic papers | `WebSearch` with `allowed_domains: ["arxiv.org"]` | arXiv, Semantic Scholar servers |

**Order of preference within a class: free and built-in first, then prepaid services, then metered ones.** If the user's own instructions rank the services (for cost or other reasons), their ranking wins. Metered search APIs are used with their cheapest depth setting unless a cheaper call already failed. Do not call an autonomous "research" endpoint of a service (for example `tavily_research`) unless the user asks: it is a paid research run inside the research run.

**Subagents use the same ladder.** `WebSearch` works inside subagents when it is allowed in the user's settings; do not steer subagents to a paid tool by default. If a tool is denied inside a subagent, the subagent says so in its file and uses the next tool in the class.

**One stubborn page:** summarizing fetch, then raw text, then unlocker. An empty or negative answer from the summarizing fetch is where you start climbing, not where you stop.

Write the ladder you built into `00_brief.md` (section "Tools") so collectors and verifiers get the same one.

## 1. Brief

Write `00_brief.md` in the run folder and treat it as frozen:

- **Question**, in one sentence, and **the decision it feeds**. If the decision is unclear, name the most likely one as an assumption.
- **Reader**: who acts on the report and what they already know.
- **Boundaries**: in scope, out of scope, time window, geography.
- **Evidence rules**: what counts as a primary source for this topic (the text of a law, a vendor's own documentation, the paper, the dataset), and that marketing pages are claims, not evidence.
- **Assumptions** you made instead of asking.
- **Tools**: the ladder from phase 0.

Ask clarifying questions only when a person is present and the question is genuinely ambiguous in a way that changes the research (which market, which period, which decision). Two or three questions at most, in one message. Otherwise decide, and write the assumption down. If later evidence forces a change to the brief, record the amendment and why in the report's method section; do not drift silently.

## 2. Plan

1. **Subquestions.** Break the question into 3–8 subquestions that together answer it. Tag each by difficulty:
   - *simple*: one checkable fact, one obvious primary source;
   - *moderate*: several facts, a comparison, one domain;
   - *hard*: contested, cross-domain, recent, non-English, or where sources are known to disagree.
2. **Perspectives.** Name 3–5 viewpoints that would ask different questions (practitioner, skeptic, regulator, buyer, researcher; whatever fits) and add the subquestions each would raise that are missing. A single decomposition inherits one viewpoint's blind spots.
3. **Organizations to sweep.** For every subquestion about what a specific organization says, measures, sells, charges or requires, list that organization's own properties: product docs, engineering blog, marketing blog, help center, changelog, press releases, a regulator's database of acts. For a regulator, list every kind of document it issues, not only the binding ones: laws and regulations, instructions, information and methodological letters, recommendations, explanations and FAQ, consultation papers. What a regulator "recommends" usually lives in a letter, not in an act. They will be searched directly (see "When to stop").
4. **Collectors.** Group subquestions into collectors that do not overlap. Each collector gets: the brief path, the subquestions it owns, what it must not cover (owned by another collector), the tool ladder, the output file path, and the output format below.
5. **Checkpoint (deep and ultradeep, only when a person is present).** One short message: the brief, the subquestions with tags, the collectors, rough cost (number of agents, expected time). One question: all at once or in waves. Then wait. In autonomous runs skip it and note that in the method section.

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

**Contradictions are records, not averages.** When sources disagree, write a record in `contradictions.md`: the two claims, their sources, the dimension of the disagreement (definition, period, population, measurement, causal claim, or a flat contradiction), a candidate explanation, and status (open, resolved, cannot be resolved). The report shows open ones; a claim involved in an open contradiction cannot have high confidence.

**Confidence per claim.** High: primary source, verbatim passage, no open contradiction. Medium: one good secondary source, or a primary source with a gap (a number read off a chart, a period not stated). Low: single weak source, opinion, or open contradiction. Low-confidence claims appear in the report as such, never as settled fact.
