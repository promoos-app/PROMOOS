import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, MessageSquare, Send } from "lucide-react";

/** Public review page — anyone with the share link can preview the newsletter
 *  and leave comments the merchant sees in their editor. No login required. */
export default function PublicNewsletterReview() {
  const { token } = useParams();
  const [html, setHtml] = useState("");
  const [loadingHtml, setLoadingHtml] = useState(true);
  const [error, setError] = useState("");
  const [comments, setComments] = useState([]);
  const [name, setName] = useState(() => localStorage.getItem("promoos_reviewer_name") || "");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);

  const loadHtml = async () => {
    setLoadingHtml(true);
    try {
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/newsletter/public/review/${token}`);
      if (!r.ok) throw new Error((await r.text()) || `HTTP ${r.status}`);
      const text = await r.text();
      setHtml(text);
    } catch (e) {
      setError(String(e.message || e));
    } finally { setLoadingHtml(false); }
  };
  const loadComments = async () => {
    try {
      const { data } = await api.get(`/newsletter/public/review/${token}/comments`);
      setComments(data);
    } catch (_) { /* silent — no comments yet */ }
  };

  useEffect(() => {
    loadHtml();
    loadComments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const submit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !body.trim()) return;
    setBusy(true);
    try {
      await api.post(`/newsletter/public/review/${token}/comments`,
        { reviewer_name: name.trim(), body: body.trim() });
      localStorage.setItem("promoos_reviewer_name", name.trim());
      setBody("");
      toast.success("Comment posted");
      loadComments();
    } catch (err) { toast.error(apiError(err)); }
    finally { setBusy(false); }
  };

  if (error) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] text-white flex items-center justify-center px-6">
        <div className="max-w-md text-center space-y-3">
          <div className="text-4xl">🔒</div>
          <h1 className="text-2xl font-bold">Review link unavailable</h1>
          <p className="text-sm text-[#A1A1AA]">{error}</p>
          <p className="text-xs text-[#71717A]">Ask the sender for a fresh link.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white">
      <div className="border-b border-[#27272A] bg-[#141414] px-6 py-3 flex items-center gap-3 sticky top-0 z-10">
        <MessageSquare className="w-5 h-5 text-fuchsia-400" />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold">Newsletter review</div>
          <div className="text-[11px] text-[#71717A]">
            You're viewing a preview. Leave feedback below — the sender will see it in their editor.
          </div>
        </div>
        <span className="hidden sm:inline text-[10px] uppercase tracking-widest px-2 py-1 rounded-full bg-fuchsia-500/20 text-fuchsia-300">
          Preview
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] max-w-7xl mx-auto">
        <div className="p-4 min-h-[60vh]">
          {loadingHtml ? (
            <div className="flex items-center justify-center h-96 text-[#71717A]">
              <Loader2 className="w-6 h-6 spin" />
            </div>
          ) : (
            <iframe title="review-preview" srcDoc={html}
              data-testid="review-iframe"
              className="w-full bg-white rounded-md shadow-2xl"
              style={{ minHeight: "80vh", border: 0 }}
              sandbox="allow-same-origin" />
          )}
        </div>
        <aside className="border-l border-[#27272A] bg-[#141414] p-4 flex flex-col gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-2">Leave feedback</div>
            <form onSubmit={submit} className="space-y-2" data-testid="review-comment-form">
              <Input value={name} onChange={(e) => setName(e.target.value)}
                placeholder="Your name" required maxLength={60}
                data-testid="review-name"
                className="bg-[#0A0A0A] border-[#27272A] text-white text-xs" />
              <Textarea value={body} onChange={(e) => setBody(e.target.value)}
                placeholder="What should be changed?" rows={4} required maxLength={2000}
                data-testid="review-body"
                className="bg-[#0A0A0A] border-[#27272A] text-white text-xs" />
              <Button type="submit" disabled={busy || !name.trim() || !body.trim()}
                data-testid="review-submit"
                className="btn-primary rounded-md gap-2 w-full h-9">
                {busy ? <Loader2 className="w-4 h-4 spin" /> : <Send className="w-4 h-4" />}
                Post comment
              </Button>
            </form>
          </div>
          <div className="pt-3 border-t border-[#27272A]">
            <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-2">
              Comments ({comments.length})
            </div>
            {comments.length === 0 ? (
              <div className="text-xs text-[#71717A] italic">Be the first to leave feedback.</div>
            ) : (
              <div className="space-y-2 max-h-[50vh] overflow-y-auto">
                {comments.map((c) => (
                  <div key={c.id} data-testid={`review-comment-${c.id}`}
                    className={`rounded-md p-3 border text-xs ${
                      c.resolved
                        ? "border-emerald-500/30 bg-emerald-500/5 opacity-70"
                        : "border-fuchsia-500/30 bg-fuchsia-500/5"
                    }`}>
                    <div className="flex items-center gap-1 mb-1">
                      <span className="font-semibold text-white">{c.reviewer_name}</span>
                      {c.resolved && (
                        <span className="ml-1 text-[9px] uppercase tracking-widest text-emerald-300">Resolved</span>
                      )}
                      <span className="ml-auto text-[10px] text-[#71717A]">
                        {new Date(c.created_at).toLocaleString(undefined,
                          { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                    <div className="text-[#E4E4E7] whitespace-pre-wrap">{c.body}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
