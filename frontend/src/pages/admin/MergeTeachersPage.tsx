import { useEffect, useState } from "react";
import { ArrowLeft, GitMerge, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useToast } from "../../components/Toast";
import { useConfirm } from "../../components/ConfirmDialog";
import {
  scanTeacherDuplicates, mergeTeachers,
  type DupCandidate, type DupTeacher,
} from "../../services/teachersAdmin";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", BORDER = "#e5e7eb";
const MUTED = "#64748b", GREEN = "#10b981", RED = "#ef4444", AMBER = "#f59e0b";

function TeacherCard({
  t, tone, onPick, picked,
}: { t: DupTeacher; tone: "keep" | "drop" | "neutral"; onPick: () => void; picked: boolean }) {
  const accent = tone === "keep" ? GREEN : tone === "drop" ? RED : BROWN;
  return (
    <div
      onClick={onPick}
      style={{
        flex: 1, minWidth: 220,
        background: picked ? accent + "15" : "#fff",
        border: `2px solid ${picked ? accent : BORDER}`,
        borderRadius: 12, padding: 14, cursor: "pointer",
        transition: "all 160ms ease",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontWeight: 800, color: "#0f172a", fontSize: "0.95rem" }}>{t.name}</div>
          <div style={{ fontSize: "0.72rem", color: MUTED, fontWeight: 700, letterSpacing: 0.5, textTransform: "uppercase", marginTop: 2 }}>
            {t.code}
          </div>
        </div>
        <div style={{
          background: (t.is_active ? GREEN : RED) + "22",
          color: t.is_active ? GREEN : RED,
          fontSize: "0.65rem", fontWeight: 800,
          padding: "2px 8px", borderRadius: 999,
        }}>{t.is_active ? "ACTIVE" : "INACTIVE"}</div>
      </div>
      <div style={{ marginTop: 10, fontSize: "0.78rem", color: "#334155" }}>
        <div><b>Role:</b> {t.role}</div>
        <div><b>Lessons:</b> {t.lr_count}</div>
        {t.email && <div><b>Email:</b> {t.email}</div>}
      </div>
      {tone !== "neutral" && (
        <div style={{
          marginTop: 10, fontSize: "0.72rem", fontWeight: 800,
          letterSpacing: 0.5, textTransform: "uppercase", color: accent,
        }}>
          {tone === "keep" ? "? Click to KEEP this one" : "Click to DROP this one ?"}
        </div>
      )}
    </div>
  );
}

function CandidateRow({
  c, onMerged,
}: { c: DupCandidate; onMerged: () => void }) {
  const toast = useToast();
  const { ask } = useConfirm();
  const [keepId, setKeepId] = useState<string>(c.a.id);
  const [busy, setBusy] = useState(false);

  async function doMerge() {
    const keep = keepId === c.a.id ? c.a : c.b;
    const drop = keepId === c.a.id ? c.b : c.a;
    const ok = await ask({
      title: `Merge "${drop.name}" into "${keep.name}"?`,
      message: (
        <>
          Every lesson assignment, timetable reference, and free-afternoon row
          pointing at <b>{drop.code}</b> will move to <b>{keep.code}</b>.<br /><br />
          The dropped teacher (<b>{drop.code}</b>) will be deactivated ? audit history preserved.
        </>
      ),
      variant: "warning",
      confirmLabel: "Merge",
    });
    if (!ok) return;

    setBusy(true);
    try {
      const r = await mergeTeachers(keep.id, drop.id);
      const total = Object.values(r.relinked).reduce((s, n) => s + n, 0);
      toast.push({
        type: "success",
        title: `Merged ${r.dropped.code} ? ${r.kept.code}`,
        message: `${total} reference(s) relinked. ${r.dropped.code} deactivated.`,
      });
      onMerged();
    } catch (e: any) {
      toast.push({
        type: "error", title: "Merge failed",
        message: e?.response?.data?.detail || String(e),
      });
    } finally { setBusy(false); }
  }

  return (
    <div style={{
      background: "#fff", border: `1px solid ${BORDER}`,
      borderRadius: 16, padding: 16, marginBottom: 16,
    }}>
      <div style={{ marginBottom: 10 }}>
        <span style={{
          background: AMBER + "22", color: "#92400e",
          fontSize: "0.7rem", fontWeight: 800,
          padding: "3px 10px", borderRadius: 999,
        }}>Reason: {c.reason}</span>
      </div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <TeacherCard
          t={c.a} tone="neutral" picked={keepId === c.a.id}
          onPick={() => setKeepId(c.a.id)}
        />
        <div style={{ display: "grid", placeItems: "center", color: MUTED, fontWeight: 800, fontSize: "1.5rem" }}>
          ?
        </div>
        <TeacherCard
          t={c.b} tone="neutral" picked={keepId === c.b.id}
          onPick={() => setKeepId(c.b.id)}
        />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
        <div style={{ fontSize: "0.75rem", color: MUTED }}>
          Keep: <b>{keepId === c.a.id ? c.a.code : c.b.code}</b> ?
          Drop: <b>{keepId === c.a.id ? c.b.code : c.a.code}</b>
        </div>
        <button
          disabled={busy}
          onClick={doMerge}
          style={{
            padding: "0.5rem 1rem", borderRadius: 8, border: "none",
            background: busy ? "#94a3b8" : BROWN, color: "#fff",
            cursor: busy ? "wait" : "pointer", fontWeight: 700,
            fontSize: "0.85rem", display: "inline-flex", alignItems: "center", gap: 6,
          }}
        >
          <GitMerge size={14} /> {busy ? "Merging..." : "Merge"}
        </button>
      </div>
    </div>
  );
}

