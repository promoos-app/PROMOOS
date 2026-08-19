import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import Footer from "@/components/Footer";
import {
  Sparkles, Ticket, Bot, Wand2, Gift, Rocket, QrCode, Wifi, ShieldCheck,
  Palette, Layers, ArrowRight, Check, Zap, TrendingUp, Globe, Wallet as WalletIcon, Store,
} from "lucide-react";

const FEATURES = [
  { icon: Ticket, title: "23 coupon types, one rule builder",
    text: "Percentage, BOGO, cart tiers, first-time, referral loops, loyalty rewards, gift cards, VIP tiers — all designed with a single visual builder." },
  { icon: Bot, title: "AI Copilot writes every campaign",
    text: "Claude sonnet + Gemini nano-banana generate on-brand copy, subject lines and coupon graphics — regenerate any field with one click." },
  { icon: Palette, title: "20 luxury gift-card templates",
    text: "Diamond, Champagne, Noir, Emerald… full editor for text, colors, backgrounds and logo overlay. AI regenerates every field on demand." },
  { icon: Rocket, title: "Drag-drop funnel builder",
    text: "Six luxury templates. Drop coupon and gift-card blocks anywhere. Publish to your own domain with automatic Cloudflare-for-SaaS SSL." },
  { icon: QrCode, title: "Colorful QR codes + print sheets",
    text: "URLs, phone, WiFi, vCards. Ten designer presets, logo overlay, tracked scans with dedup, and A4/Letter PDF grids for print." },
  { icon: Store, title: "Shopify + WooCommerce ready",
    text: "Copy-paste webhook installers. Every order fires PromoOS, redemptions log, revenue attributes. HMAC-verified for production." },
  { icon: WalletIcon, title: "Loyalty, referrals, gift cards",
    text: "Points, tiers, VIP unlocks, viral referral loops, physical + digital gift cards with balances. All out of the box." },
  { icon: Globe, title: "145 currencies, 100+ payment methods",
    text: "Stripe (cards, Apple/Google Pay, SEPA, iDEAL, Klarna, Alipay, WeChat), plus PayPal, Razorpay for India, Paystack for Africa." },
];

const HOW_IT_WORKS = [
  { step: "01", title: "Sign up in 30 seconds", text: "3-day free trial. No credit card until day 4." },
  { step: "02", title: "Design your first coupon", text: "Pick a type, let AI Copilot write it, publish to a public URL." },
  { step: "03", title: "Send it everywhere", text: "Embed on your site, share to socials, DM by SMS/WhatsApp, or post to Facebook/Instagram/LinkedIn." },
  { step: "04", title: "Watch redemptions roll in", text: "Real-time analytics, CAC/CLV, revenue attribution — from every channel." },
];

