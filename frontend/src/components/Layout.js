import { Outlet, NavLink, useNavigate, useLocation } from "react-router-dom";
import Footer from "@/components/Footer";
import ErrorBoundary from "@/components/ErrorBoundary";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";
import {
  LayoutDashboard, Ticket, Megaphone, Users, Gift, Palette,
  BarChart3, Plug, Settings as SettingsIcon, Sparkles, LogOut, ChevronDown, CalendarDays, CreditCard, Shield, Rocket, QrCode, MessageSquareQuote, Package, Zap, Mail,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/coupons", label: "Coupons", icon: Ticket },
  { to: "/library", label: "Library", icon: Sparkles },
  { to: "/calendar", label: "Calendar", icon: CalendarDays },
  { to: "/campaigns", label: "Campaigns", icon: Megaphone },
  { to: "/customers", label: "Customers", icon: Users },
  { to: "/rewards", label: "Rewards", icon: Gift },
  { to: "/gift-cards", label: "Gift Cards", icon: CreditCard },
  { to: "/funnels", label: "Funnels", icon: Rocket },
  { to: "/products", label: "Products", icon: Package },
  { to: "/reviews", label: "Reviews", icon: MessageSquareQuote },
  { to: "/sequences", label: "Automations", icon: Zap },
  { to: "/newsletters", label: "Newsletters", icon: Mail },
  { to: "/qr", label: "QR Studio", icon: QrCode },
  { to: "/design", label: "Design", icon: Palette },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/integrations", label: "Integrations", icon: Plug },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
  { to: "/admin", label: "Admin", icon: Shield, superadmin: true },
];

export default function Layout() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { data: ws } = useQuery({
    queryKey: ["workspace"],
    queryFn: async () => (await api.get("/workspace")).data,
  });

  return (
    <div className="h-screen flex overflow-hidden bg-[#0A0A0A] grain">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 border-r border-[#27272A] flex flex-col bg-[#0A0A0A] z-10">
        <div className="h-16 flex items-center px-5 border-b border-[#27272A]">
          <img src="/promoos-logo.jpg" alt="PromoOS" className="h-9 w-auto object-contain rounded" data-testid="sidebar-logo" />
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
          {NAV.filter((n) => !n.superadmin || user?.role === "superadmin").map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              data-testid={`sidebar-${n.label.toLowerCase().replace(/\s+/g, "-")}-link`}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? "bg-[#141414] text-white border-l-2 border-[#005CEE] pl-[10px]"
                    : "text-[#A1A1AA] hover:text-white hover:bg-[#141414]"
                }`
              }
            >
              <n.icon className="w-[18px] h-[18px]" />
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-[#27272A]">
          <div className="text-xs text-[#71717A] px-2 mb-1">Workspace</div>
          <div className="px-2 py-1.5 rounded-md bg-[#141414] text-sm truncate" data-testid="workspace-name">
            {ws?.name || "…"}
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 z-10">
        <header className="h-16 shrink-0 border-b border-[#27272A] flex items-center justify-between px-6 bg-[#0A0A0A]">
          <div className="flex items-center gap-3">
            <Button
              data-testid="topbar-ai-copilot-btn"
              onClick={() => navigate("/coupons/new")}
              className="btn-ai h-9 gap-2 font-medium rounded-md"
            >
              <Sparkles className="w-4 h-4" /> Ask AI Copilot
            </Button>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button data-testid="user-menu-btn" className="flex items-center gap-2 text-sm hover:bg-[#141414] px-3 py-2 rounded-md transition-colors">
                <div className="w-7 h-7 rounded-full bg-[#005CEE] flex items-center justify-center text-xs font-semibold">
                  {user?.name?.[0]?.toUpperCase()}
                </div>
                <span className="hidden sm:block">{user?.name}</span>
                <span className="text-xs text-[#71717A] uppercase font-mono">{user?.role}</span>
                <ChevronDown className="w-4 h-4 text-[#71717A]" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="bg-[#141414] border-[#27272A] text-white">
              <DropdownMenuItem data-testid="logout-btn" onClick={logout} className="gap-2 cursor-pointer focus:bg-[#1E1E1E]">
                <LogOut className="w-4 h-4" /> Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <ErrorBoundary resetKey={location.pathname}>
            <Outlet />
          </ErrorBoundary>
          <Footer />
        </main>
      </div>
    </div>
  );
}
