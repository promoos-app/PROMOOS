import { Link } from "react-router-dom";

export default function Footer({ compact = false }) {
  return (
    <footer className={`text-[11px] text-[#71717A] flex flex-wrap items-center justify-between gap-2 ${compact ? "py-3" : "py-6 border-t border-[#27272A] mt-10"}`} data-testid="site-footer">
      <div>
        © 2026 <span className="text-white font-medium">PromoOS</span>. All rights reserved.
        <span className="hidden sm:inline"> · A Division of Glorified Technology Solution (GTS).</span>
      </div>
      <div className="flex items-center gap-3">
        <Link to="/privacy" className="hover:text-white transition" data-testid="footer-privacy">Privacy Policy</Link>
        <span>·</span>
        <Link to="/terms" className="hover:text-white transition" data-testid="footer-terms">Terms of Use</Link>
      </div>
    </footer>
  );
}
