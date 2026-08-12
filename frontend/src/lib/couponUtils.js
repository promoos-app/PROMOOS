// Shared coupon UI helpers
export const STATE_STYLES = {
  draft: "bg-zinc-500/10 text-zinc-400",
  scheduled: "bg-amber-500/10 text-amber-400",
  active: "bg-emerald-500/10 text-emerald-400",
  paused: "bg-orange-500/10 text-orange-400",
  expired: "bg-red-500/10 text-red-400",
  archived: "bg-zinc-600/10 text-zinc-500",
};

export const TYPE_LABELS = {
  percentage: "% Off",
  fixed: "Fixed Amount",
  bogo: "BOGO",
  free_shipping: "Free Shipping",
  first_time: "First-Time",
  vip: "VIP",
  flash_sale: "Flash Sale",
  seasonal: "Seasonal",
  referral: "Referral",
  birthday: "Birthday",
};

export function discountText(c) {
  if (c.type === "free_shipping") return "Free Shipping";
  if (c.type === "fixed") return `$${c.discount_value} off`;
  return `${c.discount_value}% off`;
}
