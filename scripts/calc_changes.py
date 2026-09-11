#!/usr/bin/env python3
"""Calculate multi-period change percentages for SW2 sectors from kline_data.json.

Pure Python standard library - no third-party dependency.

Computes chg_5d / chg_10d / chg_20d / chg_60d against the close N trading days ago,
joins sector name + parent industry from sectors.json, sorts, and prints JSON or TSV.

Usage:
  python calc_changes.py --input data/kline_data.json --sector-info data/sectors.json \
      --sort chg_5d --format tsv
  python calc_changes.py --input data/kline_data.json --sector-info data/sectors.json \
      --sort chg_20d --format tsv --bottom 15
"""

import argparse
import json
import sys
from pathlib import Path

FIELDS = ("code", "name", "parent", "close", "chg_5d", "chg_10d", "chg_20d", "chg_60d")


def parse_kline_data(raw):
    """Parse kline_data.json into {code: [{'date','last'}, ...]}.

    Accepts:
      {"data": {"data": [{"symbol","data":{"nodes":[...]}}, ...], ...}}
      {"data": [{"symbol","data":{"nodes":[...]}}, ...]}
      {"CODE": [{"date","last"}, ...], ...}
    """
    sectors = {}

    def extract(item):
        symbol = item.get("symbol") or item.get("code") or ""
        obj = item.get("data") or item.get("nodes") or []
        nodes = obj.get("nodes", []) if isinstance(obj, dict) else (obj if isinstance(obj, list) else [])
        return symbol, nodes

    if isinstance(raw, dict):
        if "data" in raw:
            d = raw["data"]
            if isinstance(d, list):
                for item in d:
                    if isinstance(item, dict):
                        s, n = extract(item)
                        if s:
                            sectors[s] = n
            elif isinstance(d, dict):
                sectors.update(parse_kline_data(d))
        else:
            for k, v in raw.items():
                if isinstance(v, list):
                    sectors[k] = v
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                sectors.update(parse_kline_data(item))
    return sectors


def calc_changes(nodes):
    """Return {close, chg_5d, chg_10d, chg_20d, chg_60d} from date-ascending nodes."""
    if not nodes:
        return {"close": 0, "chg_5d": None, "chg_10d": None, "chg_20d": None, "chg_60d": None}

    ordered = sorted(nodes, key=lambda x: x.get("date", ""))
    close = float(ordered[-1].get("last", 0))

    def chg(days):
        if len(ordered) > days:
            prev = float(ordered[-(days + 1)].get("last", 0))
            if prev:
                return round((close - prev) / prev * 100, 2)
        return None

    return {
        "close": round(close, 2),
        "chg_5d": chg(5),
        "chg_10d": chg(10),
        "chg_20d": chg(20),
        "chg_60d": chg(60),
    }


def load_sector_info(path):
    """Return ({code: name}, {code: parent}) from sectors.json."""
    if not path:
        return {}, {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    name_map, parent_map = {}, {}

    if isinstance(data, dict):
        for val in data.values():
            if isinstance(val, dict) and "items" in val:
                for item in val["items"]:
                    code = item.get("code", "")
                    name_map[code] = item.get("name", code)
                    if item.get("parent"):
                        parent_map[code] = item["parent"]
                break
        if not name_map:
            for k, v in data.items():
                if isinstance(v, str):
                    name_map[k] = v
    return name_map, parent_map


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="kline_data.json path")
    ap.add_argument("--sector-info", default="", help="sectors.json path (code->name/parent)")
    ap.add_argument("--sort", default="chg_5d",
                    choices=["chg_5d", "chg_10d", "chg_20d", "chg_60d", "close"])
    ap.add_argument("--format", default="json", choices=["json", "tsv"])
    ap.add_argument("--fields", default="name,parent,chg_5d,chg_10d,chg_20d,chg_60d",
                    help="TSV output fields")
    ap.add_argument("--limit", type=int, default=0, help="Keep only top N rows (0 = all)")
    ap.add_argument("--bottom", type=int, default=0,
                    help="Keep only bottom N rows, worst first (for a #124..#110 style table)")
    args = ap.parse_args()

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    sectors = parse_kline_data(raw)
    print(f"Parsed K-line data for {len(sectors)} sectors", file=sys.stderr)
    if not sectors:
        print("No sector data found in input file", file=sys.stderr)
        sys.exit(1)

    name_map, parent_map = load_sector_info(args.sector_info)
    results = []
    for code, nodes in sectors.items():
        row = {"code": code, "name": name_map.get(code, code),
               "parent": parent_map.get(code, "")}
        row.update(calc_changes(nodes))
        results.append(row)

    results.sort(
        key=lambda s: (s.get(args.sort) if s.get(args.sort) is not None else -999),
        reverse=True,
    )

    if args.bottom:
        # worst-first: results are sorted descending, so take the tail then reverse
        results = results[-args.bottom:][::-1]
    elif args.limit:
        results = results[:args.limit]

    up = sum(1 for s in results if (s.get("chg_5d") or 0) >= 0)
    print(f"Rows={len(results)} Up(5d)={up} Down(5d)={len(results) - up}", file=sys.stderr)

    if args.format == "tsv":
        fields = [f.strip() for f in args.fields.split(",")]
        print("\t".join(fields))
        for s in results:
            cells = []
            for f in fields:
                v = s.get(f, "")
                if isinstance(v, float) and f.startswith("chg_"):
                    cells.append(f"+{v:.2f}%" if v >= 0 else f"{v:.2f}%")
                else:
                    cells.append(str(v))
            print("\t".join(cells))
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
