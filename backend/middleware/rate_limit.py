"""Per-IP token-bucket rate limiter for /api/public/* endpoints.

Three tiers by route:
    - strict   (30/min): validate, redeem, checkout          — brute-force targets
    - standard (120/min): public reads, opt-ins              — normal traffic
    - loose    (300/min): analytics beacons (/track)         — high volume expected

In-memory dict. Single-process pod means this doesn't need Redis at MVP scale.
Emits `X-RateLimit-*` headers on every request and `Retry-After` on 429.
Persists 429 events to `db.rate_limit_events` so abusers surface in Admin.
"""
import time
import logging
import asyncio
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("promoos.ratelimit")


# Refills tokens per second. Bucket size = tier limit; refill = limit / 60.
TIERS = {
    "strict":   {"limit": 30,  "refill_per_sec": 30 / 60.0},
    "standard": {"limit": 120, "refill_per_sec": 120 / 60.0},
    "loose":    {"limit": 300, "refill_per_sec": 300 / 60.0},
}


def _classify_route(method: str, path: str) -> str | None:
    """Return the tier name, or None to skip rate limiting entirely."""
    if not path.startswith("/api/public/"):
        return None
    # Analytics beacons — highest budget so partner sites don't clobber their own funnel.
    if path.endswith("/track") or path.endswith("/event"):
        return "loose"
    # Money paths — strictest budget.
    if any(seg in path for seg in ("/coupons/validate", "/coupons/redeem",
                                    "/products/checkout")):
        return "strict"
    # Everything else public.
    return "standard"


def _client_ip(request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return (request.client.host if request.client else "unknown") or "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Attach at app.add_middleware. Requires `db` bound at construction."""

    def __init__(self, app, db=None):
        super().__init__(app)
        self._db = db
        # key: (ip, tier) -> {tokens: float, last: float}
        self._buckets: dict[tuple[str, str], dict] = {}
        # (ip, tier) -> monotonic timestamp of last DB write, throttled to 60s.
        self._last_persist: dict[tuple[str, str], float] = {}
        # Sweep buckets older than 5 min once every minute to bound memory.
        self._last_sweep = time.monotonic()

    def _sweep_if_due(self) -> None:
        now = time.monotonic()
        if now - self._last_sweep < 60:
            return
        stale_cutoff = now - 300
        stale_keys = [k for k, v in self._buckets.items() if v["last"] < stale_cutoff]
        for k in stale_keys:
            self._buckets.pop(k, None)
        self._last_sweep = now

    async def _persist_429(self, ip: str, tier: str, path: str) -> None:
        if self._db is None:
            return
        key = (ip, tier)
        now_m = time.monotonic()
        if now_m - self._last_persist.get(key, 0) < 60:
            return  # throttle DB writes to at most one per (ip, tier) per minute
        self._last_persist[key] = now_m
        try:
            await self._db.rate_limit_events.insert_one({
                "ip": ip, "tier": tier, "path": path,
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
        except Exception:
            pass  # never let telemetry crash the request path

    async def dispatch(self, request, call_next):
        tier = _classify_route(request.method, request.url.path)
        if tier is None:
            return await call_next(request)

        cfg = TIERS[tier]
        ip = _client_ip(request)
        key = (ip, tier)
        now = time.monotonic()

        b = self._buckets.get(key)
        if b is None:
            b = {"tokens": float(cfg["limit"]), "last": now}
            self._buckets[key] = b
        else:
            elapsed = now - b["last"]
            b["tokens"] = min(cfg["limit"], b["tokens"] + elapsed * cfg["refill_per_sec"])
            b["last"] = now

        self._sweep_if_due()

        if b["tokens"] < 1:
            # Not enough — reject.
            retry_after = max(1, int((1 - b["tokens"]) / cfg["refill_per_sec"]))
            # Persist telemetry (await inline so a slow Mongo doesn't hide events;
            # the 60s throttle below prevents this from being a hot path).
            try:
                await self._persist_429(ip, tier, request.url.path)
            except Exception as e:
                logger.debug(f"rate_limit_events persist skipped: {e}")
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded ({cfg['limit']}/min for {tier} endpoints). "
                                    f"Retry in {retry_after}s."},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(cfg["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Tier": tier,
                },
            )

        b["tokens"] -= 1
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(cfg["limit"])
        response.headers["X-RateLimit-Remaining"] = str(int(b["tokens"]))
        response.headers["X-RateLimit-Tier"] = tier
        return response
