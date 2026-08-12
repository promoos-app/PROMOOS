import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Gift, CreditCard, Star, Ticket, Sparkles, Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Wallet() {
  const { token } = useParams();
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    axios.get(`${API}/public/wallet/${encodeURIComponent(token)}`)
      .then((r) => setD(r.data))
      .catch(() => setErr("We couldn't find your wallet."));
  }, [token]);

  if (err) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] text-white flex items-center justify-center p-6" data-testid="wallet-empty">
        <div className="text-center">
          <div className="text-2xl font-bold mb-2">Nothing here yet</div>
          <div className="text-[#A1A1AA]">{err}</div>
        </div>
      </div>
    );
  }
  if (!d) {
    return <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center"><Loader2 className="w-6 h-6 text-white spin" /></div>;
  }

  const totalGC = (d.gift_cards || []).reduce((s, c) => s + (c.balance || 0), 0);

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white px-4 py-10" data-testid="wallet-page"
         style={{ backgroundImage: "radial-gradient(1200px 400px at 50% -100px, #005CEE22, transparent)" }}>
      <div className="max-w-[720px] mx-auto">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 text-[11px] tracking-[0.14em] uppercase font-bold px-3 py-1 rounded-full bg-[#CCFF00] text-[#0A0A0A]">
            <Sparkles className="w-3.5 h-3.5" /> {d.workspace_name || "Your Wallet"}
          </div>
          <h1 className="font-display font-bold text-4xl mt-4" data-testid="wallet-customer">Hi {d.customer.split("@")[0]}</h1>
          <p className="text-sm text-[#A1A1AA] mt-1">Everything you've unlocked — in one place.</p>
        </div>

        <div className="grid grid-cols-3 gap-3 mb-8">
          <div className="rounded-lg bg-[#141416] border border-[#27272A] p-4 text-center">
            <Gift className="w-4 h-4 text-[#CCFF00] mx-auto mb-1" />
            <div className="text-2xl font-bold">${totalGC.toFixed(0)}</div>
            <div className="text-[10px] uppercase tracking-widest text-[#71717A]">Gift cards</div>
          </div>
          <div className="rounded-lg bg-[#141416] border border-[#27272A] p-4 text-center">
            <CreditCard className="w-4 h-4 text-[#CCFF00] mx-auto mb-1" />
            <div className="text-2xl font-bold">${Number(d.store_credits_total || 0).toFixed(0)}</div>
            <div className="text-[10px] uppercase tracking-widest text-[#71717A]">Store credit</div>
          </div>
          <div className="rounded-lg bg-[#141416] border border-[#27272A] p-4 text-center">
            <Star className="w-4 h-4 text-[#CCFF00] mx-auto mb-1" />
            <div className="text-2xl font-bold">{Math.round(d.loyalty?.points || 0)}</div>
            <div className="text-[10px] uppercase tracking-widest text-[#71717A]">Points · {d.loyalty?.tier || "—"}</div>
          </div>
        </div>

        {d.gift_cards?.length > 0 && (
          <section className="mb-8">
            <h2 className="font-display font-bold mb-3">Your gift cards</h2>
            <div className="space-y-2">
              {d.gift_cards.map((g) => (
                <div key={g.code} data-testid={`wallet-gc-${g.code}`} className="rounded-lg border border-[#27272A] bg-[#141416] p-4 flex items-center justify-between">
                  <div>
                    <div className="font-mono text-sm">{g.code}</div>
                    <div className="text-xs text-[#71717A] mt-0.5">Originally ${g.amount.toFixed(0)} · {g.state}</div>
                  </div>
                  <div className="text-2xl font-bold text-[#CCFF00]">${g.balance.toFixed(2)}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {d.recent_redemptions?.length > 0 && (
          <section>
            <h2 className="font-display font-bold mb-3 flex items-center gap-2"><Ticket className="w-4 h-4" /> Recent redemptions</h2>
            <div className="space-y-2">
              {d.recent_redemptions.map((r, i) => (
                <div key={i} className="rounded-lg border border-[#27272A] bg-[#141416] p-3 flex items-center justify-between">
                  <div className="font-mono text-xs">{r.code}</div>
                  <div className="text-xs text-[#71717A]">{(r.created_at || "").slice(0, 10)}</div>
                  <div className="text-sm font-bold text-emerald-400">-${Number(r.discount).toFixed(2)}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {(!d.gift_cards?.length && !d.recent_redemptions?.length && !d.loyalty && !d.store_credits_total) && (
          <div className="text-center text-[#71717A] py-10">Your wallet is empty for now — every coupon you redeem, gift card you receive, and point you earn will show up here.</div>
        )}
      </div>
    </div>
  );
}
