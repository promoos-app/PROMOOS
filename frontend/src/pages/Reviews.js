import { useEffect, useState } from "react";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { MessageSquareQuote, Plus, Star, Trash2, Check, X } from "lucide-react";

const EMPTY = { customer_name: "", role: "Verified buyer", quote: "", rating: 5, avatar_url: "", product_id: "", verified: true, approved: true };

function ReviewForm({ open, onOpenChange, initial, onSubmit, products }) {
  const [f, setF] = useState(initial || EMPTY);
  useEffect(() => { setF(initial || EMPTY); }, [initial, open]);
  const submit = async () => {
    if (!f.customer_name.trim() || !f.quote.trim()) { toast.error("Name and quote are required"); return; }
    await onSubmit(f);
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-lg" data-testid="review-form-dialog">
        <DialogHeader><DialogTitle>{initial?.id ? "Edit review" : "New review"}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div>
            <Label className="text-xs text-[#A1A1AA]">Customer name</Label>
            <Input data-testid="review-name-input" value={f.customer_name}
              onChange={(e) => setF({ ...f, customer_name: e.target.value })}
              className="mt-1 bg-[#0A0A0A] border-[#27272A]" placeholder="Aisha K." />
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Role / label (optional)</Label>
            <Input value={f.role || ""} onChange={(e) => setF({ ...f, role: e.target.value })}
              className="mt-1 bg-[#0A0A0A] border-[#27272A]" placeholder="Verified buyer" />
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Quote</Label>
            <textarea data-testid="review-quote-input" value={f.quote} rows={3}
              onChange={(e) => setF({ ...f, quote: e.target.value })}
              className="mt-1 w-full bg-[#0A0A0A] border border-[#27272A] rounded-md p-2 text-sm text-white"
              placeholder="Absolutely love this — arrived in 2 days." />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-[#A1A1AA]">Rating</Label>
              <select value={f.rating} onChange={(e) => setF({ ...f, rating: parseInt(e.target.value) })}
                className="mt-1 w-full h-10 bg-[#0A0A0A] border border-[#27272A] rounded-md px-2 text-sm text-white">
                {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{"★".repeat(n)} · {n}</option>)}
              </select>
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Product (optional)</Label>
              <select value={f.product_id || ""} onChange={(e) => setF({ ...f, product_id: e.target.value })}
                className="mt-1 w-full h-10 bg-[#0A0A0A] border border-[#27272A] rounded-md px-2 text-sm text-white">
                <option value="">— Any product —</option>
                {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Avatar URL (optional)</Label>
            <Input value={f.avatar_url || ""} onChange={(e) => setF({ ...f, avatar_url: e.target.value })}
              className="mt-1 bg-[#0A0A0A] border-[#27272A]" placeholder="https://..." />
          </div>
          <div className="flex items-center gap-4 text-sm">
            <label className="flex items-center gap-2"><input type="checkbox" checked={f.verified}
              onChange={(e) => setF({ ...f, verified: e.target.checked })} /> Verified purchase</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={f.approved}
              onChange={(e) => setF({ ...f, approved: e.target.checked })} /> Approved (public)</label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button data-testid="review-save-btn" className="btn-primary" onClick={submit}>Save review</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Reviews() {
  const [reviews, setReviews] = useState([]);
  const [products, setProducts] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);

  const load = async () => {
    try {
      const [r, p] = await Promise.all([api.get("/reviews"), api.get("/products")]);
      setReviews(r.data); setProducts(p.data);
    } catch (e) { toast.error(apiError(e)); }
  };
  useEffect(() => { load(); }, []);

  const save = async (f) => {
    try {
      if (editing?.id) await api.patch(`/reviews/${editing.id}`, f);
      else await api.post("/reviews", f);
      toast.success("Review saved");
      setOpen(false); setEditing(null); load();
    } catch (e) { toast.error(apiError(e)); }
  };
  const toggleApprove = async (r) => {
    try { await api.patch(`/reviews/${r.id}`, { approved: !r.approved }); load(); }
    catch (e) { toast.error(apiError(e)); }
  };
  const del = async (r) => {
    if (!window.confirm(`Delete review from ${r.customer_name}?`)) return;
    try { await api.delete(`/reviews/${r.id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(apiError(e)); }
  };

  const approvedCount = reviews.filter((r) => r.approved).length;

  return (
    <div className="space-y-6" data-testid="reviews-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-3">
            <MessageSquareQuote className="w-7 h-7 text-[#CCFF00]" /> Reviews
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-1">
            Curate verified customer quotes. Link them to any Storefront funnel testimonial block.
          </p>
        </div>
        <Button data-testid="reviews-new-btn" className="btn-primary gap-2 rounded-md"
          onClick={() => { setEditing(null); setOpen(true); }}>
          <Plus className="w-4 h-4" /> Add review
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg p-4 bg-[#141414] border border-[#27272A]">
          <div className="text-xs text-[#71717A] uppercase tracking-wider">Total</div>
          <div className="text-2xl font-bold mt-1">{reviews.length}</div>
        </div>
        <div className="rounded-lg p-4 bg-[#141414] border border-[#27272A]">
          <div className="text-xs text-[#71717A] uppercase tracking-wider">Approved</div>
          <div className="text-2xl font-bold mt-1 text-[#CCFF00]">{approvedCount}</div>
        </div>
        <div className="rounded-lg p-4 bg-[#141414] border border-[#27272A]">
          <div className="text-xs text-[#71717A] uppercase tracking-wider">Avg. rating</div>
          <div className="text-2xl font-bold mt-1">
            {reviews.length ? (reviews.reduce((s, r) => s + (r.rating || 5), 0) / reviews.length).toFixed(1) : "—"}
          </div>
        </div>
      </div>

      {reviews.length === 0 ? (
        <div className="text-center py-16 rounded-lg border border-dashed border-[#27272A]">
          <MessageSquareQuote className="w-10 h-10 mx-auto text-[#3F3F46] mb-3" />
          <div className="font-bold">No reviews yet</div>
          <div className="text-sm text-[#71717A] mt-1">Add your first customer quote to link into Storefront funnels.</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {reviews.map((r) => (
            <div key={r.id} className="rounded-lg p-4 bg-[#141414] border border-[#27272A]"
                 data-testid={`review-card-${r.id}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  {r.avatar_url ? (
                    <img src={r.avatar_url} alt={r.customer_name} className="w-9 h-9 rounded-full object-cover" />
                  ) : (
                    <div className="w-9 h-9 rounded-full bg-[#27272A] flex items-center justify-center text-xs font-bold">
                      {r.customer_name?.[0]?.toUpperCase()}
                    </div>
                  )}
                  <div>
                    <div className="font-bold text-sm">{r.customer_name}</div>
                    <div className="text-[10px] text-[#71717A]">{r.role || (r.verified ? "Verified buyer" : "")}</div>
                  </div>
                </div>
                <div className="flex items-center gap-1 text-xs">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star key={i} className={`w-3.5 h-3.5 ${i < (r.rating || 5) ? "text-[#CCFF00] fill-[#CCFF00]" : "text-[#3F3F46]"}`} />
                  ))}
                </div>
              </div>
              <p className="text-sm text-[#E4E4E7] mt-3 italic leading-relaxed">"{r.quote}"</p>
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#27272A]">
                <button data-testid={`review-toggle-approve-${r.id}`}
                  onClick={() => toggleApprove(r)}
                  className={`text-[10px] uppercase tracking-widest font-bold px-2 py-1 rounded flex items-center gap-1 ${
                    r.approved ? "text-[#CCFF00] bg-[#CCFF00]/10" : "text-[#71717A] bg-[#27272A]"
                  }`}>
                  {r.approved ? <><Check className="w-3 h-3" /> Approved</> : <><X className="w-3 h-3" /> Draft</>}
                </button>
                <div className="flex items-center gap-1">
                  <button onClick={() => { setEditing(r); setOpen(true); }}
                    className="text-xs text-[#A1A1AA] hover:text-white px-2 py-1">Edit</button>
                  <button data-testid={`review-delete-${r.id}`} onClick={() => del(r)}
                    className="text-xs text-[#EF4444] hover:text-red-300 p-1"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <ReviewForm open={open} onOpenChange={(v) => { setOpen(v); if (!v) setEditing(null); }}
        initial={editing} onSubmit={save} products={products} />
    </div>
  );
}
