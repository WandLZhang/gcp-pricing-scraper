import argparse
import json
import sys

from .resolver import resolve
from .fetch import fetch, FetchError
from .extract import extract
from .label import load_schema, label


def _collect(urls, product, schema, want_regions, filt, debug):
    rows, errors = [], []
    for u in urls:
        try:
            html = fetch(u)
        except FetchError as e:
            errors.append(str(e))
            continue
        ex = extract(html, u)
        if debug:
            print(f"# {u}: kind={ex['kind']} records={len(ex['records'])} cols={ex.get('columns')}",
                  file=sys.stderr)
        rows += label(ex, product, schema)
    if want_regions is not None:
        rows = [r for r in rows if r["region_code"] in want_regions]
    if filt:
        f = filt.lower()
        rows = [r for r in rows if f in (r["item"] or "").lower() or f in (r["price_type"] or "").lower()]
    return rows, errors


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="gcp-pricing",
        description="Live Google Cloud pricing by scraping official pricing pages (no auth).")
    ap.add_argument("target", help="product name (tpu, accelerator, bigquery, ...) or a pricing URL")
    ap.add_argument("--product", help="schema/product label to use when target is a raw URL")
    ap.add_argument("--region", action="append", default=[], help="region code filter (repeatable)")
    ap.add_argument("--all-regions", action="store_true", help="show every region")
    ap.add_argument("--filter", help="substring filter on item or price_type")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--json", action="store_true", help="emit JSON rows")
    g.add_argument("--raw", action="store_true", help="emit JSON rows incl. raw/unlabeled columns")
    ap.add_argument("--verify", action="store_true",
                    help="cross-check vs Billing Catalog API (needs a gcloud token)")
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args(argv)

    r = resolve(a.target)
    product = a.product or r["product"]
    urls = r["urls"]
    if r["resolved_by"] == "pattern":
        good = []
        for u in urls:
            try:
                fetch(u)
                good.append(u)
            except FetchError:
                pass
        if not good:
            print(f"could not resolve '{a.target}'. Pass the exact cloud.google.com pricing URL.",
                  file=sys.stderr)
            return 3
        urls = good[:1]

    want = None if a.all_regions else (set(a.region) if a.region else {"us-central1"})
    rows, errors = _collect(urls, product, load_schema(), want, a.filter, a.debug)
    if not rows:
        if errors:
            print("; ".join(errors), file=sys.stderr)
            return 4
        print("no matching rows (try --all-regions or --filter)", file=sys.stderr)
        return 0

    if a.verify:
        from .verify import verify
        rows = rows + verify(rows)

    if a.json or a.raw:
        print(json.dumps(rows, indent=2))
    else:
        _print_table(rows)
    return 0


def _print_table(rows):
    if not rows:
        print("no rows")
        return
    hdr = ["item", "region_code", "price_type", "price", "unit"]
    widths = {h: max(len(h), max(len(str(r.get(h, ""))) for r in rows)) for h in hdr}
    print("  ".join(h.ljust(widths[h]) for h in hdr))
    for r in rows:
        print("  ".join(str(r.get(h, "")).ljust(widths[h]) for h in hdr))
    # Source footer so the agent can point the user to the page to eye-check numbers.
    srcs = sorted({r["source_url"] for r in rows if r.get("source_url")})
    ts = next((r["fetched_at"] for r in rows if r.get("fetched_at")), "")
    if srcs:
        print("\nSource (open to verify): " + " ; ".join(srcs) + (f"  [fetched {ts}]" if ts else ""))
