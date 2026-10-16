#!/usr/bin/env python3
"""hk_worker.py — 港股日K worker (GitHub Actions / 本地)
数据源: 腾讯 web.ifzq.gtimg.cn fqkline (hk 前缀, qfq 前复权), 备选新浪 (未启用, hk 日K sina datalen 有限)
符号表: symbols.json — 港股通标的 ~2072 只 (东财 RPT_MUTUAL_HOLD MUTUAL_TYPE=003 快照)
用法: hk_worker.py [batch]
输出: wh/hk_daily/<year>.parquet  字段: symbol,date,open,close,high,low,volume
"""
import json, os, sys, time, pathlib
import urllib.request

BATCH = int(sys.argv[1]) if len(sys.argv) > 1 else 300
WH = "wh/hk_daily"
UA_T = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com"}
COLS = ["symbol", "date", "open", "close", "high", "low", "volume"]

def get(url, timeout=15):
    req = urllib.request.Request(url, headers=UA_T)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")

def tencent_hk_daily(hkcode, count=320):
    # hkcode like 00700 -> hk00700
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=hk{hkcode},day,,,{count},qfq"
    d = json.loads(get(url))
    k = d["data"][f"hk{hkcode}"]
    key = next((x for x in k if "qfq" in x or x == "day"), None)
    rows = k.get(key, []) if key else []
    out = []
    for r in rows:
        if not isinstance(r, list) or len(r) < 6: continue
        try:
            out.append([f"hk{hkcode}", r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])])
        except Exception:
            continue
    return out

def write_partition(year, rows):
    import pyarrow.parquet as pq, pyarrow as pa
    pathlib.Path(WH).mkdir(parents=True, exist_ok=True)
    path = f"{WH}/{year}.parquet"
    old = {}
    if os.path.exists(path):
        t = pq.read_table(path)
        for row in zip(*[t.column(c).to_pylist() for c in t.column_names]):
            old[(row[0], row[1])] = list(row)
    for r in rows:
        old[(r[0], r[1])] = r
    rows = sorted(old.values(), key=lambda r: (r[0], r[1]))
    pq.write_table(pa.table({c: [r[i] for r in rows] for i, c in enumerate(COLS)}),
                   path, compression="zstd")

def main():
    import pyarrow  # fail fast if missing
    syms = json.load(open("symbols.json"))["symbols"]
    done = set(open("_done.txt").read().split()) if os.path.exists("_done.txt") else set()
    todo = [s for s in syms if s not in done][:BATCH]
    print(f"hk worker: {len(todo)} 待补 (done={len(done)}/{len(syms)})", flush=True)
    t0 = time.time()
    ok = fail = 0
    buf = []
    for i, s in enumerate(todo):
        try:
            rows = tencent_hk_daily(s)
            buf += rows; ok += 1
        except Exception as e:
            fail += 1
            print(f"  {s} FAIL {e}", flush=True)
        if len(buf) > 20000 or i == len(todo) - 1:
            years = sorted({r[1][:4] for r in buf})
            for y in years:
                write_partition(y, [r for r in buf if r[1].startswith(y)])
            buf = []
        time.sleep(0.15)
    open("_done.txt", "a").write("\n".join(todo) + "\n")
    print(f"hk worker done: ok={ok} fail={fail} elapsed={time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
