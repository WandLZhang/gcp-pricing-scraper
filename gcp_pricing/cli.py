import argparse
import json
import sys
from datetime import datetime, timezone

from .resolver import resolve
from .fetch import fetch, FetchError
from .extract import extract


def _now():
    return datetime.now(timezone.utc).isoformat()


def _match(row, terms):
    hay = " ".join(row).lower()
    return all(t in hay for t in terms)


def _collect(urls, filters, debug):
    sheets, errors = [], []
    for u in urls:
        try:
            html = fetch(u)
        except FetchError as e:
            errors.append(str(e))
            continue
        ex = extract(html, u)
        if debug:
            print(f"# {u}: {len(ex['sheets'])} sheet(s)", file=sys.stderr)
        for sh in ex["sheets"]:
            rows = [r for r in sh["rows"] if _match(r, filters)] if filters else sh["rows"]
            if rows:
                sheets.append({"headers": sh["headers"], "rows": rows, "source_url": u})
    return sheets, errors


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="gcp-pricing",
        description="Raw Google Cloud pricing scraped from official pages (no auth, no interpretation).")
    ap.add_argument("target", help="product name (tpu, accelerator, gpu, bigquery, ...) or a pricing URL")
    ap.add_argument("--filter", action="append", default=[],
                    help="substring row filter, repeatable (AND). e.g. --filter h200 --filter netherlands")
    ap.add_argument("--json", action="store_true", help="emit raw JSON sheets")
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args(argv)

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
            print(f"could not resolve '{a.target}'. Pass the exact cloud.google.com pricing URL.",
                  file=sys.stderr)
            return 3
        urls = good[:1]

    filters = [f.lower() for f in a.filter]
    sheets, errors = _collect(urls, filters, a.debug)
    if not sheets:
        if errors:
            print("; ".join(errors), file=sys.stderr)
            return 4
        print("no rows matched " + (repr(a.filter) if a.filter else "(no price tables on page)"),
              file=sys.stderr)
        return 0

    if a.json:
        print(json.dumps({"fetched_at": _now(), "sheets": sheets}, indent=2))
    else:
        _print_sheets(sheets)
    return 0


def _print_sheets(sheets):
    for sh in sheets:
        hdr, rows = sh["headers"], sh["rows"]
        ncol = max([len(hdr)] + [len(r) for r in rows])
        cols = [hdr[i] if i < len(hdr) else f"col{i}" for i in range(ncol)]
        widths = [max(len(cols[i]), max((len(r[i]) for r in rows if i < len(r)), default=0))
                  for i in range(ncol)]

        def line(vals):
            return "  ".join((vals[i] if i < len(vals) else "").ljust(widths[i]) for i in range(ncol))

        print(line(cols))
        for r in rows:
            print(line(r))
        print(f"\nSource (open to verify): {sh['source_url']}\n")
