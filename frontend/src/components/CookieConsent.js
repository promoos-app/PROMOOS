import { useEffect, useState } from "react";

/**
 * Cookie Consent Banner — displayed on every public funnel (GDPR / CCPA).
 * Persists the user's decision in localStorage so the banner disappears
 * on subsequent visits until they clear their storage. Analytics/tracking
 * calls elsewhere should short-circuit if the consent flag is `denied`.
 */
const KEY = "promoos_cookie_consent";

export function getCookieConsent() {
  try { return localStorage.getItem(KEY) || null; } catch (_) { return null; }
}

export default function CookieConsent({ theme }) {
  const [decision, setDecision] = useState(() => getCookieConsent());
  useEffect(() => {
    // Re-check in case a prior tab decided while this one was open.
    try { setDecision(localStorage.getItem(KEY) || null); } catch (_) {}
  }, []);
  if (decision) return null;
  const decide = (choice) => {
    try { localStorage.setItem(KEY, choice); } catch (_) {}
    setDecision(choice);
  };
  const bg = theme?.bg || "#0A0A0A";
  const fg = theme?.fg || "#FFFFFF";
  const accent = theme?.accent || "#CCFF00";
  return (
    <div
      role="dialog"
      aria-live="polite"
      data-testid="cookie-consent"
      style={{
        position: "fixed", bottom: 12, left: 12, right: 12, zIndex: 60,
        maxWidth: 720, margin: "0 auto",
        background: `${bg}f2`,
        border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: 12, padding: "14px 16px",
        color: fg,
        boxShadow: "0 20px 40px rgba(0,0,0,0.45)",
        backdropFilter: "blur(12px)",
        fontFamily: "inherit",
      }}
    >
      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 220 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 2 }}>We use cookies</div>
          <div style={{ fontSize: 12, opacity: 0.7, lineHeight: 1.4 }}>
            Essential cookies keep this page working. Analytics cookies help us understand what's
            useful — only if you say yes. <a href="/privacy" style={{ color: accent, textDecoration: "underline" }}>Privacy policy</a>.
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
          <button
            onClick={() => decide("denied")}
            data-testid="cookie-consent-deny"
            style={{
              fontSize: 12, padding: "8px 14px",
              background: "transparent", color: fg,
              border: "1px solid rgba(255,255,255,0.18)",
              borderRadius: 8, cursor: "pointer",
            }}
          >Only essential</button>
          <button
            onClick={() => decide("granted")}
            data-testid="cookie-consent-accept"
            style={{
              fontSize: 12, padding: "8px 14px", fontWeight: 700,
              background: accent, color: bg,
              border: "none", borderRadius: 8, cursor: "pointer",
            }}
          >Accept all</button>
        </div>
      </div>
    </div>
  );
}
