#!/usr/bin/env python3
"""In-container smoke load test — validates Mongo indexes and API budgets.

Runs mixed reads (public funnel) + writes (public coupon validate) against the
live preview URL with asyncio + httpx. Fast, no external dependencies beyond
what's already installed. This is NOT a substitute for `loadtest.k6.js` at
500 rps — it exists to give a quick indexed-vs-unindexed signal in-container.

Usage:
    BASE_URL=... SLUG=... CODE=... python3 scripts/loadtest_bench.py \\
        --duration 20 --concurrency 100

Thresholds (informational; script always exits 0 unless --strict is set):
    p95(funnel_read)    < 500 ms
    p95(coupon_validate) < 700 ms
    error rate          < 1%
"""
import argparse
import asyncio
import os
import statistics
import sys
import time
from typing import List

import httpx


async def _run_worker(client: httpx.AsyncClient, base: str, slug: str, code: str,
                      durations: List[float], errors: List[str], deadline: float,
                      mix_pct_validate: int) -> None:
    """One coroutine issues requests until deadline elapses."""
    import random
    while time.monotonic() < deadline:
        is_validate = random.randint(1, 100) <= mix_pct_validate
        start = time.monotonic()
        try:
            if is_validate:
                r = await client.post(f"{base}/api/public/coupons/validate",
                                       json={"code": code, "cart_total": 89.99},
                                       timeout=10.0)
                ok = r.status_code in (200, 400, 404)  # 404 = unknown code is a valid outcome
            else:
                r = await client.get(f"{base}/api/public/f/{slug}", timeout=10.0)
                ok = r.status_code in (200, 404)
            elapsed_ms = (time.monotonic() - start) * 1000.0
            durations.append(elapsed_ms)
            if not ok:
                errors.append(f"{'validate' if is_validate else 'funnel'} {r.status_code}")
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000.0
            durations.append(elapsed_ms)
            errors.append(str(e)[:80])


def _percentile(values: List[float], pct: float) -> float:
    if not values: return 0.0
    values_sorted = sorted(values)
    k = min(int(round((pct / 100.0) * len(values_sorted))) - 1, len(values_sorted) - 1)
    return values_sorted[max(k, 0)]


async def main() -> int:
    parser = argparse.ArgumentParser(description="PromoOS in-container load bench")
    parser.add_argument("--duration", type=int, default=20, help="seconds")
    parser.add_argument("--concurrency", type=int, default=50, help="parallel coroutines")
    parser.add_argument("--mix-validate", type=int, default=20,
                        help="percentage of requests hitting /public/coupons/validate")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 if p95 or error thresholds are exceeded")
    args = parser.parse_args()

    base = (os.environ.get("BASE_URL") or "").rstrip("/")
    if not base:
        # Prefer external preview URL for realistic latency.
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        base = line.split("=", 1)[1].strip().rstrip("/")
                        break
        except FileNotFoundError:
            pass
    if not base:
        base = "http://localhost:8001"
    slug = os.environ.get("SLUG", "qa-storefront-live")
    code = os.environ.get("CODE", "SUMMER25")

    print(f"→ target:      {base}")
    print(f"→ funnel slug: {slug}")
    print(f"→ coupon code: {code}")
    print(f"→ mix:         {100 - args.mix_validate}% funnel reads / {args.mix_validate}% coupon validates")
    print(f"→ duration:    {args.duration}s @ concurrency={args.concurrency}")

    deadline = time.monotonic() + args.duration
    durations: List[float] = []
    errors: List[str] = []
    limits = httpx.Limits(max_connections=args.concurrency * 2,
                          max_keepalive_connections=args.concurrency)
    async with httpx.AsyncClient(limits=limits, http2=False) as client:
        # Prewarm connections
        try: await client.get(f"{base}/api/public/f/{slug}", timeout=5.0)
        except Exception: pass
        workers = [asyncio.create_task(_run_worker(
            client, base, slug, code, durations, errors, deadline, args.mix_validate))
            for _ in range(args.concurrency)]
        await asyncio.gather(*workers, return_exceptions=True)

    total = len(durations)
    err = len(errors)
    if total == 0:
        print("❌ No requests completed.")
        return 1
    rps = total / max(args.duration, 1)
    p50 = _percentile(durations, 50)
    p95 = _percentile(durations, 95)
    p99 = _percentile(durations, 99)
    mean = statistics.mean(durations)
    err_rate = err / total

    print()
    print("═" * 56)
    print(f"  Requests total : {total}")
    print(f"  Throughput     : {rps:.1f} rps")
    print(f"  Errors         : {err}  ({err_rate * 100:.2f}%)")
    print(f"  Latency mean   : {mean:.1f} ms")
    print(f"  Latency p50    : {p50:.1f} ms")
    print(f"  Latency p95    : {p95:.1f} ms")
    print(f"  Latency p99    : {p99:.1f} ms")
    print("═" * 56)

    # Threshold check
    fails = []
    if p95 > 500 and args.mix_validate < 50:
        fails.append(f"p95 {p95:.0f}ms > 500ms budget (funnel-heavy)")
    if p95 > 700 and args.mix_validate >= 50:
        fails.append(f"p95 {p95:.0f}ms > 700ms budget (validate-heavy)")
    if err_rate > 0.01:
        # Cluster first 5 error kinds
        from collections import Counter
        top = Counter(errors).most_common(5)
        fails.append(f"error rate {err_rate * 100:.2f}% > 1%. Top: {top}")

    if fails:
        print("⚠️  Threshold breaches:")
        for f in fails: print(f"    · {f}")
        if args.strict:
            return 1
    else:
        print("✅ All latency + error budgets held.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(130)
