import { useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { KeyRound, ArrowLeft, Loader2 } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setBusy(true);
    try {
      await axios.post(`${API}/api/auth/password-reset/request`, { email });
      setSent(true);
    } catch { toast.error("Could not send reset link"); } finally { setBusy(false); }
  };
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0A0A] text-white px-6" data-testid="forgot-password-page">
      <div className="w-full max-w-sm">
        <Link to="/login" className="text-xs text-[#71717A] hover:text-white flex items-center gap-1 mb-4">
          <ArrowLeft className="w-3 h-3" /> Back to sign in
        </Link>
        <div className="flex items-center gap-2 mb-6">
          <KeyRound className="w-5 h-5 text-[#CCFF00]" />
          <h1 className="font-display font-bold text-2xl">Reset your password</h1>
        </div>
        {sent ? (
          <div className="surface rounded-lg p-6" data-testid="reset-sent-message">
            <p className="text-sm text-[#A1A1AA]">If that email exists, we've sent you a reset link. Check your inbox — the link expires in 2 hours.</p>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div>
              <Label className="text-xs text-[#A1A1AA]">Email</Label>
              <Input data-testid="forgot-email-input" type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 bg-[#141414] border-[#27272A] text-white" />
            </div>
            <Button data-testid="forgot-submit-btn" type="submit" disabled={busy} className="btn-primary rounded-md w-full gap-2">
              {busy && <Loader2 className="w-4 h-4 spin" />} Send reset link
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}

export function ResetPassword() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const [pwd, setPwd] = useState("");
  const [pwd2, setPwd2] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    if (pwd !== pwd2) { toast.error("Passwords don't match"); return; }
    if (pwd.length < 8) { toast.error("At least 8 characters"); return; }
    setBusy(true);
    try {
      await axios.post(`${API}/api/auth/password-reset/complete`, { token: sp.get("token"), new_password: pwd });
      toast.success("Password reset — please sign in with the new password");
      nav("/login");
    } catch (e) { toast.error(e?.response?.data?.detail || "Reset failed"); } finally { setBusy(false); }
  };
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0A0A] text-white px-6" data-testid="reset-password-page">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 mb-6">
          <KeyRound className="w-5 h-5 text-[#CCFF00]" />
          <h1 className="font-display font-bold text-2xl">Set new password</h1>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <Label className="text-xs text-[#A1A1AA]">New password</Label>
            <Input data-testid="reset-pw-input" type="password" required value={pwd} onChange={(e) => setPwd(e.target.value)}
              className="mt-1 bg-[#141414] border-[#27272A] text-white" />
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Confirm</Label>
            <Input data-testid="reset-pw2-input" type="password" required value={pwd2} onChange={(e) => setPwd2(e.target.value)}
              className="mt-1 bg-[#141414] border-[#27272A] text-white" />
          </div>
          <Button data-testid="reset-submit-btn" type="submit" disabled={busy} className="btn-primary rounded-md w-full gap-2">
            {busy && <Loader2 className="w-4 h-4 spin" />} Reset password
          </Button>
        </form>
      </div>
    </div>
  );
}
