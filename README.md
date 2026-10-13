# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> The three tools are implemented. The last command searches listings, suggests
> an outfit, and creates a fit card.
>
> **The Unit 3 build and Unit 4 test sections below are the submission.**

---

## What This Does

FitFindr takes a request for a thrift item, such as a vintage graphic tee under $30 in size M. It searches 40 mock listings, chooses the best match, suggests an outfit using the user's saved wardrobe, and writes a short fit-card caption. When there is no match, it stops and tells the user which search constraints to change.

---

## Tool Inventory

### `search_listings`

- **What it does:** Filters the local listings and ranks remaining items by overlap with the request.
- **Inputs:** `description` (`str`, required search words), `size` (`str | None`, optional case-insensitive clothing or exact numeric size), `max_price` (`float | None`, inclusive ceiling).
- **Returns:** `list[dict]`, at most `config.SEARCH_RESULT_LIMIT` listing records in score order. Each record has `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.
- **When it has nothing:** Returns `[]`, including when filters eliminate every match.

### `suggest_outfit`

- **What it does:** Uses the model to suggest one or two ways to style the selected listing.
- **Inputs:** `new_item` (`dict`, one complete listing record), `wardrobe` (`dict` with an `items: list[dict]` field; each item has a name, category, colors, and style tags).
- **Returns:** `str`, a non-empty outfit suggestion using named owned items when available.
- **When it has nothing:** If `wardrobe["items"]` is empty, returns general styling advice for the listing. If `new_item` is empty, returns a descriptive message rather than calling the model.

### `create_fit_card`

- **What it does:** Uses the model to write a short, post-ready caption for the selected listing and suggested outfit.
- **Inputs:** `outfit` (`str`, the prior tool's suggestion), `new_item` (`dict`, the same listing record selected after search).
- **Returns:** `str`, a two-to-four-sentence caption naming the item, its price, its platform, and a concrete outfit detail.
- **When it has nothing:** If `outfit` is empty or whitespace, returns an actionable message instead of calling the model.

---

## Planning Loop

**Branch rule:** If `search_listings` returns `[]`, save a message telling the user to broaden the description, change the size, or raise the price limit, then stop. Otherwise save the first result as `selected_item` and proceed to `suggest_outfit` and `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regular expressions extract a price ceiling and size phrase; the remaining words become the description. No model call is needed for parsing.

**What moves through the session:** `parsed` feeds `search_results`; the first result becomes `selected_item`; that item and `wardrobe` feed `outfit_suggestion`; the suggestion and same item feed `fit_card`. `tool_inputs` records the item ID passed into the outfit tool so the transfer can be checked.

---

## Sample Run

**One full query**

```text
$ .venv/bin/python app.py ask 'vintage graphic tee under $30'

  Found:    Graphic Tee — 2003 Tour Bootleg Style — $24.0 on depop

  Outfit:   Pair your new graphic tee with the baggy straight-leg jeans, black combat boots, and black crossbody bag for an effortless grunge look. Alternatively, layer the vintage black denim jacket over the tee and style it with the wide-leg khaki trousers and chunky white sneakers.

  Fit card: Found this insane 2003 tour bootleg style graphic tee on Depop for just $24. It looks so good with baggy straight-leg jeans. Totally obsessed with how worn-in it is!

1 model calls this session, 1 served from cache, 147 prompt + 44 output tokens
```

**The three tools, tested one at a time**

```text
$ .venv/bin/python -c "from tools import search_listings; print([(x['id'], x['title'], x['size'], x['price']) for x in search_listings('graphic tee', max_price=30)])"
[('lst_006', 'Graphic Tee — 2003 Tour Bootleg Style', 'L', 24.0), ('lst_002', 'Y2K Baby Tee — Butterfly Print', 'S/M', 18.0), ('lst_033', 'Vintage Band Tee — Faded Grey', 'L', 19.0), ('lst_015', 'Vintage Graphic Hoodie — Faded Black', 'L', 26.0)]
```

```text
$ .venv/bin/python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[5], get_example_wardrobe()))"
Pair your new graphic tee with the baggy straight-leg jeans, black combat boots, and black crossbody bag for an effortless grunge look. Alternatively, layer the vintage black denim jacket over the tee and style it with the wide-leg khaki trousers and chunky white sneakers.
```

