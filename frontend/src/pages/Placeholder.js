import { useNavigate } from "react-router-dom";
import { Sparkles, Construction } from "lucide-react";
import { Button } from "@/components/ui/button";

const COPY = {
  Campaigns: "Group coupons into multi-channel campaigns with schedules and goals.",
  Customers: "Customer CRM with purchase history, LTV, tags and AI segmentation.",
  Rewards: "Loyalty points, tiers, gift cards and referral engine.",
  "Design Studio": "AI template designer and reusable on-brand promo layouts.",
  Integrations: "Connect Shopify, WooCommerce, email (Resend), SMS/WhatsApp (Twilio).",
};

export default function Placeholder({ title }) {
  const navigate = useNavigate();
  return (
    <div className="fade-up flex items-center justify-center min-h-[70vh]">
      <div className="text-center max-w-md">
        <div className="w-14 h-14 rounded-lg bg-[#141414] border border-[#27272A] flex items-center justify-center mx-auto mb-5">
          <Construction className="w-6 h-6 text-[#CCFF00]" />
        </div>
        <h1 className="font-display font-bold text-3xl tracking-tight mb-2">{title}</h1>
        <p className="text-sm text-[#A1A1AA] mb-6">{COPY[title] || "Coming soon."} This module ships in an upcoming phase.</p>
        <Button data-testid="placeholder-cta-btn" onClick={() => navigate("/coupons/new")} className="btn-ai rounded-md gap-2">
          <Sparkles className="w-4 h-4" /> Try the AI Copilot
        </Button>
      </div>
    </div>
  );
}
