"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

The loop reads each completed step from the session before choosing the next.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "tool_inputs": {},           # IDs sent to model-backed tools
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """Extract explicit constraints and leave searchable item words."""
    price_match = re.search(
        r"\b(?:under|below|up to|max(?:imum)?|less than)\s*\$?\s*(\d+(?:\.\d{1,2})?)\b",
        query, re.IGNORECASE,
    )
    size_match = re.search(
        r"\b(?:in\s+)?size\s+(one size|xxl|xxs|xl|xs|s|m|l|us\s*\d+(?:\.5)?|w\d+|\d+(?:\.5)?)\b",
        query, re.IGNORECASE,
    )
    description = query
    for match in sorted((m for m in (price_match, size_match) if m),
                        key=lambda found: found.start(), reverse=True):
        description = description[:match.start()] + description[match.end():]
    description = re.sub(r"\b(?:looking for|find me|i want|i need)\b", "", description,
                         flags=re.IGNORECASE)
    description = re.sub(r"\s+", " ", description.strip(" ,.-"))
    return {
        "description": description.strip(" ,.-"),
        "size": size_match.group(1).upper() if size_match else None,
        "max_price": float(price_match.group(1)) if price_match else None,
    }


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    The search stage branches on an empty result list. The selected item,
    outfit suggestion, and fit card are stored in the session. Unit 4 adds
    step tracing and a user-facing ModelUnavailable handler.
    """
    session = new_session(query, wardrobe)

    stage = "search"
    iterations = 0
    while stage != "done":
        iterations += 1
        trace.check_iterations(iterations)

        if stage == "search":
            session["parsed"] = _parse_query(session["query"])
            parsed = session["parsed"]
            session["search_results"] = search_listings(
                parsed["description"], parsed["size"], parsed["max_price"]
            )
            if not session["search_results"]:
                session["error"] = (
                    "No listings matched that request. Try a broader item "
                    "description, another size, or a higher price limit."
                )
                return session
            session["selected_item"] = session["search_results"][0]
            stage = "outfit"
        elif stage == "outfit":
            item = session["selected_item"]
            session["tool_inputs"]["suggest_outfit"] = {"new_item_id": item["id"]}
            session["outfit_suggestion"] = suggest_outfit(
                item, session["wardrobe"]
            )
            stage = "card"
        elif stage == "card":
            item = session["selected_item"]
            session["tool_inputs"]["create_fit_card"] = {"new_item_id": item["id"]}
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"], item
            )
            stage = "done"
    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