```text
$ .venv/bin/python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('Baggy straight-leg jeans and black combat boots', load_listings()[5]))"
Found this sick 2003 tour bootleg style graphic tee on depop for just $24. It looks so good with my black combat boots. I love scoring pieces that look this worn-in and authentic.
```

**Empty-search branch**

```text
$ .venv/bin/python app.py ask 'designer ballgown size XXS under $5'
  No listings matched that request. Try a broader item description, another size, or a higher price limit.
0 model calls this session
```

For the state check, I replaced the outfit tool temporarily with a spy and ran the matching query. `selected_item.id`, the saved `tool_inputs.suggest_outfit.new_item_id`, and the ID actually received by the spy were all `lst_006`. Repeating the impossible query with a spy that would raise if called returned `fit_card: None`; the outfit tool was never reached.

With caching disabled, three calls to `create_fit_card` for the same listing produced different wording. Each mentioned the graphic tee, $24, and Depop. The normal sample above used one cached outfit answer while the fit card was a fresh model call.

I also checked the tool empty cases directly: `search_listings('designer ballgown', size='XXS', max_price=5)` returned `[]`; `suggest_outfit({}, get_empty_wardrobe())` returned `Choose a listing before asking for outfit ideas.`; and `create_fit_card(' ', load_listings()[5])` returned `Add an outfit suggestion before creating a fit card.` A separate empty-wardrobe call with a real listing returned general styling ideas without claiming the user owned specific pieces.

---

## How I Used AI

**Moment 1**

- *What I asked for:* I asked Codex to inspect the listing data and build the three specified tools.
- *What came back:* It found clothing sizes such as `S/M`, numeric shoe sizes such as `US 8`, and waist sizes such as `W30 L30`. A plain substring size check would have confused these formats.
- *What I changed:* The search uses size tokens for clothing and exact matches for numeric shoe sizes. I checked that a request for size S finds the `S/M` tee without returning a shoe or XL top.

**Moment 2**

- *What I asked for:* I asked Codex to run both the matching and impossible queries and inspect the session transfer.
- *What came back:* The first parser check left `size XXS` inside the description instead of recording it as a size. The impossible search still stopped, but the parsed state was wrong.
- *What I changed:* I added `XXS` to the size parser and reran the check. The session now records `size: XXS`, returns no listings, and stops before the outfit tool. A spy also confirmed the selected `lst_006` reached `suggest_outfit` on the matching path.

**Unit 4:** I asked Codex to register the search tool through MCP and compare its returned value with the direct call; both returned a Python list of listing dictionaries, including `[]` for no match. I also asked it to trigger the three required failures and inspect the messages. It used an invalid key only for one process, saw the model error handled in the outfit stage, and added trace steps that show the MCP call and early stop.

---

## Run Log — Before

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Empty search stops before tool 2 | 5/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Selected item reaches outfit tool unchanged | 5/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card includes item, price, platform in 2–4 sentences | 4/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Every search result stays within price ceiling | 5/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Raw evidence: [results/run_2026-10-13_1816_before.md](results/run_2026-10-13_1816_before.md), produced by `run_eval.py::main` with caching off. It contains all 25 tries, full model text, session fields, and traces. The excerpts below are actual output from try 1 of each scenario (criterion 4 also quotes try 2).

**1. Full run:** `agent.py::run_agent` called the MCP tool, `tools.py::suggest_outfit`, and `tools.py::create_fit_card` in that order. `run_eval.py::write_report` recorded the resulting card:

```text
- selected_item_id: lst_006
Just scored this 2003 tour bootleg graphic tee on Depop for $24! It looks so good paired with baggy straight-leg jeans for an effortless grunge vibe. Can’t wait to wear it all the time.
```

**2. Empty search:** `agent.py::run_agent` stopped after `mcp_server.py::search_listings` returned `[]`; its trace contains no outfit call:

```text
[1] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
[2] stop
      out: No listings matched that request. Try a broader item description, another size, or a higher price limit.
      →    search returned an empty list
```

**3. State transfer:** `agent.py::run_agent` recorded the selected ID and the ID passed to `tools.py::suggest_outfit`:

