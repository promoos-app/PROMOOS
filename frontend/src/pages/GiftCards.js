import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Gift, Loader2, Plus, DollarSign, CreditCard, Copy, Palette } from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";

const REASONS = [
  { v: "customer_appreciation", label: "Customer appreciation" },
  { v: "promotional", label: "Promotional" },
  { v: "refund", label: "Refund" },
  { v: "referral", label: "Referral reward" },
  { v: "loyalty", label: "Loyalty reward" },
];

function Stat({ label, value, icon: Icon }) {
  return (
    <div className="surface rounded-lg p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs uppercase tracking-wide text-[#71717A]">{label}</span>
        <Icon className="w-4 h-4 text-[#71717A]" />
      </div>
      <div className="font-display font-bold text-3xl">${Number(value || 0).toFixed(0)}</div>
    </div>
  );
}

function IssueGiftCardDialog({ onIssued }) {
  const [open, setOpen] = useState(false);
  const [amount, setAmount] = useState(50);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  const [sendEmail, setSendEmail] = useState(true);
  const [busy, setBusy] = useState(false);

  const issue = async () => {
    if (!email) { toast.error("Recipient email is required"); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/gift-cards", {
        amount: Number(amount), recipient_email: email, recipient_name: name,
        message, send_email: sendEmail,
      });
      toast.success(`Gift card issued · ${data.code}`);
      setOpen(false); setEmail(""); setName(""); setMessage("");
      onIssued?.();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button data-testid="gc-issue-btn" className="btn-primary rounded-md gap-2">
          <Plus className="w-4 h-4" /> Issue gift card
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#141414] border-[#27272A] text-white">
        <DialogHeader><DialogTitle>New gift card</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-[#A1A1AA]">Amount ($)</Label>
              <Input data-testid="gc-amount" type="number" min={1} value={amount} onChange={(e) => setAmount(e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A]" />
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Recipient email</Label>
              <Input data-testid="gc-email" value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A]" />
            </div>
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Recipient name (optional)</Label>
            <Input data-testid="gc-name" value={name} onChange={(e) => setName(e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A]" />
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Personal message</Label>
            <textarea data-testid="gc-message" rows={2} value={message} onChange={(e) => setMessage(e.target.value)} className="mt-1 w-full bg-[#0A0A0A] border border-[#27272A] rounded-md p-2 text-sm" placeholder="Happy birthday!" />
          </div>
          <div className="flex items-center justify-between p-3 rounded-md bg-[#0A0A0A] border border-[#27272A]">
            <div>
              <div className="text-sm font-medium">Deliver by email</div>
              <div className="text-xs text-[#71717A]">Sends the branded gift card via Resend (needs API key).</div>
            </div>
            <Switch data-testid="gc-send-email" checked={sendEmail} onCheckedChange={setSendEmail} />
          </div>
        </div>
        <DialogFooter>
          <Button data-testid="gc-issue-submit" onClick={issue} disabled={busy} className="btn-primary rounded-md gap-2">
            {busy && <Loader2 className="w-4 h-4 spin" />} Issue gift card
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function IssueCreditDialog({ onIssued }) {
  const [open, setOpen] = useState(false);
  const [customer, setCustomer] = useState("");
  const [amount, setAmount] = useState(20);
  const [reason, setReason] = useState("customer_appreciation");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const issue = async () => {
    if (!customer) { toast.error("Customer id/email required"); return; }
    setBusy(true);
    try {
      await api.post("/store-credits", { customer, amount: Number(amount), reason, note });
      toast.success("Store credit issued");
      setOpen(false); setCustomer(""); setNote("");
      onIssued?.();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button data-testid="sc-issue-btn" className="btn-ghost rounded-md gap-2">
          <CreditCard className="w-4 h-4" /> Issue store credit
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#141414] border-[#27272A] text-white">
        <DialogHeader><DialogTitle>Store credit</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div>
            <Label className="text-xs text-[#A1A1AA]">Customer (email or id)</Label>
            <Input data-testid="sc-customer" value={customer} onChange={(e) => setCustomer(e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A]" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-[#A1A1AA]">Amount ($)</Label>
              <Input data-testid="sc-amount" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A]" />
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Reason</Label>
              <select data-testid="sc-reason" value={reason} onChange={(e) => setReason(e.target.value)} className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm">
                {REASONS.map((r) => <option key={r.v} value={r.v}>{r.label}</option>)}
              </select>
            </div>
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Note</Label>
            <Input data-testid="sc-note" value={note} onChange={(e) => setNote(e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A]" />
          </div>
        </div>
        <DialogFooter>
          <Button data-testid="sc-issue-submit" onClick={issue} disabled={busy} className="btn-primary rounded-md gap-2">
            {busy && <Loader2 className="w-4 h-4 spin" />} Issue credit
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function GiftCards() {
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [credits, setCredits] = useState(null);
  const load = () => {
    api.get("/gift-cards").then((r) => setData(r.data)).catch((e) => toast.error(apiError(e)));
    api.get("/store-credits").then((r) => setCredits(r.data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  if (!data) return <div className="text-[#71717A]">Loading…</div>;

  return (
    <div className="fade-up max-w-[1300px]" data-testid="giftcards-page">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-2">
            <Gift className="w-7 h-7 text-[#CCFF00]" /> Gift Cards & Store Credit
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-1">Issue, track and redeem gift cards; award store credit for appreciation, refunds or loyalty.</p>
        </div>
        <div className="flex gap-2">
          <Button data-testid="gc-studio-btn" onClick={() => nav("/gift-cards/studio")} className="btn-ghost rounded-md gap-2">
            <Palette className="w-4 h-4" /> Design gallery
          </Button>
          <IssueCreditDialog onIssued={load} />
          <IssueGiftCardDialog onIssued={load} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6">
        <Stat label="GC Issued" value={data.total_issued} icon={Gift} />
        <Stat label="GC Outstanding" value={data.outstanding} icon={DollarSign} />
        <Stat label="GC Redeemed" value={data.redeemed} icon={CreditCard} />
        <Stat label="Store Credit Out" value={credits?.total_outstanding || 0} icon={DollarSign} />
      </div>

      <div className="surface rounded-lg overflow-hidden">
        <div className="p-6 pb-2">
          <h3 className="font-display font-bold text-lg">All gift cards</h3>
        </div>
        {data.cards.length === 0 ? (
          <div className="px-6 pb-6 text-sm text-[#71717A]">No gift cards issued yet.</div>
        ) : (
          <table className="w-full text-sm" data-testid="gc-table">
            <thead className="bg-[#0A0A0A] text-[#71717A] text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-6 py-2">Code</th>
                <th className="text-left px-3 py-2">Recipient</th>
                <th className="text-right px-3 py-2">Amount</th>
                <th className="text-right px-3 py-2">Balance</th>
                <th className="text-left px-3 py-2">State</th>
                <th className="text-right px-6 py-2">Issued</th>
              </tr>
            </thead>
            <tbody>
              {data.cards.map((c) => (
                <tr key={c.id} className="border-t border-[#27272A]" data-testid={`gc-row-${c.code}`}>
                  <td className="px-6 py-2 font-mono text-xs">
                    <button className="hover:text-white flex items-center gap-1" onClick={() => { navigator.clipboard.writeText(c.code).catch(() => {}); toast.success("Copied"); }}>
                      {c.code} <Copy className="w-3 h-3 text-[#71717A]" />
                    </button>
                  </td>
                  <td className="px-3 py-2 text-[#A1A1AA]">{c.recipient_email}</td>
                  <td className="px-3 py-2 text-right">${Number(c.amount).toFixed(0)}</td>
                  <td className="px-3 py-2 text-right font-bold text-[#CCFF00]">${Number(c.balance).toFixed(2)}</td>
                  <td className="px-3 py-2"><span className="text-xs uppercase px-2 py-0.5 rounded bg-[#27272A]">{c.state}</span></td>
                  <td className="px-6 py-2 text-right text-xs text-[#71717A]">{(c.created_at || "").slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {credits?.credits?.length > 0 && (
        <div className="surface rounded-lg overflow-hidden mt-6">
          <div className="p-6 pb-2">
            <h3 className="font-display font-bold text-lg">Recent store credits</h3>
          </div>
          <table className="w-full text-sm" data-testid="sc-table">
            <thead className="bg-[#0A0A0A] text-[#71717A] text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-6 py-2">Customer</th>
                <th className="text-right px-3 py-2">Balance</th>
                <th className="text-left px-3 py-2">Reason</th>
                <th className="text-left px-6 py-2">Note</th>
              </tr>
            </thead>
            <tbody>
              {credits.credits.map((c) => (
                <tr key={c.id} className="border-t border-[#27272A]" data-testid={`sc-row-${c.id}`}>
                  <td className="px-6 py-2 font-mono text-xs">{c.customer}</td>
                  <td className="px-3 py-2 text-right font-bold text-[#CCFF00]">${Number(c.balance).toFixed(2)}</td>
                  <td className="px-3 py-2 text-xs">{c.reason}</td>
                  <td className="px-6 py-2 text-xs text-[#A1A1AA]">{c.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
