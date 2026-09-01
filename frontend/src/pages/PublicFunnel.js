import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Countdown, ProductBlock, Testimonials, blockColors, trackFunnelEvent } from "./PublicFunnelBlocks";
import { LogoBar, Stats, Guarantee, PricingTable, OrderBump, Upsell, Optin, Spacer, Divider } from "./PublicFunnelIndustrial";
import { getContrastText } from "@/lib/contrast";

const API = process.env.REACT_APP_BACKEND_URL;

function Hero({ block, theme }) {
  const p = block.props || {};
  const c = blockColors(block, theme);
  return (
    <section id={block.anchor} className="py-24 px-6 text-center" data-testid="funnel-block-hero"
      style={c.bg ? { background: c.bg } : undefined}>
      {p.eyebrow ? <div className="text-[10px] tracking-[0.3em] uppercase font-bold mb-4" style={{ color: c.accent }}>{p.eyebrow}</div> : null}
      <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold max-w-3xl mx-auto leading-[1.1]" style={{ fontFamily: theme.font_display }}>{p.headline}</h1>
      {p.subline ? <p className="text-base opacity-75 max-w-xl mx-auto mt-6">{p.subline}</p> : null}
      {p.cta_label ? (
        <a href={p.cta_scroll_to ? `#${p.cta_scroll_to}` : "#"}
           data-testid="funnel-hero-cta"
           className="inline-block mt-8 px-8 py-3 font-bold rounded-full transition hover:scale-[1.03]"
           style={{ background: c.accent, color: getContrastText(c.accent, theme.bg) }}>{p.cta_label}</a>
      ) : null}
    </section>
  );
}

function CouponBlock({ block, theme, slug }) {
  const p = block.props || {};
  const c = p.coupon;
  const cc = blockColors(block, theme);
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    if (!c || !c.code) return;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(c.code);
      } else {
        // Fallback for insecure contexts / iframes without clipboard permission
        const ta = document.createElement("textarea");
        ta.value = c.code; ta.setAttribute("readonly", "");
        ta.style.position = "absolute"; ta.style.left = "-9999px";
        document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); } catch (e) { /* noop */ }
        document.body.removeChild(ta);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
      trackFunnelEvent(slug, "coupon_copy", { block_id: block.id, block_type: "coupon", meta: { code: c.code } });
    } catch (e) {
      // permission denied or other clipboard error — never crash the storefront
      setCopied(false);
    }
  };
  return (
    <section id={block.anchor} className="py-16 px-6" data-testid="funnel-block-coupon"
      style={cc.bg ? { background: cc.bg } : undefined}>
      <div className="max-w-md mx-auto rounded-2xl p-8 text-center relative overflow-hidden" style={{ background: "rgba(255,255,255,0.05)", border: `1px dashed ${cc.accent}` }}>
        <div className="text-[10px] tracking-[0.3em] uppercase font-bold mb-2" style={{ color: cc.accent }}>{p.label || "Your coupon"}</div>
        <div className="text-3xl font-bold mb-2" style={{ fontFamily: theme.font_display }}>{(c && (c.headline || c.name)) || "Special offer"}</div>
        {c && c.description ? <p className="text-sm opacity-75 mb-6">{c.description}</p> : null}
        {c && c.code ? (
          <div className="border-2 border-dashed rounded-lg p-4 my-4" style={{ borderColor: cc.accent }}>
            <div className="text-3xl font-mono font-bold tracking-widest">{c.code}</div>
            <button data-testid={`coupon-copy-${c.code}`} onClick={copy}
              className="text-[10px] mt-2 uppercase tracking-widest opacity-60 hover:opacity-100">
              {copied ? "✓ Copied" : "Tap to copy"}
            </button>
          </div>
        ) : (
          <div className="text-sm opacity-60">Coupon not yet attached.</div>
        )}
      </div>
    </section>
  );
}

