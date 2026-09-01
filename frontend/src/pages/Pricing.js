import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { apiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Check, Loader2, Sparkles } from "lucide-react";
import Footer from "@/components/Footer";

export default function Pricing() {
  const nav = useNavigate();
  const { user } = useAuth();
  const [plans, setPlans] = useState([]);
  const [providers, setProviders] = useState([]);
  const [busy, setBusy] = useState(null);
  const [sub, setSub] = useState(null);
  const [provider, setProvider] = useState("stripe");

  useEffect(() => {
    api.get("/billing/plans").then((r) => setPlans(r.data.plans)).catch(() => {});
    api.get("/billing/providers").then((r) => setProviders(r.data.providers)).catch(() => {});
    if (user) api.get("/billing/subscription").then((r) => setSub(r.data)).catch(() => {});
  }, [user]);

  const subscribe = async (plan) => {
    const lookup_key = plan.lookup_key;
    // Hosted Stripe Payment Link — instant checkout, no server-side wiring needed.
    // For Stripe provider we prefer this so merchants can pay in one click.
    if (provider === "stripe" && plan.payment_link) {
      // preserve the app's origin as the return URL via query params so Stripe returns here
      const client_reference = user ? user.workspace_id : "";
      const email = user ? user.email : "";
      const url = new URL(plan.payment_link);
      if (client_reference) url.searchParams.set("client_reference_id", client_reference);
      if (email) url.searchParams.set("prefilled_email", email);
      window.location.href = url.toString();
      return;
    }
    if (!user) { nav("/login?next=/pricing"); return; }
    setBusy(lookup_key);
    try {
      let data;
      if (provider === "stripe") {
        ({ data } = await api.post("/billing/checkout", {
          lookup_key, origin_url: window.location.origin,
        }));
      } else {
        ({ data } = await api.post("/billing/alt-checkout", {
          provider, lookup_key, origin_url: window.location.origin,
        }));
      }
      window.location.href = data.checkout_url;
    } catch (e) {
      toast.error(apiError(e));
      setBusy(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white" data-testid="pricing-page">
      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-[#CCFF00] font-bold mb-3">
            <Sparkles className="w-3 h-3" /> Simple, transparent pricing
          </div>
          <h1 className="font-display font-bold text-4xl sm:text-5xl lg:text-6xl tracking-tight mb-4">
            Everything unlimited. <span className="text-[#CCFF00]">3 days free.</span>
          </h1>
          <p className="text-base text-[#A1A1AA] max-w-xl mx-auto">
            Cancel anytime. No card charged until your trial ends.
          </p>
        </div>

        {sub?.status === "active" && (
          <div className="mb-6 text-center text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-md py-2" data-testid="active-plan-banner">
            You are on <span className="font-bold">{sub.plan}</span>.
          </div>
        )}

        {providers.length > 0 && (
          <div className="flex flex-wrap items-center justify-center gap-2 mb-8" data-testid="payment-provider-selector">
            <span className="text-xs uppercase tracking-widest text-[#71717A] mr-2">Pay with</span>
            {providers.map((p) => (
              <button key={p.id} onClick={() => p.configured && setProvider(p.id)}
                data-testid={`provider-${p.id}`}
                disabled={!p.configured}
                title={p.configured ? p.note : `Not configured — ${(p.env_needed || []).join(", ")}`}
                className={`px-3 py-1.5 rounded-md text-xs uppercase tracking-widest border ${provider === p.id ? "bg-[#CCFF00] text-[#0A0A0A] border-[#CCFF00] font-bold" : p.configured ? "border-[#27272A] text-white hover:border-[#CCFF00]/50" : "border-[#27272A] text-[#52525B] cursor-not-allowed"}`}>
                {p.label}{!p.configured && " (setup)"}
              </button>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {plans.map((p, i) => (
            <div key={p.lookup_key} data-testid={`plan-${p.lookup_key}`}
                 className={`surface rounded-2xl p-8 relative ${i === 1 ? "border-[#CCFF00]/40 bg-gradient-to-b from-[#141414] to-[#0A0A0A]" : ""}`}>
              {i === 1 && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#CCFF00] text-[#0A0A0A] text-[10px] uppercase tracking-widest font-bold px-3 py-1 rounded-full">
                  Most popular
                </div>
              )}
              <div className="text-xs uppercase tracking-widest text-[#71717A] mb-2">{p.name}</div>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-5xl font-display font-bold">${p.price}</span>
                <span className="text-sm text-[#A1A1AA]">/month</span>
              </div>
              <div className="text-xs text-[#CCFF00] mb-6">{p.trial_days}-day free trial · cancel anytime</div>
              <ul className="space-y-2.5 mb-8">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <Check className="w-4 h-4 text-[#CCFF00] shrink-0 mt-0.5" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <Button data-testid={`subscribe-${p.lookup_key}`}
                      onClick={() => subscribe(p)}
                      disabled={busy === p.lookup_key}
                      className={`w-full rounded-md gap-2 ${i === 1 ? "btn-primary" : "btn-ghost"}`}>
                {busy === p.lookup_key && <Loader2 className="w-4 h-4 spin" />}
                {provider === "stripe" && p.payment_link ? `Subscribe · $${p.price}/mo` : `Start ${p.trial_days}-day trial`}
              </Button>
            </div>
          ))}
        </div>

        <p className="text-center text-xs text-[#71717A] mt-10 max-w-lg mx-auto">
          Payments processed by Stripe. 100+ payment methods supported globally — cards, Apple Pay, Google Pay,
          SEPA, iDEAL, Klarna, Afterpay, Alipay, WeChat Pay, and more.
        </p>
      </div>
      <div className="max-w-6xl mx-auto px-6"><Footer /></div>
    </div>
  );
}