```text
- selected_item_id: lst_004
- outfit_tool_item_id: lst_004
[2] suggest_outfit
      in:  new_item=lst_004 90s Track Jacket — Navy/White Stripe; wardrobe_items=10
```

**4. Fit card facts:** `tools.py::create_fit_card` returned this two-sentence card for the selected `90s Silk Slip Dress — Floral, Midi Length`, price $30 on Depop (try 2):

```text
Still can't believe I scored this 90s silk slip dress on Depop for just $30! Throwing my oversized grey crewneck sweatshirt right over it for the easiest outfit ever.
```

**5. Price ceiling:** `agent.py::_parse_query` found 50.0; `mcp_server.py::search_listings` returned six listings, all at or below it, as recorded by `run_eval.py::write_report`:

```text
- parsed: {'description': 'denim jacket', 'size': None, 'max_price': 50.0}
- search_result_prices: [42.0, 24.0, 27.0, 45.0, 30.0, 38.0]
```

---

## Verdicts and Diagnoses

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | Full three-tool run | 4/5 | MET | All five matching tries completed the MCP search, outfit suggestion, and fit card. |
| 2 | Empty search stops before outfit tool | 5/5 | MET | All five impossible tries returned the actionable stop message, with no outfit call in the trace. |
| 3 | Selected item ID equals outfit input ID | 5/5 | MET | All five tries recorded `lst_004` in both session fields and in the outfit call trace. |
| 4 | Card has item/type, numeric price, platform, and 2–4 sentences | 4/5 | MET | All five cards named a silk slip dress, $30, and Depop; one had two sentences and four had three. |
| 5 | All search results at or below parsed ceiling | 5/5 | MET | Every result in each of the five tries cost at most $50; the six prices were the same each time. |

**Diagnoses**

No criterion missed. These five scenarios are direct and the first result is stable, so the targets may be safe. I would tighten criterion 1 in the next unit to require five of five *different phrasings* of a matching request, instead of repeating one direct query.

The baseline still exposes a retrieval-tool weakness outside the five pass/fail targets. Across the four matching scenarios, `search_listings` returned 21 listings; 14 matched only one distinct request word in their title, category, tags, or colors. For example, `denim jacket` returned denim shorts and a denim vest, and `90s track jacket` returned a leather bomber and slip dress because each shared just one word. The mechanism is the search tool's current rule that accepts any single matching word. This adds weak candidates to the session even though the top listing remains correct. I will tighten that one search rule and measure whether it removes the weak candidates without losing the selected listings.

---

## Loop Trace

**Happy path**

```text
$ .venv/bin/python app.py ask 'vintage graphic tee under $30' --trace
[1] search_listings (via MCP)
      in:  description='vintage graphic tee', size=None, max_price=30.0
      out: 10 items: Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey, Vintage Graphic Hoodie — Faded Black … +7 more
[2] suggest_outfit
      in:  new_item=lst_006 Graphic Tee — 2003 Tour Bootleg Style; wardrobe_items=10
      out: Pair your new graphic tee with the baggy straight-leg jeans, black combat boots, and black crossbody bag for a…
[3] create_fit_card
      in:  new_item=lst_006 Graphic Tee — 2003 Tour Bootleg Style; outfit=Pair your new graphic tee with the baggy straig…
      out: Found this insane 2003 tour bootleg style graphic tee on Depop for just $24. It looks so good with baggy strai…
```

**Empty search**

```text
$ .venv/bin/python app.py ask 'designer ballgown size XXS under $5' --trace
[1] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
[2] stop
      out: No listings matched that request. Try a broader item description, another size, or a higher price limit.
      →    search returned an empty list
```

**On the MCP move:** `mcp_server.py::search_listings` exposes the existing search with a description and typed inputs. `agent.py::run_agent` now calls it through `mcp_client.call_tool` and still receives `list[dict]` for matches or `[]` for no match. `python mcp_client.py` listed only `search_listings`; an end-to-end query selected the same `lst_006` listing as the direct call. The server startup adds overhead but did not change the search result shape.

**Deliberate failures:** The impossible query stopped after the MCP search and suggested broadening the description, changing size, or raising the price ceiling. The empty wardrobe query, `90s track jacket in size M --empty-wardrobe`, returned general styling advice and a fit card. With `AI201_CACHE=0` and a temporary invalid `GEMINI_API_KEY` environment value, the agent stopped at `suggest_outfit` with: `The outfit model could not be reached. Check your API key or internet connection and try again.` The `.env` file was not edited.

