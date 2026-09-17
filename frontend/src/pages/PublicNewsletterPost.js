import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import CookieConsent from "@/components/CookieConsent";

const API = process.env.REACT_APP_BACKEND_URL;

/** Render one block as inline JSX. Mirrors the email render but colored for a public dark page. */
function Block({ b, primary }) {
  const p = b.props || {};
  if (b.type === "heading") {
    const Tag = p.level === "h2" ? "h2" : "h1";
    return <Tag style={{ fontSize: Tag === "h1" ? 28 : 22, margin: "24px 0 8px", color: "#fff" }}>{p.text}</Tag>;
  }
  if (b.type === "text") return <p style={{ margin: "0 0 16px", fontSize: 15, lineHeight: 1.7, color: "#E4E4E7", whiteSpace: "pre-wrap" }}>{p.text}</p>;
  if (b.type === "image" && p.url) return <img src={p.url} alt={p.alt || ""} style={{ display: "block", width: "100%", borderRadius: 10, margin: "16px 0" }} />;
  if (b.type === "button") return (
    <div style={{ margin: "24px 0" }}>
      <a href={p.url || "#"} target="_blank" rel="noopener noreferrer"
        style={{ display: "inline-block", background: primary, color: "#fff",
                 textDecoration: "none", padding: "12px 24px", borderRadius: 8, fontWeight: 700 }}>{p.label}</a>
    </div>
  );
  if (b.type === "divider") return <hr style={{ border: 0, borderTop: "1px solid #27272A", margin: "24px 0" }} />;
  if (b.type === "coupon") {
    const h = p._hydrated || {};
    const code = h.code || p.code || "CODE";
    return (
      <div style={{ margin: "16px 0", padding: 20, border: `2px dashed ${primary}`, borderRadius: 10, textAlign: "center" }}>
        <div style={{ fontSize: 11, color: "#A1A1AA", textTransform: "uppercase", letterSpacing: 3, marginBottom: 8 }}>Reader-only offer</div>
        <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 12, color: "#fff" }}>{h.headline || "A gift for you"}</div>
        <div style={{ fontFamily: "monospace", fontSize: 22, fontWeight: 800, letterSpacing: 4, color: primary, marginBottom: 16 }}>{code}</div>
        <a href={`/c/${code}`} style={{ display: "inline-block", background: primary, color: "#fff",
          textDecoration: "none", padding: "10px 20px", borderRadius: 8, fontWeight: 700 }}>{h.cta || "Redeem"}</a>
      </div>
    );
  }
  if (b.type === "giftcard") {
    const h = p._hydrated || {};
    return (
      <div style={{ margin: "16px 0", padding: 24, background: "#141414", border: "1px solid #27272A", borderRadius: 12, textAlign: "center" }}>
        <div style={{ fontSize: 11, letterSpacing: 3, textTransform: "uppercase", opacity: 0.6 }}>Gift card</div>
        <div style={{ fontSize: 36, fontWeight: 800, margin: "12px 0" }}>${h.amount || 25}</div>
        <div style={{ fontSize: 13, opacity: 0.8 }}>{h.message || "Redeem at checkout."}</div>
      </div>
    );
  }
  if (b.type === "funnel") {
    const h = p._hydrated || {};
    return (
      <div style={{ margin: "16px 0", padding: 20, border: "1px solid #27272A", borderRadius: 10 }}>
        <div style={{ fontSize: 11, color: "#A1A1AA", letterSpacing: 2, textTransform: "uppercase", marginBottom: 6 }}>Featured</div>
        <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>{h.name || "Take a look"}</div>
        <a href={`/f/${h.slug || p.slug || ""}`} style={{ color: primary, fontWeight: 700, textDecoration: "none" }}>Explore →</a>
      </div>
    );
  }
  return null;
}

export default function PublicNewsletterPost() {
  const { slug, postSlug } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    axios.get(`${API}/api/newsletter/public/${slug}/p/${postSlug}`)
      .then((r) => setData(r.data))
      .catch((e) => setErr((e?.response?.data?.detail) || "Not found"));
  }, [slug, postSlug]);

  if (err) return <div style={{ minHeight: "100vh", background: "#0A0A0A", color: "#fff",
    display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "system-ui", flexDirection: "column" }}>
    <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 8 }}>Post not found</div>
    <div style={{ fontSize: 13, color: "#71717A" }}>{err}</div>
  </div>;
  if (!data) return <div style={{ minHeight: "100vh", background: "#0A0A0A", color: "#71717A",
    display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "system-ui" }}>Loading…</div>;

  const { pub, post } = data;
  const primary = pub.primary_color || "#005CEE";
  return (
    <div style={{ background: "#0A0A0A", color: "#fff", minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}
      data-testid="public-newsletter-post">
      <div style={{ maxWidth: 720, margin: "0 auto", padding: "60px 24px 120px" }}>
        <Link to={`/n/${slug}`} data-testid="back-to-pub"
          style={{ color: primary, fontSize: 12, textDecoration: "none", letterSpacing: 2, textTransform: "uppercase" }}>
          ← {pub.name}
        </Link>
        <h1 style={{ fontSize: 40, fontWeight: 800, margin: "24px 0 8px", lineHeight: 1.15 }}>{post.title}</h1>
        {post.subtitle && <div style={{ fontSize: 16, color: "#A1A1AA", marginBottom: 32 }}>{post.subtitle}</div>}
        <div style={{ fontSize: 11, color: "#71717A", marginBottom: 32, letterSpacing: 2, textTransform: "uppercase" }}>
          {post.sent_at ? new Date(post.sent_at).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) : ""}
        </div>
        <div>
          {(post.blocks || []).map((b) => <Block key={b.id} b={b} primary={primary} />)}
        </div>
        <div style={{ marginTop: 60, padding: 20, borderTop: "1px solid #27272A", textAlign: "center", color: "#71717A", fontSize: 12 }}>
          <Link to={`/n/${slug}`} style={{ color: primary, textDecoration: "none" }}>Subscribe to {pub.name}</Link>
        </div>
      </div>
      <CookieConsent theme={{ bg: "#0A0A0A", fg: "#fff", accent: primary }} />
    </div>
  );
}
