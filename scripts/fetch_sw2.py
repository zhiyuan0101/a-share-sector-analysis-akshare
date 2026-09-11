#!/usr/bin/env python3
"""Fetch 申万二级 (SW2) industry index daily K-lines via akshare (申万宏源研究数据源).

Standalone data fetcher for the a-share-sector-analysis-akshare skill.
No MCP connector required - only `pip install akshare`.

Outputs (into --out-dir):
  sectors.json    {"industry_list_sw2": {"items": [{"code","name","parent"}, ...]}}
  kline_data.json {"data": {"data": [{"symbol","data":{"nodes":[{"date","last"}]}}, ...],
                            "errors": [...], "metadata": {...}}}

Usage:
  python fetch_sw2.py --out-dir ./data
  python fetch_sw2.py --out-dir ./data --workers 8 --keep-rows 70
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import akshare as ak
import pandas as pd


def fetch_one(code: str, keep_rows: int, retries: int = 3):
    """Return (code, nodes, error). nodes = [{'date','last'}, ...] ascending by date."""
    bare = code.split(".")[0]
    last_err = None
    for attempt in range(retries):
        try:
            df = ak.index_hist_sw(symbol=bare, period="day")
            if df is None or df.empty:
                return code, [], "empty response"
            df = df[["日期", "收盘"]].copy()
            df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
            df = df.dropna().tail(keep_rows)
            nodes = [
                {"date": d, "last": round(float(c), 2)}
                for d, c in df.itertuples(index=False, name=None)
            ]
            return code, nodes, None
        except Exception as e:  # noqa: BLE001 - network flakiness, retry
            last_err = e
            time.sleep(1.0 * (attempt + 1))
    return code, [], str(last_err)


def main():
    ap = argparse.ArgumentParser(description="Fetch SW2 sector index history via akshare")
    ap.add_argument("--out-dir", default=".", help="Output directory for JSON files")
    ap.add_argument("--workers", type=int, default=6, help="Concurrent fetch threads")
    ap.add_argument("--keep-rows", type=int, default=70,
                    help="Trailing bars to keep per sector (70 is enough for chg_60d)")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    info = ak.sw_index_second_info()
    items = [
        {
            "code": str(row["行业代码"]),
            "name": row["行业名称"],
            "parent": row.get("上级行业", ""),
        }
        for _, row in info.iterrows()
    ]
    print(f"[info] SW2 sectors listed by akshare: {len(items)}", file=sys.stderr)

    (out_dir / "sectors.json").write_text(
        json.dumps({"industry_list_sw2": {"items": items}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    results, errors = {}, []
    done, total = 0, len(items)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch_one, it["code"], args.keep_rows): it["code"] for it in items}
        for fut in as_completed(futures):
            code, nodes, err = fut.result()
            done += 1
            if err or not nodes:
                errors.append({"code": code, "error": err or "empty"})
            else:
                results[code] = nodes
            if done % 20 == 0 or done == total:
                print(f"[info] fetched {done}/{total}", file=sys.stderr)

    if not results:
        print("[fatal] no data fetched - check network / akshare version", file=sys.stderr)
        sys.exit(1)

    # Drop stale indices: SWS stops publishing some legacy sub-indices (e.g. 801011 林业)
    # Keeping them would corrupt rankings because their "latest" bar is months old.
    latest = max(n[-1]["date"] for n in results.values())
    kept = {c: n for c, n in results.items() if n[-1]["date"] >= latest}
    dropped = sorted(set(results) - set(kept))
    if dropped:
        print(f"[warn] dropped {len(dropped)} stale sectors (last bar < {latest}): {dropped}",
              file=sys.stderr)

    batch = {
        "data": {
            "data": [{"symbol": c, "data": {"nodes": n}} for c, n in sorted(kept.items())],
            "errors": errors,
            "metadata": {
                "total": len(items),
                "successCount": len(kept),
                "errorCount": len(errors),
                "droppedStale": dropped,
                "latestDate": latest,
                "source": "akshare:index_hist_sw (申万宏源研究)",
            },
        }
    }
    (out_dir / "kline_data.json").write_text(
        json.dumps(batch, ensure_ascii=False), encoding="utf-8"
    )

    print(f"[done] sectors={len(kept)} latest={latest} "
          f"failed={len(errors)} droppedStale={len(dropped)}", file=sys.stderr)


if __name__ == "__main__":
    main()
