import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Mail, Plus, Users, FileText, Loader2, ExternalLink } from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";

export default function Newsletters() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [color, setColor] = useState("#005CEE");
  const [busy, setBusy] = useState(false);

  const { data: pubs = [], isLoading } = useQuery({
    queryKey: ["publications"],
    queryFn: async () => (await api.get("/newsletter/publications")).data,
  });

  const create = async () => {
    if (!name.trim()) { toast.error("Give your newsletter a name"); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/newsletter/publications",
        { name, description, primary_color: color });
      toast.success("Newsletter created");
      qc.invalidateQueries({ queryKey: ["publications"] });
      setOpen(false); setName(""); setDescription("");
      navigate(`/newsletters/${data.id}`);
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <div className="fade-up max-w-[1200px]" data-testid="newsletters-page">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-2">
            <Mail className="w-7 h-7 text-[#CCFF00]" /> Newsletters
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-1">
            Publications, subscribers, referrals — with your coupons and gift cards embedded natively.
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="new-publication-btn" className="btn-primary rounded-md gap-2">
              <Plus className="w-4 h-4" /> New newsletter
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#141414] border-[#27272A] text-white" data-testid="new-publication-dialog">
            <DialogHeader><DialogTitle>Create a newsletter</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <div><Label className="text-xs text-[#A1A1AA]">Name</Label>
                <Input data-testid="pub-name-input" value={name} onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Acme Weekly"
                  className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
              <div><Label className="text-xs text-[#A1A1AA]">Description</Label>
                <Textarea data-testid="pub-desc-input" value={description} onChange={(e) => setDescription(e.target.value)}
                  rows={2} placeholder="Deals + drops from Acme Swimwear"
                  className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
              <div><Label className="text-xs text-[#A1A1AA]">Brand color</Label>
                <div className="flex gap-2 mt-1">
                  <Input type="color" value={color} onChange={(e) => setColor(e.target.value)}
                    className="w-14 h-10 p-1 bg-[#0A0A0A] border-[#27272A]"
                    data-testid="pub-color-input" />
                  <Input value={color} onChange={(e) => setColor(e.target.value)}
                    className="flex-1 bg-[#0A0A0A] border-[#27272A] text-white font-mono text-xs" />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button data-testid="pub-create-submit" onClick={create} disabled={busy}
                className="btn-primary rounded-md gap-2">
                {busy && <Loader2 className="w-4 h-4 spin" />} Create newsletter
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="text-[#71717A] py-12 text-center">Loading…</div>
      ) : pubs.length === 0 ? (
        <div className="surface rounded-lg p-12 text-center">
          <Mail className="w-10 h-10 text-[#CCFF00] mx-auto mb-3" />
          <div className="font-display font-bold text-lg mb-1">No newsletters yet</div>
          <p className="text-sm text-[#A1A1AA] max-w-md mx-auto">
            Ship a weekly digest, a new-drop announcement, or a monthly VIP letter — with coupons,
            gift cards, and funnels embedded natively.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {pubs.map((p) => (
            <div key={p.id} data-testid={`publication-card-${p.id}`}
              onClick={() => navigate(`/newsletters/${p.id}`)}
              className="surface rounded-lg p-5 cursor-pointer hover:border-[#CCFF00] transition-colors border border-transparent">
              <div className="flex items-start justify-between mb-2 gap-3">
                <div>
                  <div className="font-display font-bold text-lg">{p.name}</div>
                  <div className="text-xs text-[#71717A] font-mono">/n/{p.slug}</div>
                </div>
                <span className="w-8 h-8 rounded-full shrink-0"
                  style={{ background: p.primary_color || "#005CEE" }} />
              </div>
              {p.description && (
                <p className="text-xs text-[#A1A1AA] mb-3 line-clamp-2">{p.description}</p>
              )}
              <div className="flex items-center gap-4 text-xs text-[#71717A] mt-3">
                <span className="flex items-center gap-1">
                  <Users className="w-3.5 h-3.5" /> {p.subscriber_count || 0} subscriber{p.subscriber_count === 1 ? "" : "s"}
                </span>
                <span className="flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5" /> {p.post_count || 0} post{p.post_count === 1 ? "" : "s"}
                </span>
                <a href={`/n/${p.slug}`} target="_blank" rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  data-testid={`pub-public-link-${p.id}`}
                  className="ml-auto flex items-center gap-1 hover:text-[#CCFF00]">
                  <ExternalLink className="w-3 h-3" /> Public
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
