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
> **The Unit 3 sections below are the submission.** Unit 4 sections remain as
> the starter template for the next assignment.

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

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