```text
$ .venv/bin/python app.py ask '90s track jacket in size M' --empty-wardrobe
  Outfit:   Here are two easy ways to style a 90s navy and white track jacket:

*   **Retro Streetwear:** Layer it over a graphic tee or hoodie, paired with relaxed-fit light wash denim and chunky sneakers.
*   **Athleisure Casual:** Keep it sporty by pairing it with matching navy sweatpants or joggers, a simple white crewneck tee, and minimalist trainers.
```

```text
$ GEMINI_API_KEY=invalid-key AI201_CACHE=0 .venv/bin/python app.py ask 'corduroy wide-leg pants under $40' --trace
[2] suggest_outfit
      in:  new_item=lst_005 Corduroy Wide-Leg Pants — Rust; wardrobe_items=10
      out: The outfit model could not be reached. Check your API key or internet connection and try again.
```

---

## The Improvement

**What I changed:** In `tools.py::search_listings`, a multiword description now requires at least two distinct matches across a listing's title, category, style tags, and colors. One-word descriptions still need one match. This was the only search-behavior change after the baseline; the corpus, model, query parsing, prompts, and five scenarios stayed the same.

**Which failure it was meant to fix:** None of the five original criteria missed, but the retrieval-tool diagnosis above found 14 weak candidates among 21 returned listings across the four matching scenarios. A one-word match such as `denim` admitted shorts and vests for a jacket request. Requiring two matching words was meant to remove those weak candidates without losing the intended top listings.

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Empty search stops before tool 2 | 5/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Selected item reaches outfit tool unchanged | 5/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card includes item, price, platform in 2–4 sentences | 4/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Every search result stays within price ceiling | 5/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Raw evidence: [results/run_2026-10-13_1819_after.md](results/run_2026-10-13_1819_after.md), again produced by `run_eval.py::main` with caching off. Actual excerpts from try 1 of each scenario:

**1. Full run:** `agent.py::run_agent` completed the three calls. `run_eval.py::write_report` recorded:

```text
- selected_item_id: lst_006
Score this 2003 tour bootleg style graphic tee on Depop for just $24! I'm totally planning to wear it with baggy straight-leg jeans for that effortless grunge look. Such a sick thrift find.
```

**2. Empty search:** `agent.py::run_agent` stopped before the outfit tool:

```text
[1] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
[2] stop
      out: No listings matched that request. Try a broader item description, another size, or a higher price limit.
      →    search returned an empty list
```

**3. State transfer:** `agent.py::run_agent` recorded the same ID selected and passed to `tools.py::suggest_outfit`:

```text
- selected_item_id: lst_004
- outfit_tool_item_id: lst_004
[2] suggest_outfit
      in:  new_item=lst_004 90s Track Jacket — Navy/White Stripe; wardrobe_items=10
```

**4. Fit card facts:** `tools.py::create_fit_card` returned three sentences identifying the silk slip dress, $30, and Depop:

```text
Scored this gorgeous 90s floral silk slip dress on depop for just $30! I love how it looks layered under an oversized grey crewneck sweatshirt. Such an easy piece to dress up or down.
```

**5. Price ceiling:** `agent.py::_parse_query` still found $50 and `mcp_server.py::search_listings` returned only the $42 jacket:

```text
- parsed: {'description': 'denim jacket', 'size': None, 'max_price': 50.0}
- search_result_prices: [42.0]
```

**Did it help, and how do I know:** Yes, for search focus on these four matching scenarios. The total results fell from 21 to 7, while the same four intended listings remained first. Before the change, 14 of 21 results matched only one distinct request word in the primary fields; after, none of the 7 did. The five acceptance-criterion scores did not change: every row stayed at 5/5. This result does not show that stricter matching helps with paraphrased requests, which these scenarios do not test.

---

## What's Still Broken

No acceptance criterion remained missed after the improvement. The stricter search may now reject a relevant listing when the user's words are synonyms for the listing text or only one requested word appears in its main fields. I would next add varied phrasings and inspect false negatives before deciding whether to add synonyms or a different ranking approach. I stopped after one search change so the before-and-after run isolates its effect, as this unit requires.

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
