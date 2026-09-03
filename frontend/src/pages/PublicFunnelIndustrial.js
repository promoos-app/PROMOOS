import { useState } from "react";
import axios from "axios";
import { getContrastText } from "@/lib/contrast";

const API = process.env.REACT_APP_BACKEND_URL;

function bg(props, theme) {
  return props.bg ? { background: props.bg } : undefined;
}

export function LogoBar({ block, theme }) {
  const p = block.props || {};
  return (
    <section className="py-8 px-6 border-b" style={{ borderColor: "rgba(255,255,255,0.05)", ...(p.bg ? { background: p.bg } : {}) }}
      data-testid="funnel-block-logo_bar">
      <div className="max-w-5xl mx-auto text-center">
        {p.label ? <div className="text-[10px] uppercase tracking-[0.3em] opacity-50 mb-4">{p.label}</div> : null}
        <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
          {(p.logos || []).map((l, i) => (
            <div key={i} className="text-lg font-bold opacity-40 hover:opacity-80 transition"
              style={{ fontFamily: theme.font_display }}>{l}</div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function Stats({ block, theme }) {
  const p = block.props || {};
  return (
    <section className="py-16 px-6" data-testid="funnel-block-stats" style={bg(p, theme)}>
      <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
        {(p.items || []).map((it, i) => (
          <div key={i}>
            <div className="text-5xl font-bold" style={{ color: p.accent || theme.accent, fontFamily: theme.font_display }}>{it.value}</div>
            <div className="text-[11px] tracking-widest uppercase opacity-70 mt-2">{it.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function Guarantee({ block, theme }) {
  const p = block.props || {};
  const accent = p.accent || theme.accent;
  return (
    <section className="py-14 px-6" data-testid="funnel-block-guarantee" style={bg(p, theme)}>
      <div className="max-w-2xl mx-auto rounded-2xl p-8 flex items-center gap-6 border" style={{ borderColor: `${accent}66`, background: "rgba(255,255,255,0.03)" }}>
        <div className="flex-shrink-0 w-16 h-16 rounded-full flex items-center justify-center text-3xl"
          style={{ background: `${accent}22`, color: accent }}>
          {p.icon === "clock" ? "⏱" : p.icon === "handshake" ? "🤝" : "🛡"}
        </div>
        <div>
          <div className="font-bold text-xl mb-1" style={{ fontFamily: theme.font_display }}>{p.title}</div>
          <div className="text-sm opacity-80">{p.text}</div>
        </div>
      </div>
    </section>
  );
}

export function PricingTable({ block, theme }) {
  const p = block.props || {};
  const accent = p.accent || theme.accent;
  return (
    <section id={block.anchor} className="py-20 px-6" data-testid="funnel-block-pricing_table" style={bg(p, theme)}>
      <div className="max-w-4xl mx-auto">
        {p.title ? <h2 className="text-3xl sm:text-4xl font-bold text-center mb-12" style={{ fontFamily: theme.font_display }}>{p.title}</h2> : null}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {(p.tiers || []).map((t, i) => (
            <div key={i} className="rounded-2xl p-8 relative"
              style={{
                background: t.highlight ? `linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))` : "rgba(255,255,255,0.03)",
                border: t.highlight ? `1px solid ${accent}` : "1px solid rgba(255,255,255,0.1)",
              }}>
              {t.highlight ? (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] uppercase tracking-widest font-bold px-3 py-1 rounded-full"
                  style={{ background: accent, color: theme.bg }}>Most popular</div>
              ) : null}
              <div className="text-xs uppercase tracking-widest opacity-60 mb-2">{t.name}</div>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-5xl font-bold" style={{ fontFamily: theme.font_display }}>${t.price}</span>
                <span className="text-sm opacity-60">/ {t.period}</span>
              </div>
              <ul className="space-y-2.5 mb-8 text-sm">
                {(t.features || []).map((f, k) => (
                  <li key={k} className="flex items-start gap-2">
                    <span style={{ color: accent }}>✓</span> <span>{f}</span>
                  </li>
                ))}
              </ul>
              <button className="w-full py-3 font-bold rounded-full transition hover:scale-[1.02]"
                data-testid={`pricing-cta-${t.name}`}
                style={t.highlight ? { background: accent, color: getContrastText(accent, theme.bg) } : { background: "rgba(255,255,255,0.06)", color: theme.fg, border: "1px solid rgba(255,255,255,0.15)" }}>
                {t.cta_label || "Select"}
              </button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function OrderBump({ block, theme }) {
  const p = block.props || {};
  const accent = p.accent || theme.accent;
  const [add, setAdd] = useState(false);
  return (
    <section className="py-8 px-6" data-testid="funnel-block-order_bump" style={bg(p, theme)}>
      <div className="max-w-2xl mx-auto rounded-lg p-5 flex items-start gap-4"
        style={{ background: `${accent}12`, border: `2px dashed ${accent}` }}>
        <input type="checkbox" checked={add} onChange={(e) => setAdd(e.target.checked)}
          data-testid={`order-bump-toggle-${block.id}`}
          className="mt-1 w-5 h-5 accent-current" style={{ accentColor: accent }} />
        <div className="flex-1">
          <div className="flex items-baseline justify-between gap-2 flex-wrap">
            <div className="font-bold text-lg" style={{ fontFamily: theme.font_display }}>{p.title}</div>
            <div className="font-mono text-sm" style={{ color: accent }}>+ ${p.price} {p.currency || "USD"}</div>
          </div>
          <div className="text-sm opacity-75 mt-1">{p.text}</div>
          {add ? <div className="mt-2 text-xs font-bold" style={{ color: accent }}>✓ Added to your order</div> : null}
        </div>
      </div>
    </section>
  );
}

export function Upsell({ block, theme, slug }) {
  const p = block.props || {};
  const accent = p.accent || theme.accent;
  return (
    <section id={block.anchor} className="py-20 px-6" data-testid="funnel-block-upsell" style={bg(p, theme)}>
      <div className="max-w-2xl mx-auto rounded-2xl p-10 text-center"
        style={{ background: `linear-gradient(135deg, ${accent}22, transparent)`, border: `1px solid ${accent}55` }}>
        <div className="text-[10px] uppercase tracking-[0.3em] font-bold mb-3" style={{ color: accent }}>One-time offer</div>
        <h2 className="text-3xl sm:text-4xl font-bold mb-3" style={{ fontFamily: theme.font_display }}>{p.headline}</h2>
        <p className="text-base opacity-80 mb-6">{p.text}</p>
        {p.price != null ? (
          <div className="text-4xl font-bold mb-6" style={{ color: accent }}>${p.price} {p.currency || "USD"}</div>
        ) : null}
        <button data-testid={`upsell-cta-${block.id}`} className="px-8 py-3 font-bold rounded-full transition hover:scale-[1.03]"
          style={{ background: accent, color: getContrastText(accent, theme.bg) }}>{p.cta_label || "Yes, add it"}</button>
      </div>
    </section>
  );
}

export function Optin({ block, theme, slug }) {
  const p = block.props || {};
  const accent = p.accent || theme.accent;
  const initial = Object.fromEntries((p.fields || []).map((f) => [f.key, ""]));
  const [values, setValues] = useState(initial);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const submit = async (e) => {
    e && e.preventDefault && e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post(`${API}/api/public/f/${slug}/optin`, {
        block_id: block.id,
        fields: values,
        lead_tag: p.lead_tag || "",
        source_url: typeof window !== "undefined" ? window.location.href : "",
      });
      setDone(true);
    } catch (err) {
      alert((err && err.response && err.response.data && err.response.data.detail) || "Submission failed");
    } finally { setSubmitting(false); }
  };
  return (
    <section id={block.anchor} className="py-20 px-6" data-testid="funnel-block-optin" style={bg(p, theme)}>
      <div className="max-w-md mx-auto rounded-2xl p-8"
        style={{ background: "rgba(255,255,255,0.04)", border: `1px solid ${accent}55` }}>
        {done ? (
          <div className="text-center py-6" data-testid="optin-success">
            <div className="text-5xl mb-3">✓</div>
            <div className="font-bold text-xl mb-2" style={{ fontFamily: theme.font_display }}>You&apos;re in.</div>
            <div className="text-sm opacity-75">{p.success_text || "Check your inbox in the next 2 minutes."}</div>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div>
              <h3 className="font-bold text-2xl" style={{ fontFamily: theme.font_display }}>{p.headline || "Enter your email"}</h3>
              {p.sub ? <p className="text-sm opacity-75 mt-1">{p.sub}</p> : null}
            </div>
            {(p.fields || []).map((f) => (
              <div key={f.key}>
                <label className="text-[10px] uppercase tracking-widest opacity-60 block mb-1">{f.label}{f.required ? " *" : ""}</label>
                {f.type === "textarea" ? (
                  <textarea rows={3} value={values[f.key] || ""} required={f.required}
                    data-testid={`optin-field-${f.key}`}
                    onChange={(e) => setValues({ ...values, [f.key]: e.target.value })}
                    className="w-full px-3 py-2 rounded-md text-sm outline-none"
                    style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", color: theme.fg }} />
                ) : (
                  <input type={f.key === "email" ? "email" : "text"}
                    value={values[f.key] || ""} required={f.required}
                    data-testid={`optin-field-${f.key}`}
                    onChange={(e) => setValues({ ...values, [f.key]: e.target.value })}
                    className="w-full px-3 py-2 rounded-md text-sm outline-none"
                    style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", color: theme.fg }} />
                )}
              </div>
            ))}
            <button type="submit" disabled={submitting}
              data-testid={`optin-submit-${block.id}`}
              className="w-full py-3 font-bold rounded-full transition hover:scale-[1.02] disabled:opacity-50"
              style={{ background: accent, color: getContrastText(accent, theme.bg) }}>
              {submitting ? "Sending..." : (p.cta_label || "Get access")}
            </button>
            <div className="text-[10px] opacity-50 text-center">We respect your privacy. Unsubscribe anytime.</div>
          </form>
        )}
      </div>
    </section>
  );
}

export function Spacer({ block }) {
  const h = (block.props && block.props.height) || 40;
  return <div style={{ height: `${h}px` }} data-testid="funnel-block-spacer" />;
}

export function Divider({ block, theme }) {
  const accent = (block.props && block.props.accent) || theme.accent;
  return (
    <div className="py-4 px-6" data-testid="funnel-block-divider">
      <div className="max-w-3xl mx-auto h-px" style={{ background: `linear-gradient(to right, transparent, ${accent}66, transparent)` }} />
    </div>
  );
}

export function FooterBlock({ block, theme, slug }) {
  const p = block.props || {};
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const unsub = async (e) => {
    e && e.preventDefault && e.preventDefault();
    if (!email || !email.includes("@")) return;
    setBusy(true);
    try {
      await axios.post(`${API}/api/public/f/${slug}/track`, {
        event: "cta_click", block_id: block.id, block_type: "footer_unsubscribe",
        meta: { unsubscribe_email: email },
      });
      setDone(true);
    } catch (err) { /* silent */ }
    finally { setBusy(false); }
  };
  const year = new Date().getFullYear();
  return (
    <footer className="mt-12 border-t px-6 py-10"
      data-testid="funnel-block-footer"
      style={{ borderColor: "rgba(255,255,255,0.08)", background: p.bg || "rgba(0,0,0,0.2)" }}>
      <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8 text-[12px]">
        <div className="space-y-2">
          <div className="text-sm font-bold" style={{ fontFamily: theme.font_display }}>{p.brand || "PromoOS"}</div>
          <div className="opacity-70 whitespace-pre-line">{p.address || ""}</div>
          <div className="opacity-70">{p.phone ? <>Tel: <a href={`tel:${p.phone}`} className="hover:opacity-100">{p.phone}</a></> : null}</div>
          <div className="opacity-70">{p.email ? <>Email: <a href={`mailto:${p.email}`} className="hover:opacity-100">{p.email}</a></> : null}</div>
        </div>
        <div className="space-y-2">
          <div className="text-[10px] uppercase tracking-widest opacity-60">Legal</div>
          {p.privacy_url ? <div><a href={p.privacy_url} target="_blank" rel="noreferrer" className="hover:underline opacity-80">Privacy Policy</a></div> : null}
          {p.terms_url ? <div><a href={p.terms_url} target="_blank" rel="noreferrer" className="hover:underline opacity-80">Terms of Use</a></div> : null}
          {p.cookies_url ? <div><a href={p.cookies_url} target="_blank" rel="noreferrer" className="hover:underline opacity-80">Cookie Policy</a></div> : null}
        </div>
        <div className="space-y-2">
          <div className="text-[10px] uppercase tracking-widest opacity-60">Unsubscribe</div>
          {done ? (
            <div className="text-[11px]" data-testid="footer-unsub-success">✓ You've been unsubscribed.</div>
          ) : (
            <form onSubmit={unsub} className="flex items-center gap-2">
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                data-testid="footer-unsub-email"
                className="flex-1 px-2 py-1.5 text-xs rounded"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", color: theme.fg }} />
              <button type="submit" disabled={busy}
                data-testid="footer-unsub-btn"
                className="text-[10px] uppercase tracking-widest px-3 py-1.5 rounded font-bold disabled:opacity-50"
                style={{ background: theme.accent, color: getContrastText(theme.accent, theme.bg) }}>
                {busy ? "…" : "Unsubscribe"}
              </button>
            </form>
          )}
        </div>
      </div>
      <div className="max-w-5xl mx-auto mt-8 pt-6 border-t flex flex-wrap items-center justify-between gap-2 text-[10px] opacity-60"
        style={{ borderColor: "rgba(255,255,255,0.06)" }}>
        <div>© {year} {p.brand || "PromoOS"}. All rights reserved.</div>
        <div>{p.copyright_extra || ""}</div>
      </div>
    </footer>
  );
}