export default function MergeTeachersPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [candidates, setCandidates] = useState<DupCandidate[]>([]);
  const [err, setErr] = useState("");

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const d = await scanTeacherDuplicates();
      setCandidates(d.candidates);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || String(e);
      setErr(msg);
      toast.push({ type: "error", title: "Scan failed", message: msg });
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  return (
    <div style={{ padding: "1.5rem", maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <button onClick={() => navigate("/admin")} style={{
          padding: "0.4rem 0.8rem", borderRadius: 6,
          border: `1px solid ${BORDER}`, background: "#fff",
          cursor: "pointer", fontSize: "0.82rem",
        }}>
          <ArrowLeft size={14} /> Back
        </button>
        <h1 style={{ margin: 0, fontSize: "1.4rem", color: BROWN, fontWeight: 700 }}>
          Merge Duplicate Teachers
        </h1>
        <div style={{ marginLeft: "auto" }}>
          <button onClick={load} style={{
            padding: "0.4rem 0.8rem", borderRadius: 6,
            border: `1px solid ${BORDER}`, background: "#fff",
            cursor: "pointer", fontSize: "0.82rem",
            display: "inline-flex", alignItems: "center", gap: 6,
          }}>
            <RefreshCw size={13} /> Rescan
          </button>
        </div>
      </div>

      {loading && <div style={{ padding: "2rem", textAlign: "center", color: MUTED }}>Scanning?</div>}

      {!loading && err && (
        <div style={{ padding: 14, background: "#fef2f2", color: "#991b1b", borderRadius: 12 }}>
          {err}
        </div>
      )}

      {!loading && !err && candidates.length === 0 && (
        <div style={{
          padding: "3rem 1rem", textAlign: "center", color: MUTED,
          background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 16,
        }}>
          <div style={{ fontSize: "1.1rem", fontWeight: 800, color: GREEN, marginBottom: 6 }}>
            ? No duplicates found
          </div>
          Every teacher appears exactly once.
        </div>
      )}

      {!loading && !err && candidates.length > 0 && (
        <>
          <div style={{
            padding: "10px 14px", background: "#fffbeb", color: "#92400e",
            borderRadius: 10, marginBottom: 16, fontSize: "0.85rem",
            border: "1px solid #fde68a",
          }}>
            <b>{candidates.length}</b> candidate pair(s). Click a card to choose which one to keep, then press Merge.
          </div>
          {candidates.map((c, i) => (
            <CandidateRow key={i} c={c} onMerged={load} />
          ))}
        </>
      )}
    </div>
  );
}