export default function Landing() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [plans, setPlans] = useState([]);

  useEffect(() => {
    if (user) nav("/dashboard", { replace: true });
    api.get("/billing/plans").then((r) => setPlans(r.data.plans)).catch(() => {});
  }, [user, nav]);

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white grain overflow-x-hidden" data-testid="landing-page">
      {/* Nav */}
      <nav className="border-b border-[#27272A]/50 backdrop-blur-lg bg-[#0A0A0A]/80 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" data-testid="nav-brand">
            <div className="w-8 h-8 rounded-md bg-[#CCFF00] flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-[#0A0A0A]" />
            </div>
            <span className="font-display font-extrabold text-lg">PromoOS</span>
          </Link>
          <div className="flex items-center gap-1 md:gap-3 text-sm">
            <a href="#features" className="hidden md:inline text-[#A1A1AA] hover:text-white px-3 py-1.5" data-testid="nav-features">Features</a>
            <Link to="/pricing" className="hidden md:inline text-[#A1A1AA] hover:text-white px-3 py-1.5" data-testid="nav-pricing">Pricing</Link>
            <Link to="/login" className="text-[#A1A1AA] hover:text-white px-3 py-1.5" data-testid="nav-login">Sign in</Link>
            <Link to="/login" data-testid="nav-cta">
              <Button className="btn-primary rounded-md text-xs gap-1">Start free trial <ArrowRight className="w-3 h-3" /></Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative">
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-[#005CEE] opacity-15 blur-[140px]" />
          <div className="absolute top-40 right-10 w-[400px] h-[400px] rounded-full bg-[#CCFF00] opacity-10 blur-[120px]" />
        </div>
        <div className="max-w-5xl mx-auto px-6 pt-24 pb-32 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#CCFF00]/30 bg-[#CCFF00]/5 text-[10px] uppercase tracking-[0.25em] text-[#CCFF00] font-bold mb-8" data-testid="hero-badge">
            <Sparkles className="w-3 h-3" /> The Promotional Operating System
          </div>
          <h1 className="font-display font-extrabold text-5xl sm:text-6xl lg:text-7xl leading-[0.95] tracking-tight mb-6">
            Every coupon. Every channel.<br />
            <span className="text-[#CCFF00]">One command center.</span>
          </h1>
          <p className="text-lg sm:text-xl text-[#A1A1AA] max-w-2xl mx-auto leading-relaxed mb-10">
            Design coupons, gift cards, funnels and loyalty campaigns with AI Copilot. Publish to your site, socials and POS in minutes.
            Track redemptions, revenue and lifetime value from one dashboard.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap" data-testid="hero-ctas">
            <Link to="/login">
              <Button data-testid="hero-cta-primary" className="btn-primary rounded-full h-12 px-7 gap-2 text-base">
                Start 3-day free trial <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
            <a href="#features">
              <Button data-testid="hero-cta-secondary" className="btn-ghost rounded-full h-12 px-7 text-base">
                See what's inside
              </Button>
            </a>
          </div>
          <div className="mt-10 flex items-center justify-center gap-6 text-xs text-[#71717A] flex-wrap">
            <span className="flex items-center gap-1"><Check className="w-3 h-3 text-[#CCFF00]" /> No credit card for trial</span>
            <span className="flex items-center gap-1"><Check className="w-3 h-3 text-[#CCFF00]" /> Cancel anytime</span>
            <span className="flex items-center gap-1"><Check className="w-3 h-3 text-[#CCFF00]" /> Basic $49 · Pro $79</span>
          </div>
        </div>
      </section>

      {/* Trust bar */}
      <section className="border-y border-[#27272A]">
        <div className="max-w-6xl mx-auto px-6 py-8 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { n: "53", l: "product modules" },
            { n: "23", l: "coupon types" },
            { n: "145", l: "currencies" },
            { n: "100+", l: "payment methods" },
          ].map((s) => (
            <div key={s.l}>
              <div className="font-display font-extrabold text-3xl text-[#CCFF00]">{s.n}</div>
              <div className="text-[10px] uppercase tracking-widest text-[#71717A] mt-1">{s.l}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-6 py-24">
        <div className="max-w-2xl mb-14">
          <div className="text-[10px] uppercase tracking-[0.3em] text-[#CCFF00] font-bold mb-3">Every promotion, one system</div>
          <h2 className="font-display font-bold text-4xl lg:text-5xl leading-[1.05] mb-4">
            Built for merchants who ship promotions weekly.
          </h2>
          <p className="text-[#A1A1AA] text-lg">
            Stop stitching Mailchimp, Canva, a coupon plugin, a QR generator and three spreadsheets together. PromoOS ships them as one.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="features-grid">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div key={f.title} className="surface rounded-lg p-5 hover:border-[#CCFF00]/30 transition group" data-testid={`feature-${f.title.split(" ")[0].toLowerCase()}`}>
                <Icon className="w-6 h-6 text-[#CCFF00] mb-3 group-hover:scale-110 transition" />
                <div className="font-display font-bold text-base mb-1.5">{f.title}</div>
                <div className="text-xs text-[#A1A1AA] leading-relaxed">{f.text}</div>
              </div>
            );
          })}
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-[#27272A] bg-[#0F0F0F]">
        <div className="max-w-5xl mx-auto px-6 py-24">
          <div className="text-center mb-14">
            <div className="text-[10px] uppercase tracking-[0.3em] text-[#CCFF00] font-bold mb-3">Zero to first sale</div>
            <h2 className="font-display font-bold text-4xl lg:text-5xl">In under 10 minutes.</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {HOW_IT_WORKS.map((s, i) => (
              <div key={s.step} className="relative">
                <div className="font-display font-black text-6xl text-[#27272A] mb-2 leading-none">{s.step}</div>
                <div className="font-display font-bold text-lg mb-1">{s.title}</div>
                <div className="text-xs text-[#A1A1AA] leading-relaxed">{s.text}</div>
                {i < HOW_IT_WORKS.length - 1 && <div className="hidden md:block absolute top-4 -right-3 text-[#3f3f46]">→</div>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing summary */}
      <section className="max-w-4xl mx-auto px-6 py-24 text-center">
        <div className="text-[10px] uppercase tracking-[0.3em] text-[#CCFF00] font-bold mb-3">Simple pricing</div>
        <h2 className="font-display font-bold text-4xl lg:text-5xl mb-4">Unlimited everything. 3 days free.</h2>
        <p className="text-[#A1A1AA] mb-10">Cancel anytime. No card charged until your trial ends.</p>
        {plans.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto" data-testid="landing-plans">
            {plans.map((p, i) => (
              <div key={p.lookup_key}
                className={`surface rounded-2xl p-6 text-left ${i === 1 ? "border-[#CCFF00]/40 bg-gradient-to-b from-[#141414] to-[#0A0A0A]" : ""}`}
                data-testid={`landing-plan-${p.lookup_key}`}>
                <div className="text-xs uppercase tracking-widest text-[#71717A] mb-2">{p.name}</div>
                <div className="flex items-baseline gap-1 mb-4">
                  <span className="text-4xl font-display font-bold">${p.price}</span>
                  <span className="text-sm text-[#A1A1AA]">/mo</span>
                </div>
                <div className="text-xs text-[#CCFF00] mb-4">{p.trial_days}-day free trial</div>
                <ul className="space-y-1.5 mb-6">
                  {p.features.slice(0, 4).map((f) => (
                    <li key={f} className="flex items-start gap-1.5 text-xs text-[#A1A1AA]">
                      <Check className="w-3 h-3 text-[#CCFF00] shrink-0 mt-0.5" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <Link to="/login" data-testid={`landing-cta-${p.lookup_key}`}>
                  <Button className={`rounded-md w-full ${i === 1 ? "btn-primary" : "btn-ghost"}`}>
                    Start {p.trial_days}-day trial
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        )}
        <Link to="/pricing" className="mt-8 inline-block text-xs text-[#71717A] hover:text-white" data-testid="landing-full-pricing">
          See full pricing details →
        </Link>
      </section>

      {/* Final CTA */}
      <section className="border-t border-[#27272A]">
        <div className="max-w-3xl mx-auto px-6 py-24 text-center">
          <h2 className="font-display font-bold text-4xl lg:text-5xl mb-6 leading-[1.1]">
            Your next campaign shouldn't need <span className="text-[#CCFF00]">five tools.</span>
          </h2>
          <p className="text-[#A1A1AA] text-lg mb-10 max-w-xl mx-auto">
            Try PromoOS free for 3 days. If it doesn't save you a week of work, don't pay.
          </p>
          <Link to="/login" data-testid="final-cta">
            <Button className="btn-primary rounded-full h-12 px-8 text-base gap-2">
              Start free trial <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </div>
      </section>

      <div className="max-w-6xl mx-auto px-6"><Footer /></div>
    </div>
  );
}
