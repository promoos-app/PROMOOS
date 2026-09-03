import { useEffect, useState } from "react";
import axios from "axios";
import { getContrastText } from "@/lib/contrast";

const API = process.env.REACT_APP_BACKEND_URL;

// A tiny helper so every block can pull its own overrides on top of the theme.
// Merchants can tint any block's background/accent/text without touching the global theme.
export function blockColors(block, theme) {
  const p = block.props || {};
  return {
    bg: p.bg || null,
    accent: p.accent || theme.accent,
    fg: p.fg || theme.fg,
    theme,
  };
}

export function trackFunnelEvent(slug, event, extra) {
  if (!slug || !event) return;
  try {
    const body = { event, ...(extra || {}) };
    // fire-and-forget, don't block UI
    if (navigator.sendBeacon) {
      const blob = new Blob([JSON.stringify(body)], { type: "application/json" });
      navigator.sendBeacon(`${API}/api/public/f/${slug}/track`, blob);
    } else {
      axios.post(`${API}/api/public/f/${slug}/track`, body).catch(() => {});
    }
  } catch (e) { /* noop */ }
}

export function Countdown({ block, theme }) {
  const c = blockColors(block, theme);
  const [t, setT] = useState({ d: 0, h: 0, m: 0, s: 0, done: false });
  useEffect(() => {
    const tick = () => {
      const diff = new Date(block.props.ends_at).getTime() - Date.now();
      if (diff <= 0) { setT({ d: 0, h: 0, m: 0, s: 0, done: true }); return; }
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setT({ d, h, m, s, done: false });
    };
    tick(); const id = setInterval(tick, 1000); return () => clearInterval(id);
  }, [block.props.ends_at]);
  return (
    <section className="py-16 px-6 text-center" data-testid="funnel-block-countdown" style={c.bg ? { background: c.bg } : undefined}>
      <div className="text-[10px] tracking-[0.3em] uppercase font-bold mb-4" style={{ color: c.accent }}>{block.props.label || "Offer ends in"}</div>
      {t.done ? (
        <div className="text-4xl font-bold opacity-60">Offer ended</div>
      ) : (
        <div className="flex justify-center gap-4">
          {[["Days", t.d], ["Hours", t.h], ["Minutes", t.m], ["Seconds", t.s]].map(([l, v]) => (
            <div key={l} className="min-w-[72px]">
              <div className="text-5xl font-bold tabular-nums" style={{ color: c.accent, fontFamily: theme.font_display }}>{String(v).padStart(2, "0")}</div>
              <div className="text-[10px] tracking-widest uppercase opacity-60 mt-1">{l}</div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

const CURRENCY_SYMBOLS = {
  USD: "$", CAD: "$", AUD: "$", NZD: "$", SGD: "$", HKD: "$", MXN: "$", BRL: "R$", ARS: "$", CLP: "$", COP: "$",
  EUR: "€", GBP: "£", JPY: "¥", CNY: "¥", CHF: "CHF ", SEK: "kr ", NOK: "kr ", DKK: "kr ",
  INR: "₹", AED: "د.إ ", SAR: "﷼ ", ILS: "₪", TRY: "₺", RUB: "₽",
  KRW: "₩", TWD: "NT$", THB: "฿", IDR: "Rp ", PHP: "₱", MYR: "RM ", VND: "₫",
  ZAR: "R", NGN: "₦", KES: "KSh ", EGP: "E£", PLN: "zł ", CZK: "Kč ", HUF: "Ft ",
};

// Public-facing helper: return "€49.00" / "$49.00" / "¥4900" based on currency code.
export function fmtMoney(amount, currency) {
  const code = (currency || "USD").toUpperCase();
  const sym = CURRENCY_SYMBOLS[code];
  const n = Number(amount || 0);
  const zeroDecimal = ["JPY", "KRW", "VND", "IDR", "CLP", "HUF"].includes(code);
  const value = zeroDecimal ? Math.round(n).toLocaleString() : n.toFixed(2);
  return sym ? `${sym}${value}` : `${code} ${value}`;
}

function computeDiscounted(price, coupon) {
  if (!price || !coupon) return null;
  const val = coupon.discount_value != null ? coupon.discount_value
    : (coupon.value != null ? coupon.value : null);
  if (val == null || !Number.isFinite(Number(val)) || Number(val) <= 0) return null;
  const type = (coupon.discount_type || coupon.type || "").toLowerCase();
  // Fixed-amount off types
  if (type === "fixed" || type === "fixed_amount" || type === "amount") {
    const out = Math.max(0, price - Number(val));
    return out < price ? out : null;
  }
  // Percentage-off — explicit allow-list from the platform's coupon taxonomy so
  // types like free_shipping/bogo/gift don't render a bogus "% off" price.
  const PCT_TYPES = new Set([
    "percentage", "percent", "%",
    "vip", "frequent", "regular", "new", "at_risk",
    "flash", "launch", "loyalty", "welcome", "seasonal",
  ]);
  if (PCT_TYPES.has(type)) {
    const out = Math.max(0, price * (1 - Number(val) / 100));
    return out < price ? out : null;
  }
  return null;
}

export function ProductBlock({ block, theme, slug }) {
  const [busy, setBusy] = useState(false);
  const p = block.props || {};
  const c = blockColors(block, theme);
  const product = p.product || null;
  const coupon = p.coupon || null;
  const buy = async () => {
    trackFunnelEvent(slug, "buy_now_click", { block_id: block.id, block_type: "product" });
    setBusy(true);
    try {
      const { data } = await axios.post(`${API}/api/public/products/checkout`, {
        product_id: p.product_id, origin_url: window.location.origin,
        coupon_code: p.coupon_code || null,
      });
      window.location.href = data.checkout_url;
    } catch (e) { alert((e && e.response && e.response.data && e.response.data.detail) || "Checkout failed"); setBusy(false); }
  };
  const price = product && product.price;
  const discounted = computeDiscounted(price, coupon);
  const currency = (product && product.currency) || "USD";
  const buttonLabel = busy ? "Redirecting..." : (p.product_id ? "Buy now" : "Attach a product to enable checkout");
  return (
    <section id={block.anchor} className="py-20 px-6" data-testid="funnel-block-product"
      style={c.bg ? { background: c.bg } : undefined}>
      <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-10 items-center rounded-2xl p-8"
        style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)" }}>
        <div className="rounded-xl overflow-hidden" style={{ background: "rgba(255,255,255,0.06)", aspectRatio: "1/1" }}>
          {product && product.image_url ? (
            <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-xs opacity-40">Product image</div>
          )}
        </div>
        <div>
          <div className="text-[10px] tracking-[0.3em] uppercase font-bold mb-2" style={{ color: c.accent }}>
            Featured product
          </div>
          <h2 className="font-bold text-3xl mb-3" style={{ fontFamily: theme.font_display }}>
            {(product && product.name) || "Buy now"}
          </h2>
          {product && product.description ? (
            <p className="text-sm opacity-75 mb-5 leading-relaxed">{product.description}</p>
          ) : null}
          {price != null && discounted != null ? (
            <div className="flex items-baseline gap-3 mb-5">
              <span className="text-3xl font-bold" style={{ color: c.accent }}>{fmtMoney(discounted, currency)}</span>
              <span className="text-lg opacity-50 line-through">{fmtMoney(price, currency)}</span>
            </div>
          ) : null}
          {price != null && discounted == null ? (
            <div className="flex items-baseline gap-3 mb-5">
              <span className="text-3xl font-bold" style={{ color: c.accent }}>{fmtMoney(price, currency)}</span>
            </div>
          ) : null}
          {p.coupon_code ? (
            <div className="text-xs opacity-70 mb-4">
              Code <code className="font-mono font-bold">{p.coupon_code}</code> applied at checkout
            </div>
          ) : null}
          <button onClick={buy} disabled={busy || !p.product_id}
            data-testid="funnel-buy-now-btn"
            className="w-full md:w-auto px-8 py-3 font-bold rounded-full transition hover:scale-[1.03] disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ background: c.accent, color: getContrastText(c.accent, theme.bg) }}>
            {buttonLabel}
          </button>
        </div>
      </div>
    </section>
  );
}

export function Testimonials({ block, theme }) {
  const p = block.props || {};
  const c = blockColors(block, theme);
  const items = (p.items && p.items.length) ? p.items : [
    { quote: p.quote, author: p.author, role: p.role, avatar_url: p.avatar_url },
  ];
  const gridCols = items.length > 1 ? "grid grid-cols-1 md:grid-cols-3 gap-6" : "grid grid-cols-1 gap-6";
  return (
    <section id={block.anchor} className="py-20 px-6" data-testid="funnel-block-testimonials"
      style={c.bg ? { background: c.bg } : undefined}>
      <div className="max-w-5xl mx-auto">
        {p.title ? (
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-12" style={{ fontFamily: theme.font_display }}>{p.title}</h2>
        ) : null}
        <div className={gridCols}>
          {items.map((it, i) => (
            <figure key={i} className="rounded-2xl p-6" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <div className="text-xl" style={{ color: c.accent }}>{"\u2605".repeat(Math.max(1, Math.min(5, it.rating || 5)))}</div>
              <blockquote className="mt-3 text-base italic leading-relaxed" style={{ fontFamily: theme.font_display }}>"{it.quote}"</blockquote>
              <figcaption className="mt-4 flex items-center gap-3">
                {it.avatar_url ? (<img src={it.avatar_url} alt={it.author} className="w-9 h-9 rounded-full object-cover" />) : null}
                <div>
                  <div className="text-sm font-bold">{it.author}</div>
                  {it.role ? (<div className="text-[11px] opacity-60">{it.role}</div>) : null}
                </div>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}
