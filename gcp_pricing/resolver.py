"""Resolve a product name or URL to pricing URL(s).

Never raises for unknowns — it proposes pattern-guessed URLs; the CLI validates them by
fetching and only then reports failure. Discovery of exotic products is the calling
agent's job (it has web search); the CLI stays dependency-free."""
from .registry import PRODUCTS, ALIASES, BASE


def resolve(token):
    t = token.strip()
    if "://" in t:      # any URL scheme (https, http, file) passes straight through
        return {"product": t, "urls": [t], "resolved_by": "passthrough", "note": None}
    key = ALIASES.get(t.lower(), t.lower())
    if key in PRODUCTS:
        return {"product": key, "urls": PRODUCTS[key], "resolved_by": "registry", "note": None}
    cands = [f"{BASE}/{key}/pricing?hl=en", f"{BASE}/products/{key}/pricing?hl=en"]
    return {"product": key, "urls": cands, "resolved_by": "pattern",
            "note": "guessed URL by pattern; if wrong, pass the exact pricing URL"}
