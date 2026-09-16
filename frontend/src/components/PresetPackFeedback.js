import { useEffect, useState } from "react";
import { Star, MessageCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "@/lib/api";

/**
 * PresetPackFeedback — rating + qualitative comment UI for marketplace preset packs.
 *
 * Shown alongside the tap-to-apply preset chips in the Coupon and Gift Card
 * studios so agencies see quality signal AND workspaces can leave a note.
 * A pack is any object returned by `GET /api/preset-packs?scope=…` before
 * flattening into individual presets.
 */
export default function PresetPackFeedback({ scope }) {
  const [packs, setPacks] = useState([]);
  const [comments, setComments] = useState({});
  const [drafts, setDrafts] = useState({});
  const [busy, setBusy] = useState(null);
  const [loadingComments, setLoadingComments] = useState(null);
  const [expanded, setExpanded] = useState(false);

  const load = () => {
    api.get(`/preset-packs?scope=${scope}`)
      .then((r) => setPacks(r.data || []))
      .catch(() => setPacks([]));
  };
  useEffect(() => { load(); }, [scope]);

  const toggleComments = async (pid) => {
    if (comments[pid] != null) { setComments((s) => ({ ...s, [pid]: null })); return; }
    setLoadingComments(pid);
    try {
      const { data } = await api.get(`/preset-packs/${pid}/comments`);
      setComments((s) => ({ ...s, [pid]: data.comments || [] }));
    } catch (e) { toast.error(apiError(e)); } finally { setLoadingComments(null); }
  };

  const rate = async (pid, stars) => {
    setBusy(pid);
    try {
      const comment = (drafts[pid] || "").trim();
      await api.post(`/preset-packs/${pid}/rate`, { stars, comment: comment || undefined });
      toast.success(comment ? `Rated ${stars}★ with a note` : `Rated ${stars}★`);
      setDrafts((s) => ({ ...s, [pid]: "" }));
      if (comments[pid] != null) {
        try {
          const { data } = await api.get(`/preset-packs/${pid}/comments`);
          setComments((s) => ({ ...s, [pid]: data.comments || [] }));
        } catch (_) { /* non-fatal */ }
      }
      load();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(null); }
  };

  if (!packs.length) return null;

  return (
    <div className="mt-3 border-t border-[#27272A] pt-3" data-testid={`preset-pack-feedback-${scope}`}>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        data-testid={`preset-pack-feedback-toggle-${scope}`}
        className="text-[10px] uppercase tracking-widest text-[#71717A] hover:text-[#CCFF00] inline-flex items-center gap-1"
      >
        <MessageCircle className="w-3 h-3" />
        {expanded ? "Hide" : "Show"} marketplace pack feedback · {packs.length}
      </button>
      {expanded && (
        <div className="mt-2 space-y-2">
          {packs.map((p) => (
            <div key={p.id} className="rounded-md bg-[#0A0A0A] border border-[#27272A] p-2.5"
              data-testid={`preset-pack-feedback-${p.id}`}>
              <div className="flex items-center gap-2 flex-wrap">
                <div className="font-medium text-xs flex-1 min-w-0 truncate" title={p.name}>{p.name}</div>
                <div className="flex items-center gap-0.5" data-testid={`preset-pack-stars-${p.id}`}>
                  {[1, 2, 3, 4, 5].map((s) => {
                    const filled = s <= Math.round(p.rating_avg || 0);
                    return (
                      <button
                        key={s}
                        onClick={() => rate(p.id, s)}
                        disabled={busy === p.id}
                        data-testid={`preset-pack-rate-${p.id}-${s}`}
                        title={`Rate ${s} star${s === 1 ? "" : "s"}`}
                        className="p-0.5 hover:scale-110 transition-transform"
                      >
                        <Star className={`w-3 h-3 ${filled ? "fill-[#CCFF00] text-[#CCFF00]" : "text-[#3F3F46]"}`} />
                      </button>
                    );
                  })}
                  <span className="text-[10px] text-[#71717A] ml-1">
                    {(p.rating_avg || 0).toFixed(1)} · {p.rating_count || 0}
                  </span>
                  <button
                    onClick={() => toggleComments(p.id)}
                    data-testid={`preset-pack-comments-toggle-${p.id}`}
                    title="Toggle qualitative notes"
                    className="ml-1 p-1 rounded hover:bg-white/5 text-[#71717A] hover:text-[#CCFF00]"
                  >
                    {loadingComments === p.id
                      ? <Loader2 className="w-3 h-3 spin" />
                      : <MessageCircle className="w-3 h-3" />}
                  </button>
                </div>
              </div>
              <input
                type="text" maxLength={200}
                value={drafts[p.id] || ""}
                onChange={(e) => setDrafts((s) => ({ ...s, [p.id]: e.target.value }))}
                placeholder="Add a one-line note (optional) then tap stars…"
                data-testid={`preset-pack-comment-input-${p.id}`}
                className="mt-1.5 w-full h-7 rounded bg-[#141414] border border-[#27272A] px-2 text-[11px] text-white placeholder:text-[#3F3F46] focus:border-[#CCFF00]/40 focus:outline-none"
              />
              {comments[p.id] != null && (
                <div className="mt-2 rounded border border-[#27272A] bg-[#141414] p-2 max-h-32 overflow-y-auto space-y-1"
                  data-testid={`preset-pack-comments-${p.id}`}>
                  {comments[p.id].length === 0 ? (
                    <div className="text-[10px] text-[#71717A]">No notes yet — be first to leave one.</div>
                  ) : (
                    comments[p.id].map((c, i) => (
                      <div key={i} className="text-[10px] flex items-start gap-2"
                        data-testid={`preset-pack-comment-${p.id}-${i}`}>
                        <span className="text-[#CCFF00] font-bold shrink-0">{c.stars}★</span>
                        <div className="min-w-0">
                          <div className="text-[#A1A1AA] break-words">{c.comment}</div>
                          <div className="text-[9px] text-[#71717A]">— {c.workspace_name}</div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
