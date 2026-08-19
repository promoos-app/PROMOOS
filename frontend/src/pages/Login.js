import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sparkles, Ticket, Bot, Wand2 } from "lucide-react";
import Footer from "@/components/Footer";

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "admin@promoos.com", password: "admin123", workspace_name: "" });
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (mode === "login") await login(form.email, form.password);
      else await register(form);
      navigate("/");
    } catch (err) {
      toast.error(apiError(err, "Authentication failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0A0A0A] grain text-white">
      <div className="flex-1 flex">
      {/* Left brand panel */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 border-r border-[#27272A] p-12 relative overflow-hidden">
        <div className="flex items-center gap-2 z-10">
          <img src="/promoos-logo.jpg" alt="PromoOS" className="h-9 w-auto object-contain rounded" data-testid="login-logo" />
        </div>
        <div className="z-10 max-w-md">
          <h1 className="font-display font-extrabold text-5xl leading-[1.05] tracking-tight mb-4">
            The Promotional Operating System.
          </h1>
          <p className="text-[#A1A1AA] text-base leading-relaxed">
            Create, design, and optimize coupons, gift cards, and loyalty campaigns — powered by AI, run from one command center.
          </p>
          <div className="mt-10 space-y-3">
            {[
              [Ticket, "Every coupon type, one rule builder"],
              [Bot, "AI Copilot writes the copy & concept"],
              [Wand2, "Generate on-brand promo visuals instantly"],
            ].map(([Icon, txt], i) => (
              <div key={i} className="flex items-center gap-3 text-sm text-[#A1A1AA]">
                <Icon className="w-4 h-4 text-[#CCFF00]" /> {txt}
              </div>
            ))}
          </div>
        </div>
        <div className="text-xs text-[#52525B] z-10 font-mono">v1.0 · Command Center</div>
        <div className="absolute -bottom-40 -right-40 w-96 h-96 rounded-full bg-[#005CEE] opacity-20 blur-[120px]" />
      </div>

      {/* Right form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm fade-up">
          <h2 className="font-display font-bold text-3xl mb-1">
            {mode === "login" ? "Welcome back" : "Create your workspace"}
          </h2>
          <p className="text-sm text-[#A1A1AA] mb-8">
            {mode === "login" ? "Sign in to your command center." : "Start running smarter promotions."}
          </p>

          <form onSubmit={submit} className="space-y-4">
            {mode === "register" && (
              <div>
                <Label className="text-xs text-[#A1A1AA]">Your name</Label>
                <Input data-testid="register-name-input" required value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="mt-1 bg-[#141414] border-[#27272A] text-white" placeholder="Alex Merchant" />
              </div>
            )}
            <div>
              <Label className="text-xs text-[#A1A1AA]">Email</Label>
              <Input data-testid="email-input" type="email" required value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="mt-1 bg-[#141414] border-[#27272A] text-white" placeholder="you@company.com" />
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Password</Label>
              <Input data-testid="password-input" type="password" required value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="mt-1 bg-[#141414] border-[#27272A] text-white" placeholder="••••••••" />
            </div>
            {mode === "register" && (
              <div>
                <Label className="text-xs text-[#A1A1AA]">Workspace name (optional)</Label>
                <Input data-testid="register-workspace-input" value={form.workspace_name}
                  onChange={(e) => setForm({ ...form, workspace_name: e.target.value })}
                  className="mt-1 bg-[#141414] border-[#27272A] text-white" placeholder="Acme Co." />
              </div>
            )}
            <Button data-testid="submit-auth-btn" type="submit" disabled={loading}
              className="btn-primary w-full h-10 rounded-md font-medium">
              {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create workspace"}
            </Button>
          </form>

          <button data-testid="toggle-auth-mode-btn"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
            className="mt-5 text-sm text-[#A1A1AA] hover:text-white transition-colors">
            {mode === "login" ? "Need an account? Create one" : "Already have an account? Sign in"}
          </button>
        </div>
      </div>
      </div>
      <div className="border-t border-[#27272A] px-6 lg:px-12"><Footer compact /></div>
    </div>
  );
}
