"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    def size_matches(listing_size: str, requested: str) -> bool:
        want = requested.strip().upper()
        have = listing_size.upper()
        if want in {"XXS", "XS", "S", "M", "L", "XL", "XXL"}:
            # Match the slash sizes (S/M, M/L, L/XL), but not L inside XL.
            return want in re.findall(r"(?<![A-Z])[A-Z]{1,3}(?![A-Z0-9])", have)
        if want in {"ONE SIZE", "OS"}:
            return have.startswith("ONE SIZE")
        if want.startswith("US ") or want.replace(".", "", 1).isdigit():
            number = want.removeprefix("US ").strip()
            return have == f"US {number}"
        return want == have or have.startswith(f"{want} ")

    stop_words = {"a", "an", "and", "for", "in", "of", "the", "to", "with"}
    words = set(re.findall(r"[a-z0-9]+", description.lower())) - stop_words
    if not words:
        return []

    ranked = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size is not None and not size_matches(str(listing["size"]), size):
            continue
        title = set(re.findall(r"[a-z0-9]+", listing["title"].lower()))
        tags = set(re.findall(r"[a-z0-9]+", " ".join(listing["style_tags"]).lower()))
        category = set(re.findall(r"[a-z0-9]+", listing["category"].lower()))
        colors = set(re.findall(r"[a-z0-9]+", " ".join(listing["colors"]).lower()))
        details = set(re.findall(r"[a-z0-9]+", listing["description"].lower()))
        if not words & (title | tags | category | colors):
            continue
        score = (4 * len(words & title) + 3 * len(words & tags)
                 + 2 * len(words & category) + 2 * len(words & colors)
                 + len(words & details))
        if score:
            ranked.append((score, listing))

    ranked.sort(key=lambda entry: (-entry[0], entry[1]["price"], entry[1]["id"]))
    return [listing for _, listing in ranked[:config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    if not new_item:
        return "Choose a listing before asking for outfit ideas."

    item_details = (
        f"{new_item['title']} (size {new_item['size']}, colors: "
        f"{', '.join(new_item['colors'])}, styles: "
        f"{', '.join(new_item['style_tags'])})"
    )
    owned = wardrobe.get("items", [])
    if owned:
        closet = "\n".join(
            f"- {piece['name']} ({piece['category']}; "
            f"colors: {', '.join(piece['colors'])}; "
            f"styles: {', '.join(piece['style_tags'])})"
            for piece in owned
        )
        prompt = (
            f"New thrift find: {item_details}\nOwned wardrobe:\n{closet}\n\n"
            "Suggest one or two wearable outfits using the new find and "
            "specific pieces from the owned wardrobe. Name those pieces "
            "exactly. Keep it to two short sentences and do not invent owned items."
        )
    else:
        prompt = (
            f"New thrift find: {item_details}\nThe user has no saved wardrobe. "
            "Give one or two short, general styling ideas. Do not claim the "
            "user owns any particular piece."
        )
    return generate(prompt).strip() or f"Try pairing {new_item['title']} with simple basics and complementary colors."


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit.strip():
        return "Add an outfit suggestion before creating a fit card."
    if not new_item:
        return "Choose a listing before creating a fit card."

    prompt = (
        f"Thrift find: {new_item['title']}\n"
        f"Price: ${new_item['price']:g}\nPlatform: {new_item['platform']}\n"
        f"Outfit idea: {outfit}\n\n"
        "Write a natural social-media caption of two to four short sentences. "
        "Mention the exact item or its clear type, its numeric dollar price, "
        "and its platform once each. Include one concrete outfit detail from "
        "the idea. Sound like a person sharing a find, not a product listing. "
        "Return only the caption."
    )
    return generate(prompt).strip() or (
        f"Found {new_item['title']} for ${new_item['price']:g} on "
        f"{new_item['platform']}. {outfit.strip()}"
    )
