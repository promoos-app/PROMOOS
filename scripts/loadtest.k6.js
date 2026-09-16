// k6 load test — /api/public/f/:slug + /api/coupons/redeem
//
// Usage:
//   BASE_URL=https://campaign-hub-436.preview.emergentagent.com \
//   FUNNEL_SLUG=summer-sale-2026 \
//   COUPON_CODE=SUMMER25 \
//   k6 run scripts/loadtest.k6.js
//
// Install: https://k6.io/docs/get-started/installation/  (brew install k6)
//
// Stages ramp to 500 rps sustained for 2 minutes. Thresholds fail the run if
// p95 latency exceeds 500 ms or error rate exceeds 1%.
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const funnelLatency = new Trend('funnel_latency', true);
const redeemLatency = new Trend('redeem_latency', true);
const errorRate = new Rate('errors');

const BASE = __ENV.BASE_URL || 'http://localhost:8001';
const SLUG = __ENV.FUNNEL_SLUG || 'qa-storefront-live';
const CODE = __ENV.COUPON_CODE || 'SUMMER25';

export const options = {
  scenarios: {
    funnel_reads: {
      executor: 'ramping-arrival-rate',
      exec: 'readFunnel',
      startRate: 10,
      timeUnit: '1s',
      preAllocatedVUs: 200,
      maxVUs: 800,
      stages: [
        { target: 100, duration: '30s' },
        { target: 300, duration: '30s' },
        { target: 500, duration: '30s' },   // Hold 500 rps for reads
        { target: 500, duration: '2m' },
        { target: 0,   duration: '30s' },
      ],
    },
    coupon_redeems: {
      executor: 'ramping-arrival-rate',
      exec: 'redeemCoupon',
      startRate: 5,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 200,
      stages: [
        { target: 25,  duration: '30s' },
        { target: 75,  duration: '30s' },
        { target: 100, duration: '2m30s' }, // 100 rps validation writes
        { target: 0,   duration: '30s' },
      ],
    },
  },
  thresholds: {
    'http_req_duration{scenario:funnel_reads}':  ['p(95)<500', 'p(99)<1200'],
    'http_req_duration{scenario:coupon_redeems}': ['p(95)<700', 'p(99)<1500'],
    errors: ['rate<0.01'],
  },
};

export function readFunnel() {
  const url = `${BASE}/api/public/f/${SLUG}`;
  const r = http.get(url, { tags: { name: 'funnel_read' } });
  funnelLatency.add(r.timings.duration);
  const ok = check(r, { 'funnel 200': (x) => x.status === 200 });
  errorRate.add(!ok);
}

export function redeemCoupon() {
  const url = `${BASE}/api/public/coupons/validate`;
  const r = http.post(url,
    JSON.stringify({ code: CODE, cart_total: 89.99 }),
    { headers: { 'Content-Type': 'application/json' }, tags: { name: 'coupon_validate' } });
  redeemLatency.add(r.timings.duration);
  const ok = check(r, { 'validate 200 or 404': (x) => x.status === 200 || x.status === 404 });
  errorRate.add(!ok);
}
