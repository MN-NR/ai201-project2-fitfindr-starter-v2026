# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
The search uses local keyword overlap rather than understanding every synonym, so one reasonable phrasing may find no listing. Four of five still requires the agent to complete the full path on most queries the dataset can satisfy.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
An empty Python list is deterministic and the loop can inspect it before any model call. Every impossible query should therefore stop safely and tell the user how to broaden the search.

---

## 3. The selected listing reaches the outfit tool unchanged

For five matching queries, `session["selected_item"]["id"]` equals the `new_item["id"]` actually passed to `suggest_outfit` in 5 of 5 tries.

**Why this target:**
The listing ID is stable and unique in the data, so there is no ambiguity about whether the tool received the selected item. State transfer is local code, so all five transfers should agree.

---

## 4. Fit cards include the facts a shopper needs

For five matching queries, at least 4 of 5 fit cards are two to four sentences and mention the selected item's title or clear item type, its numeric price, and its platform.

**Why this target:**
The caption's wording can vary, but it should still tell a reader what the find is, what it costs, and where to find it. I allowed one miss because generation can vary even with a specific prompt.

---

## 5. Search respects the price ceiling

For five queries with a stated maximum price, every item in `session["search_results"]` has `price <= session["parsed"]["max_price"]`, in 5 of 5 tries.

**Why this target:**
Price is a numeric field in every listing, so this filter should be exact. A single above-budget result would make the agent disregard an explicit shopper constraint.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
