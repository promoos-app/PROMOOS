import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export function BillingSuccess() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const [state, setState] = useState({ status: "polling", plan: null });

  useEffect(() => {
    const sid = sp.get("session_id");
    if (!sid) { setState({ status: "unknown" }); return; }
    let attempts = 0;
    const poll = async () => {
      try {
        const { data } = await api.get(`/billing/status/${sid}`);
        if (data.payment_status === "paid") {
          setState({ status: "paid", plan: data.lookup_key });
        } else if (attempts < 8) {
          attempts += 1; setTimeout(poll, 2000);
        } else {
          setState({ status: "pending" });
        }
      } catch { setState({ status: "error" }); }
    };
    poll();
  }, [sp]);

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white flex items-center justify-center px-6" data-testid="billing-success-page">
      <div className="max-w-md w-full text-center surface rounded-2xl p-10">
        {state.status === "paid" ? (
          <>
            <CheckCircle2 className="w-14 h-14 text-[#CCFF00] mx-auto mb-4" />
            <h1 className="font-display font-bold text-3xl mb-2">You're in!</h1>
            <p className="text-sm text-[#A1A1AA] mb-6">
              Your 3-day trial has started on the <span className="text-[#CCFF00] font-bold">{(state.plan || "").replace("_monthly", "").toUpperCase()}</span> plan.
              No card is charged until day 4.
            </p>
            <Button data-testid="go-dashboard-btn" onClick={() => nav("/")} className="btn-primary rounded-md w-full">
              Go to dashboard
            </Button>
          </>
        ) : state.status === "polling" ? (
          <>
            <Loader2 className="w-10 h-10 text-[#CCFF00] mx-auto mb-4 spin" />
            <h1 className="font-display font-bold text-2xl mb-2">Confirming your subscription…</h1>
            <p className="text-sm text-[#A1A1AA]">This usually takes a few seconds.</p>
          </>
        ) : (
          <>
            <XCircle className="w-14 h-14 text-orange-400 mx-auto mb-4" />
            <h1 className="font-display font-bold text-2xl mb-2">Still processing</h1>
            <p className="text-sm text-[#A1A1AA] mb-6">
              Stripe is finalizing your trial. Refresh in a minute or check your email for a confirmation.
            </p>
            <Button onClick={() => nav("/pricing")} className="btn-ghost rounded-md w-full">Back to pricing</Button>
          </>
        )}
      </div>
    </div>
  );
}

export function BillingCancel() {
  const nav = useNavigate();
  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white flex items-center justify-center px-6" data-testid="billing-cancel-page">
      <div className="max-w-md w-full text-center surface rounded-2xl p-10">
        <XCircle className="w-14 h-14 text-[#71717A] mx-auto mb-4" />
        <h1 className="font-display font-bold text-3xl mb-2">Checkout cancelled</h1>
        <p className="text-sm text-[#A1A1AA] mb-6">No worries — you weren't charged. Come back whenever you're ready.</p>
        <Button data-testid="back-to-pricing-btn" onClick={() => nav("/pricing")} className="btn-primary rounded-md w-full">
          View plans again
        </Button>
      </div>
    </div>
  );
}
