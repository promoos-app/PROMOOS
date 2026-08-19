// Pixel-perfect React mockups of the real app dashboards.
// Used on the Landing page for product-preview screenshots that don't drift when the real
// dashboard changes and load instantly (no external images, no auth flow).
import { Ticket, DollarSign, Users, TrendingUp, Sparkles, Wand2, Loader2 } from "lucide-react";

export function DashboardMockup() {
  return (
    <div className="rounded-xl overflow-hidden shadow-2xl border border-[#27272A] bg-[#0A0A0A]" data-testid="dashboard-mockup">
      {/* Browser chrome */}
      <div className="bg-[#141414] px-3 py-2 flex items-center gap-1.5 border-b border-[#27272A]">
        <div className="w-2.5 h-2.5 rounded-full bg-[#FF5F57]" />
        <div className="w-2.5 h-2.5 rounded-full bg-[#FEBC2E]" />
        <div className="w-2.5 h-2.5 rounded-full bg-[#28C840]" />
        <div className="ml-3 text-[10px] text-[#71717A] font-mono">app.promoos.com/dashboard</div>
      </div>
      <div className="grid grid-cols-[140px_1fr]">
        {/* Sidebar */}
        <div className="bg-[#0A0A0A] border-r border-[#27272A] p-3 text-[10px] space-y-1">
          <div className="flex items-center gap-1.5 mb-3">
            <img src="/promoos-logo.jpg" alt="PromoOS" className="h-4 w-auto object-contain rounded" />
          </div>
          {["Dashboard","Coupons","Gift Cards","Funnels","QR Studio","Analytics","Integrations"].map((l,i) => (
            <div key={l} className={`px-2 py-1 rounded ${i===0?"bg-[#CCFF00]/10 text-[#CCFF00]":"text-[#A1A1AA]"}`}>{l}</div>
          ))}
        </div>
        {/* Main */}
        <div className="p-4">
          <div className="font-display font-bold text-sm text-white mb-3">Command Center</div>
          <div className="grid grid-cols-4 gap-2 mb-3">
            {[
              { icon: Ticket, l: "Active", v: "42", c: "#CCFF00" },
              { icon: DollarSign, l: "Revenue", v: "$18,240", c: "#00F5FF" },
              { icon: Users, l: "Customers", v: "1,281", c: "#FF006E" },
              { icon: TrendingUp, l: "CVR", v: "12.4%", c: "#FFBE0B" },
            ].map((s) => {
              const Icon = s.icon;
              return (
                <div key={s.l} className="rounded-md bg-[#141414] border border-[#27272A] p-2">
                  <Icon className="w-3 h-3 mb-1" style={{ color: s.c }} />
                  <div className="text-[8px] uppercase tracking-widest text-[#71717A]">{s.l}</div>
                  <div className="text-sm font-bold text-white">{s.v}</div>
                </div>
              );
            })}
          </div>
          {/* Chart placeholder */}
          <div className="rounded-md bg-[#141414] border border-[#27272A] p-3">
            <div className="text-[9px] uppercase tracking-widest text-[#71717A] mb-2">Redemptions · 30 days</div>
            <div className="h-16 flex items-end gap-1">
              {[8,12,9,15,11,17,13,19,22,18,24,21,27,25,30,28,33,29,35,32,38,36,42,39,45,43,48,46,51,49].map((h, i) => (
                <div key={i} className="flex-1 rounded-t" style={{ height: `${h*1.5}%`, background: `linear-gradient(180deg, #CCFF00 0%, #005CEE 100%)`, opacity: 0.4 + (i / 60) }} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function GiftCardStudioMockup() {
  return (
    <div className="rounded-xl overflow-hidden shadow-2xl border border-[#27272A] bg-[#0A0A0A]" data-testid="gc-studio-mockup">
      <div className="bg-[#141414] px-3 py-2 flex items-center gap-1.5 border-b border-[#27272A]">
        <div className="w-2.5 h-2.5 rounded-full bg-[#FF5F57]" />
        <div className="w-2.5 h-2.5 rounded-full bg-[#FEBC2E]" />
        <div className="w-2.5 h-2.5 rounded-full bg-[#28C840]" />
        <div className="ml-3 text-[10px] text-[#71717A] font-mono">app.promoos.com/gift-cards/studio</div>
      </div>
      <div className="p-4">
        <div className="text-[9px] uppercase tracking-widest text-[#71717A] mb-2">Live preview · Midnight Onyx</div>
        {/* Fake gift card */}
        <div className="rounded-xl h-40 mb-3 relative overflow-hidden"
             style={{ background: "linear-gradient(135deg,#0A0A0A 0%,#1A1A1A 60%,#2B2B2B 100%)" }}>
          <div className="absolute inset-0 p-5 flex flex-col justify-between text-white">
            <div className="text-[8px] tracking-[0.3em] uppercase text-[#CCFF00]">Gift Card</div>
            <div>
              <div className="font-display font-bold text-lg">To someone remarkable</div>
              <div className="text-[10px] opacity-70">A little something, from the heart.</div>
            </div>
            <div className="absolute bottom-2 right-3 text-[8px] tracking-widest text-white/50 font-mono">GC-8F3K2Q</div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 mb-3">
          <div className="rounded-md bg-[#141414] border border-[#27272A] p-2">
            <div className="text-[8px] uppercase text-[#71717A]">Headline</div>
            <div className="text-[10px] text-white flex items-center justify-between">
              <span>To someone remarkable</span>
              <Wand2 className="w-2.5 h-2.5 text-[#CCFF00]" />
            </div>
          </div>
          <div className="rounded-md bg-[#141414] border border-[#27272A] p-2">
            <div className="text-[8px] uppercase text-[#71717A]">Background</div>
            <div className="text-[10px] text-white flex items-center justify-between">
              <span>AI-generated</span>
              <Sparkles className="w-2.5 h-2.5 text-[#CCFF00]" />
            </div>
          </div>
        </div>
        <div className="text-[9px] uppercase tracking-widest text-[#71717A] mb-1">More templates</div>
        <div className="grid grid-cols-5 gap-1">
          {[
            "linear-gradient(135deg,#3A2E12,#D4AF37)",
            "linear-gradient(135deg,#2B0A0F,#B01930)",
            "linear-gradient(135deg,#04231A,#1FB07E)",
            "linear-gradient(135deg,#FF006E,#3A86FF)",
            "linear-gradient(135deg,#FDE2E4,#FAD2E1)",
          ].map((bg,i) => (
            <div key={i} className="aspect-video rounded" style={{ background: bg }} />
          ))}
        </div>
      </div>
    </div>
  );
}

export function CouponBuilderMockup() {
  return (
    <div className="rounded-xl overflow-hidden shadow-2xl border border-[#27272A] bg-[#0A0A0A]" data-testid="coupon-builder-mockup">
      <div className="bg-[#141414] px-3 py-2 flex items-center gap-1.5 border-b border-[#27272A]">
        <div className="w-2.5 h-2.5 rounded-full bg-[#FF5F57]" />
        <div className="w-2.5 h-2.5 rounded-full bg-[#FEBC2E]" />
        <div className="w-2.5 h-2.5 rounded-full bg-[#28C840]" />
        <div className="ml-3 text-[10px] text-[#71717A] font-mono">app.promoos.com/coupons/new</div>
      </div>
      <div className="p-4">
        <div className="text-[9px] uppercase tracking-widest text-[#CCFF00] mb-1">AI Copilot</div>
        <div className="text-sm font-display font-bold text-white mb-3">Design your coupon</div>
        <div className="rounded-md bg-[#141414] border border-[#27272A] p-3 mb-2">
          <div className="text-[8px] uppercase text-[#71717A] mb-1">Headline</div>
          <div className="text-[11px] text-white">Save 20% off your first order — this weekend only</div>
        </div>
        <div className="grid grid-cols-2 gap-2 mb-2">
          <div className="rounded-md bg-[#141414] border border-[#27272A] p-2">
            <div className="text-[8px] uppercase text-[#71717A]">Type</div>
            <div className="text-[10px] text-white">Percentage · 20%</div>
          </div>
          <div className="rounded-md bg-[#141414] border border-[#27272A] p-2">
            <div className="text-[8px] uppercase text-[#71717A]">Code</div>
            <div className="text-[10px] text-white font-mono">WEEKEND20</div>
          </div>
        </div>
        <div className="rounded-md bg-gradient-to-br from-[#005CEE] to-[#00F5FF] p-3 mt-3">
          <div className="text-[8px] uppercase tracking-widest text-white/70 mb-0.5">Preview</div>
          <div className="text-white font-display font-bold text-base">Save 20% off your first order</div>
          <div className="text-white/80 text-[9px]">Use code WEEKEND20 at checkout · Expires Sunday</div>
        </div>
      </div>
    </div>
  );
}
