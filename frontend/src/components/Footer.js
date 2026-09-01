import { Link } from "react-router-dom";
import { Lock, Shield } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function Footer({ compact = false }) {
  const { user } = useAuth() || {};
  const isPrivileged = user && (user.role === "superadmin" || user.role === "admin");
  return (
    <footer className={`text-[11px] text-[#71717A] flex flex-wrap items-center justify-between gap-2 ${compact ? "py-3" : "py-6 border-t border-[#27272A] mt-10"}`} data-testid="site-footer">
      <div>
        © 2026 <span className="text-white font-medium">PromoOS</span>. All rights reserved.
        <span className="hidden sm:inline"> · A Division of Glorified Technology Solution (GTS).</span>
      </div>
      <div className="flex items-center gap-3">
        <Link to="/pricing" className="hover:text-white transition" data-testid="footer-pricing">Pricing</Link>
        <span>·</span>
        <Link to="/privacy" className="hover:text-white transition" data-testid="footer-privacy">Privacy Policy</Link>
        <span>·</span>
        <Link to="/terms" className="hover:text-white transition" data-testid="footer-terms">Terms of Use</Link>
        <span>·</span>
        {isPrivileged ? (
          <Link
            to="/admin"
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#141414] border border-[#27272A] text-[#CCFF00] hover:bg-[#1E1E1E] hover:border-[#CCFF00]/40 transition"
            data-testid="footer-admin-portal"
            title="Open Admin Portal"
          >
            <Shield className="w-3 h-3" /> Admin Portal
          </Link>
        ) : (
          <Link
            to="/login?admin=1"
            className="hover:text-[#CCFF00] transition flex items-center gap-1"
            data-testid="footer-admin-login"
            title="Sign in as an admin"
          >
            <Lock className="w-3 h-3" /> Admin
          </Link>
        )}
      </div>
    </footer>
  );
}
