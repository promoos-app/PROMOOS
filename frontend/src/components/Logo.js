// Central logo component — swap here to update everywhere.
export default function Logo({ className = "", size = "md", showWordmark = true }) {
  const heights = { xs: "h-5", sm: "h-6", md: "h-8", lg: "h-10", xl: "h-12" };
  const h = heights[size] || heights.md;
  return (
    <img
      src="/promoos-logo.jpg"
      alt="PromoOS"
      className={`${h} w-auto object-contain ${className}`}
      data-testid="promoos-logo"
    />
  );
}
