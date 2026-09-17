import { useEffect, useState } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import axios from "axios";
import CookieConsent from "@/components/CookieConsent";

const API = process.env.REACT_APP_BACKEND_URL;

export default function PublicNewsletter() {
  const { slug } = useParams();
  const [sp] = useSearchParams();
  const ref = sp.get("ref") || "";
  const [pub, setPub] = useState(null);
  const [err, setErr] = useState(null);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [done, setDone] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios.get(`${API}/api/newsletter/public/${slug}`)
      .then((r) => setPub(r.data))
      .catch((e) => setErr((e?.response?.data?.detail) || "Not found"));
  }, [slug]);

  const subscribe = async (e) => {
    e.preventDefault();
    if (!email.includes("@")) return;
    setBusy(true);
    try {
      const { data } = await axios.post(`${API}/api/newsletter/public/${slug}/subscribe`,
        { email, name, ref: ref || null });
      setDone(data);
    } catch (er) {
      setDone({ ok: false, error: er?.response?.data?.detail || "Subscribe failed" });
    } finally { setBusy(false); }
  };

  if (err) return <ErrorScreen msg={err} />;
  if (!pub) return <LoadingScreen />;

  const p = pub.primary_color || "#005CEE";
  return (
    <div style={{ background: "#0A0A0A", color: "#fff", minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}
      data-testid="public-newsletter">
      <div style={{ maxWidth: 720, margin: "0 auto", padding: "80px 24px 120px" }}>
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{ fontSize: 12, letterSpacing: 4, textTransform: "uppercase", color: p, marginBottom: 12 }}>
            Newsletter
          </div>
          <h1 style={{ fontSize: 44, fontWeight: 800, margin: 0, lineHeight: 1.1 }}>{pub.name}</h1>
          {pub.description && (
            <p style={{ fontSize: 15, color: "#A1A1AA", marginTop: 12, maxWidth: 480, marginLeft: "auto", marginRight: "auto" }}>
              {pub.description}
            </p>
          )}
        </div>

        {done ? (
          <div style={{ background: "#141414", border: "1px solid #27272A", borderRadius: 12, padding: 32, textAlign: "center" }}
            data-testid="subscribe-thanks">
            <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 8, color: done.ok ? p : "#F87171" }}>
              {done.ok ? pub.thanks_headline : "Something went wrong"}
            </div>
            <div style={{ color: "#A1A1AA", fontSize: 14 }}>{done.ok ? pub.thanks_body : done.error}</div>
          </div>
        ) : (
          <form onSubmit={subscribe}
            style={{ background: "#141414", border: "1px solid #27272A", borderRadius: 12, padding: 32, marginBottom: 40 }}
            data-testid="subscribe-form">
            <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 6 }}>{pub.subscribe_headline}</div>
            <div style={{ color: "#A1A1AA", fontSize: 14, marginBottom: 20 }}>{pub.subscribe_body}</div>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com" data-testid="subscribe-email"
              style={{ width: "100%", padding: "12px 14px", background: "#0A0A0A", border: "1px solid #27272A",
                       borderRadius: 8, color: "#fff", fontSize: 14, marginBottom: 8, boxSizing: "border-box" }} />
            <input value={name} onChange={(e) => setName(e.target.value)}
              placeholder="Name (optional)" data-testid="subscribe-name"
              style={{ width: "100%", padding: "12px 14px", background: "#0A0A0A", border: "1px solid #27272A",
                       borderRadius: 8, color: "#fff", fontSize: 14, marginBottom: 12, boxSizing: "border-box" }} />
            <button type="submit" disabled={busy} data-testid="subscribe-submit"
              style={{ width: "100%", padding: "12px", background: p, color: "#fff",
                       border: "none", borderRadius: 8, fontSize: 14, fontWeight: 700, cursor: "pointer",
                       opacity: busy ? 0.6 : 1 }}>
              {busy ? "Subscribing…" : "Subscribe"}
            </button>
            {ref && <div style={{ fontSize: 11, color: "#71717A", marginTop: 12, textAlign: "center" }}>
              Referred by a friend
            </div>}
          </form>
        )}

        {pub.posts?.length > 0 && (
          <div>
            <div style={{ fontSize: 12, letterSpacing: 3, textTransform: "uppercase", color: "#A1A1AA", marginBottom: 16 }}>
              Recent issues
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {pub.posts.map((post) => (
                <Link key={post.id} to={`/n/${slug}/p/${post.slug}`}
                  data-testid={`archive-post-${post.slug}`}
                  style={{ display: "block", padding: "16px 20px", background: "#141414",
                            border: "1px solid #27272A", borderRadius: 10, textDecoration: "none", color: "#fff" }}>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>{post.title}</div>
                  {post.subtitle && <div style={{ fontSize: 13, color: "#A1A1AA", marginTop: 4 }}>{post.subtitle}</div>}
                  <div style={{ fontSize: 11, color: "#71717A", marginTop: 8 }}>
                    {post.sent_at ? new Date(post.sent_at).toLocaleDateString() : ""}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
      <CookieConsent theme={{ bg: "#0A0A0A", fg: "#fff", accent: p }} />
    </div>
  );
}

function LoadingScreen() {
  return <div style={{ minHeight: "100vh", background: "#0A0A0A", color: "#71717A",
    display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "system-ui" }}>Loading…</div>;
}
function ErrorScreen({ msg }) {
  return <div style={{ minHeight: "100vh", background: "#0A0A0A", color: "#fff",
    display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "system-ui", flexDirection: "column" }}>
    <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 8 }}>Newsletter not found</div>
    <div style={{ fontSize: 13, color: "#71717A" }}>{msg}</div>
  </div>;
}