function GiftCardBlock({ block, theme }) {
  const p = block.props || {};
  const t = p.template;
  if (!t) return <section className="py-16 px-6 text-center opacity-60">Gift card preview unavailable.</section>;
  const bg = { background: t.background.value };
  return (
    <section id={block.anchor} className="py-16 px-6" data-testid="funnel-block-giftcard">
      <div className="max-w-md mx-auto rounded-2xl overflow-hidden shadow-2xl" style={{ ...bg, color: t.text_color, fontFamily: t.font, aspectRatio: "1.6/1" }}>
        <div className="p-6 h-full flex flex-col justify-between">
          <div className="text-[10px] tracking-[0.3em] uppercase opacity-70" style={{ color: t.accent }}>Gift Card · ${p.amount} {p.currency}</div>
          <div>
            <div className="text-2xl font-bold">{t.headline}</div>
            <div className="text-sm opacity-80 mt-1">{t.subline}</div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Features({ block, theme }) {
  const p = block.props || {};
  return (
    <section className="py-16 px-6" data-testid="funnel-block-features">
      <div className="max-w-4xl mx-auto">
        {p.title ? <h2 className="text-3xl font-bold text-center mb-10" style={{ fontFamily: theme.font_display }}>{p.title}</h2> : null}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {(p.items || []).map((it, i) => (
            <div key={i}>
              <div className="text-lg font-bold mb-1" style={{ color: theme.accent }}>{it.title}</div>
              <div className="text-sm opacity-75">{it.text}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function LegacyTestimonial({ block, theme }) {
  const p = block.props || {};
  return (
    <section className="py-16 px-6 text-center" data-testid="funnel-block-testimonials">
      <div className="max-w-2xl mx-auto">
        <div className="text-2xl italic" style={{ fontFamily: theme.font_display }}>"{p.quote}"</div>
        <div className="text-xs uppercase tracking-widest mt-4 opacity-60">— {p.author}</div>
      </div>
    </section>
  );
}

function FAQ({ block }) {
  const p = block.props || {};
  return (
    <section className="py-16 px-6" data-testid="funnel-block-faq">
      <div className="max-w-2xl mx-auto space-y-4">
        {(p.items || []).map((it, i) => (
          <details key={i} className="border-b pb-3" style={{ borderColor: "rgba(255,255,255,0.15)" }}>
            <summary className="font-bold cursor-pointer">{it.q}</summary>
            <p className="text-sm opacity-75 mt-2">{it.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

function CTA({ block, theme }) {
  const p = block.props || {};
  return (
    <section className="py-20 px-6 text-center" data-testid="funnel-block-cta">
      <h2 className="text-3xl sm:text-4xl font-bold" style={{ fontFamily: theme.font_display }}>{p.headline}</h2>
      {p.cta_label ? (
        <a href={p.cta_scroll_to ? `#${p.cta_scroll_to}` : "#"} className="inline-block mt-6 px-8 py-3 font-bold rounded-full transition hover:scale-[1.03]"
           style={{ background: theme.accent, color: theme.bg }}>{p.cta_label}</a>
      ) : null}
    </section>
  );
}

function Heading({ block, theme }) {
  return <section className="py-8 px-6 text-center"><h2 className="text-3xl font-bold" style={{ fontFamily: theme.font_display }}>{block.props.text}</h2></section>;
}

function Paragraph({ block }) {
  return <section className="py-4 px-6"><p className="max-w-2xl mx-auto text-base opacity-80">{block.props.text}</p></section>;
}

function ImageBlock({ block }) {
  const p = block.props || {};
  return (
    <section className="py-8 px-6" data-testid="funnel-block-image">
      <div className="max-w-3xl mx-auto">
        {p.url ? <img src={p.url} alt={p.alt || ""} className="w-full rounded-lg" /> : null}
        {p.caption ? <div className="text-xs opacity-60 mt-2 text-center">{p.caption}</div> : null}
      </div>
    </section>
  );
}

function VideoBlock({ block }) {
  const p = block.props || {};
  if (!p.url) return null;
  const isEmbed = p.url.includes("youtube.com") || p.url.includes("youtu.be") || p.url.includes("vimeo.com");
  return (
    <section className="py-8 px-6" data-testid="funnel-block-video">
      <div className="max-w-3xl mx-auto rounded-lg overflow-hidden">
        {isEmbed ? (
          <iframe src={p.url.replace("watch?v=", "embed/")} className="w-full aspect-video" allowFullScreen title="video" />
        ) : (
          <video src={p.url} poster={p.poster_url} controls={!p.autoplay} autoPlay={p.autoplay} muted={p.autoplay} loop={p.autoplay} className="w-full" />
        )}
      </div>
    </section>
  );
}

function AudioBlock({ block }) {
  const p = block.props || {};
  return (
    <section className="py-8 px-6" data-testid="funnel-block-audio">
      <div className="max-w-2xl mx-auto text-center">
        {p.label ? <div className="text-sm mb-2 opacity-75">{p.label}</div> : null}
        {p.url ? <audio src={p.url} controls className="w-full" /> : null}
      </div>
    </section>
  );
}

function Row({ block, theme }) {
  const p = block.props || {};
  return (
    <section className="py-8 px-6" data-testid="funnel-block-row">
      <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
        {(p.columns || []).map((col, i) => (
          <div key={i}>{(col.blocks || []).map((b) => <Block key={b.id || Math.random()} block={b} theme={theme} />)}</div>
        ))}
      </div>
    </section>
  );
}

function TestimonialSwitch({ block, theme }) {
  const p = block.props || {};
  if (Array.isArray(p.items) && p.items.length > 0) return <Testimonials block={block} theme={theme} />;
  return <LegacyTestimonial block={block} theme={theme} />;
}

function CTAWithTrack({ block, theme, slug }) {
  const p = block.props || {};
  const c = blockColors(block, theme);
  const click = () => trackFunnelEvent(slug, "cta_click", { block_id: block.id, block_type: "cta" });
  return (
    <section className="py-20 px-6 text-center" data-testid="funnel-block-cta"
      style={c.bg ? { background: c.bg } : undefined}>
      <h2 className="text-3xl sm:text-4xl font-bold" style={{ fontFamily: theme.font_display }}>{p.headline}</h2>
      {p.cta_label ? (
        <a onClick={click} href={p.cta_scroll_to ? `#${p.cta_scroll_to}` : "#"} className="inline-block mt-6 px-8 py-3 font-bold rounded-full transition hover:scale-[1.03]"
           style={{ background: c.accent, color: getContrastText(c.accent, theme.bg) }}>{p.cta_label}</a>
      ) : null}
    </section>
  );
}

const REGISTRY = {
  hero: Hero,
  coupon: CouponBlock,
  giftcard: GiftCardBlock,
  features: Features,
  testimonial: TestimonialSwitch,
  faq: FAQ,
  cta: CTAWithTrack,
  heading: Heading,
  paragraph: Paragraph,
  image: ImageBlock,
  video: VideoBlock,
  audio: AudioBlock,
  countdown: Countdown,
  product: ProductBlock,
  row: Row,
  // industrial (systeme.io-style) blocks
  logo_bar: LogoBar,
  stats: Stats,
  guarantee: Guarantee,
  pricing_table: PricingTable,
  order_bump: OrderBump,
  upsell: Upsell,
  optin: Optin,
  spacer: Spacer,
  divider: Divider,
};

function Block({ block, theme, slug }) {
  const Comp = REGISTRY[block.type];
  if (!Comp) return null;
  return <Comp block={block} theme={theme} slug={slug} />;
}

export default function PublicFunnel() {
  const { slug } = useParams();
  const [funnel, setFunnel] = useState(null);
  const [err, setErr] = useState(null);
  const viewFired = useRef(false);
  useEffect(() => {
    axios.get(`${API}/api/public/f/${slug}`).then((r) => {
      setFunnel(r.data);
      if (!viewFired.current) {
        viewFired.current = true;
        trackFunnelEvent(slug, "view");
      }
    }).catch((e) => setErr((e && e.response && e.response.data && e.response.data.detail) || "Not found"));
  }, [slug]);

  if (err) return <div className="min-h-screen bg-black text-white flex items-center justify-center"><div className="text-center"><div className="font-bold text-2xl mb-2">Funnel not found</div><div className="text-sm opacity-60">{err}</div></div></div>;
  if (!funnel) return <div className="min-h-screen bg-black text-white flex items-center justify-center opacity-60">Loading…</div>;

  const theme = funnel.theme || {};
  return (
    <div style={{ background: theme.bg, color: theme.fg, fontFamily: theme.font_body, minHeight: "100vh" }} data-testid="public-funnel">
      <title>{funnel.seo?.title || funnel.name}</title>
      {funnel.blocks.map((b) => <Block key={b.id} block={b} theme={theme} slug={slug} />)}
      <footer className="py-8 text-center text-[10px] tracking-widest uppercase opacity-40">
        Powered by PromoOS
      </footer>
    </div>
  );
}
