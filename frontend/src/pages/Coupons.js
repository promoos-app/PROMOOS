import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { apiError } from "@/lib/api";
import { STATE_STYLES, TYPE_LABELS, discountText } from "@/lib/couponUtils";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Search, MoreHorizontal, Ticket } from "lucide-react";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

const FILTERS = ["all", "draft", "scheduled", "active", "paused", "expired", "archived"];
const NEXT_STATES = ["draft", "scheduled", "active", "paused", "expired", "archived"];

export default function Coupons() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  const { data: coupons = [], isLoading } = useQuery({
    queryKey: ["coupons", filter],
    queryFn: async () => (await api.get(`/coupons?state=${filter}`)).data,
  });

  const filtered = coupons.filter((c) => c.name.toLowerCase().includes(search.toLowerCase()) || c.code.toLowerCase().includes(search.toLowerCase()));

  const changeState = async (id, state) => {
    try {
      await api.post(`/coupons/${id}/state`, { state });
      qc.invalidateQueries({ queryKey: ["coupons"] });
      toast.success(`Moved to ${state}`);
    } catch (e) { toast.error(apiError(e)); }
  };
  const del = async (id) => {
    try {
      await api.delete(`/coupons/${id}`);
      qc.invalidateQueries({ queryKey: ["coupons"] });
      toast.success("Coupon deleted");
    } catch (e) { toast.error(apiError(e)); }
  };

  return (
    <div className="fade-up max-w-[1400px]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight">Coupons</h1>
          <p className="text-sm text-[#A1A1AA] mt-1">Create, manage and publish your offers.</p>
        </div>
        <Button data-testid="new-coupon-btn" onClick={() => navigate("/coupons/new")} className="btn-primary gap-2 rounded-md">
          <Plus className="w-4 h-4" /> New Coupon
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="flex gap-1 flex-wrap">
          {FILTERS.map((f) => (
            <button key={f} data-testid={`filter-${f}`} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-md text-sm capitalize transition-colors ${
                filter === f ? "bg-[#141414] text-white border border-[#27272A]" : "text-[#A1A1AA] hover:text-white"
              }`}>{f}</button>
          ))}
        </div>
        <div className="relative sm:ml-auto sm:w-64">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#71717A]" />
          <Input data-testid="coupon-search" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search coupons…" className="pl-9 bg-[#141414] border-[#27272A] text-white h-9" />
        </div>
      </div>

      <div className="surface rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-[#71717A]">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="p-16 text-center">
            <Ticket className="w-10 h-10 mx-auto text-[#3a3a3e] mb-3" />
            <p className="text-[#A1A1AA]">No coupons yet.</p>
            <Button data-testid="empty-new-coupon-btn" onClick={() => navigate("/coupons/new")} className="btn-ai mt-4 rounded-md gap-2">
              <Plus className="w-4 h-4" /> Create your first coupon
            </Button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wide text-[#71717A] border-b border-[#27272A]">
                <th className="text-left font-medium p-4">Name</th>
                <th className="text-left font-medium p-4">Code</th>
                <th className="text-left font-medium p-4">Type</th>
                <th className="text-left font-medium p-4">Discount</th>
                <th className="text-left font-medium p-4">State</th>
                <th className="text-right font-medium p-4">Redemptions</th>
                <th className="w-10 p-4"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id} data-testid={`coupon-row-${c.id}`}
                  className="border-b border-[#1E1E1E] last:border-0 hover:bg-[#141414] transition-colors cursor-pointer"
                  onClick={() => navigate(`/coupons/${c.id}`)}>
                  <td className="p-4 font-medium">{c.name}</td>
                  <td className="p-4"><span className="font-mono text-xs bg-[#0A0A0A] border border-[#27272A] px-2 py-1 rounded">{c.code}</span></td>
                  <td className="p-4 text-[#A1A1AA]">{TYPE_LABELS[c.type] || c.type}</td>
                  <td className="p-4 font-mono">{discountText(c)}</td>
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded text-xs capitalize font-medium ${STATE_STYLES[c.state]}`}>{c.state}</span>
                  </td>
                  <td className="p-4 text-right font-mono">{c.stats?.redemptions ?? 0}</td>
                  <td className="p-4" onClick={(e) => e.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button data-testid={`coupon-menu-${c.id}`} className="p-1.5 rounded hover:bg-[#1E1E1E] transition-colors">
                          <MoreHorizontal className="w-4 h-4 text-[#A1A1AA]" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="bg-[#141414] border-[#27272A] text-white">
                        <DropdownMenuItem className="focus:bg-[#1E1E1E]" onClick={() => navigate(`/coupons/${c.id}/edit`)}>Edit</DropdownMenuItem>
                        <DropdownMenuItem className="focus:bg-[#1E1E1E]" onClick={() => navigate(`/coupons/${c.id}`)}>View & QR</DropdownMenuItem>
                        <DropdownMenuSeparator className="bg-[#27272A]" />
                        {NEXT_STATES.filter((s) => s !== c.state).map((s) => (
                          <DropdownMenuItem key={s} className="focus:bg-[#1E1E1E] capitalize" onClick={() => changeState(c.id, s)}>
                            Move to {s}
                          </DropdownMenuItem>
                        ))}
                        <DropdownMenuSeparator className="bg-[#27272A]" />
                        <DropdownMenuItem className="focus:bg-[#1E1E1E] text-red-400" onClick={() => del(c.id)}>Delete</DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
