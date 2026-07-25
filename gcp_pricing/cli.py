"""CLI: bring the whole page down, write it to a file, print what was asked for.

No chunking, no record splitting, no "which table is the real one". Every run writes the
complete capture to disk and tells you where. Filters only decide what gets echoed to
stdout - they never decide what is captured.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

from .resolver import resolve
from .fetch import fetch, FetchError
from .extract import extract
from .catalog import catalog_skus, CatalogError

CAPTURE_DIR = os.environ.get("GCP_PRICING_CAPTURE_DIR") or os.path.join(
    tempfile.gettempdir(), "gcp-pricing")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _hit(text, terms):
    low = text.lower()
    return all(t in low for t in terms)


def _capture_path(url):
    slug = url.split("//", 1)[-1].replace("/", "_").replace("?", "_")[:80]
    h = hashlib.sha1(url.encode()).hexdigest()[:8]
    os.makedirs(CAPTURE_DIR, exist_ok=True)
    return os.path.join(CAPTURE_DIR, f"{slug}.{h}.txt")


def _render(ex):
    """The whole capture as one text file: page prose+tables, then every blob row."""
    out = [f"# SOURCE: {ex['source_url']}",
           f"# CAPTURED: {_now()}",
           f"# COVERAGE: {json.dumps(ex['coverage'])}",
           "",
           "=" * 70,
           "PAGE (all headings, prose, lists and tables, in document order)",
           "=" * 70,
           "",
           ex["text"]]
    if ex["regions"]:
        out += ["",
                "=" * 70,
                f"REGION ROWS ({len(ex['regions'])}) — from the page's inline JSON, "
                "one row per line, tab-separated. This is the only source of non-default "
                "regions. Nothing removed, near-duplicates included.",
                "=" * 70,
                ""]
        for r in ex["regions"]:
            out.append(r["region"] + "\t" + "\t".join(r["cells"]))
    return "\n".join(out)


def _echo(body, terms, limit):
    """Print lines/blocks that match. Tables keep their header."""
    if not terms:
        head = body.split("\n")[:limit]
        print("\n".join(head))
        return len(head)
    shown = 0
    for block in body.split("\n\n"):
        if block.startswith("|"):
            lines = block.split("\n")
            keep = [l for l in lines[2:] if _hit(l, terms)]
            if keep:
                print("\n".join(lines[:2] + keep) + "\n")
                shown += len(keep)
        elif "\t" in block:
            for line in block.split("\n"):
                if _hit(line, terms):
                    print(line)
                    shown += 1
        elif _hit(block, terms):
            print(block + "\n")
            shown += 1
        if shown >= limit:
            print(f"... (truncated at {limit}; full capture in the file below)")
            break
    return shown


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="gcp-pricing",
        description="Capture a Google Cloud pricing page whole. No auth, no interpretation.")
    ap.add_argument("target", nargs="?",
                    help="product name (vms, gpu, tpu, storage, managed-spark, ...) or any URL")
    ap.add_argument("--filter", action="append", default=[],
                    help="substring filter, repeatable (AND). Filters stdout only; the file always has everything.")
    ap.add_argument("--catalog", action="store_true",
                    help="query the Cloud Billing Catalog API instead (carries SKUs pages omit)")
    ap.add_argument("--json", action="store_true", help="raw structured output on stdout")
    ap.add_argument("--limit", type=int, default=200, help="max lines echoed to stdout (default 200)")
    ap.add_argument("--version", action="store_true",
                    help="installed version and path, so staleness is visible")
    a = ap.parse_args(argv)

    if a.version:
        try:
            from importlib.metadata import version
            v = version("gcp-pricing-scraper")
        except Exception:
            v = "unknown (running from source)"
        print(f"gcp-pricing {v}\n  module: {os.path.dirname(os.path.abspath(__file__))}\n"
              f"  upgrade: curl -fsSL https://raw.githubusercontent.com/WandLZhang/"
              f"gcp-pricing-scraper/main/install.sh | bash")
        return 0

    if not a.target:
        ap.error("a product name or URL is required")

    terms = [f.lower() for f in a.filter]

    if a.catalog:
        try:
            skus = catalog_skus(a.target, terms)
        except CatalogError as e:
            print(str(e), file=sys.stderr)
            return 5
        if a.json:
            print(json.dumps({"fetched_at": _now(), "skus": skus}, indent=2))
        elif skus:
            w = max(len(f"{s['price']:.9f}") for s in skus)
            for s in skus:
                print(f"${s['price']:<{w}.9f}  {s['unit']:<16s}  {s['description']}")
            print(f"\n{len(skus)} SKUs · Cloud Billing Catalog API")
        else:
            print(f"no SKUs matched {a.filter!r}", file=sys.stderr)
        return 0

    r = resolve(a.target)
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
            print(f"could not resolve '{a.target}'. Pass the exact URL.", file=sys.stderr)
            return 3
        urls = good[:1]

    rc = 0
    for u in urls:
        try:
            html = fetch(u)
        except FetchError as e:
            print(str(e), file=sys.stderr)
            rc = 4
            continue
        ex = extract(html, u)

        if a.json:
            print(json.dumps({"fetched_at": _now(), **ex}, indent=2))
            continue

        blob = _render(ex)
        path = _capture_path(u)
        with open(path, "w", encoding="utf-8") as f:
            f.write(blob)

        shown = _echo(blob, terms, a.limit)
        c = ex["coverage"]
        print(f"\n{c['tables']} tables ({c['tables_priced']} priced) · "
              f"{c['region_rows']} region rows · {len(blob) // 1000} KB captured · "
              f"{shown} shown")
        print(f"FULL CAPTURE: {path}")
        print(f"SOURCE: {u}\n")
        if terms and not shown:
            print(f"nothing matched {a.filter!r} — the page was still captured in full. "
                  f"grep the file above before concluding it is not offered.", file=sys.stderr)
    return rc
