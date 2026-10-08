import { useEffect, useState } from "react";
import {
  ArrowLeft, CalendarDays, ChevronLeft, ChevronRight,
  Moon, Sparkles, Sun, Trash2, UserPlus,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useToast } from "../../components/Toast";
import { useConfirm } from "../../components/ConfirmDialog";
import { Avatar } from "../../components/Avatar";
import {
  getDutyRoster, assignDuty, unassignDuty, autoRotateDuty,
  type DutyRoster, type DutyShiftKind, type DutyTeacher, type DutyWeek,
} from "../../services/dutyRoster";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", BORDER = "#e5e7eb";
const MUTED = "#64748b", GREEN = "#10b981", AMBER = "#f59e0b";
const BLUE = "#0ea5e9", RED = "#ef4444";

function fmtRange(a: string, b: string): string {
  const da = new Date(a + "T00:00:00");
  const db = new Date(b + "T00:00:00");
  const mo: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  return `${da.toLocaleDateString(undefined, mo)} – ${db.toLocaleDateString(undefined, mo)}`;
}

function weekLabel(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function DutyRosterPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { ask } = useConfirm();

  const [roster, setRoster] = useState<DutyRoster | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [weeksToShow, setWeeksToShow] = useState(8);

  // Assign modal
  const [assignCell, setAssignCell] = useState<{ week_start: string; shift: DutyShiftKind } | null>(null);
  const [pickTeacher, setPickTeacher] = useState("");
  const [busy, setBusy] = useState(false);

  // Auto-rotate modal
  const [rotateOpen, setRotateOpen] = useState(false);
  const [rotateStart, setRotateStart] = useState("");
  const [rotateWeeks, setRotateWeeks] = useState(13);
  const [preview, setPreview] = useState<any[] | null>(null);

  async function load(weekStart?: string) {
    setLoading(true);
    setErr("");
    try {
      const d = await getDutyRoster(weekStart, weeksToShow);
      setRoster(d);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || String(e);
      setErr(msg);
      toast.push({ type: "error", title: "Could not load roster", message: msg });
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const navWeeks = (delta: number) => {
    if (!roster) return;
    const d = new Date(roster.week_start + "T00:00:00");
    d.setDate(d.getDate() + delta * weeksToShow * 7);
    load(d.toISOString().slice(0, 10));
  };

  const eligible = (shift: DutyShiftKind): DutyTeacher[] => {
    if (!roster) return [];
    return roster.eligible_teachers.filter(t => (shift === "DAY" ? t.day_ok : t.night_ok));
  };

  async function doAssign() {
    if (!assignCell || !pickTeacher) return;
    setBusy(true);
    try {
      await assignDuty({
        week_start: assignCell.week_start,
        shift: assignCell.shift,
        teacher_id: pickTeacher,
      });
      toast.push({ type: "success", title: "Assigned" });
      setAssignCell(null); setPickTeacher("");
      await load(roster?.week_start);
    } catch (e: any) {
      toast.push({
        type: "error", title: "Assign failed",
        message: e?.response?.data?.detail || String(e),
      });
    } finally { setBusy(false); }
  }

  async function doUnassign(id: string, who: string) {
    const ok = await ask({
      title: `Clear ${who}?`,
      message: "The teacher will be removed from this week's duty.",
      variant: "warning",
      confirmLabel: "Clear",
    });
    if (!ok) return;
    try {
      await unassignDuty(id);
      toast.push({ type: "success", title: "Cleared" });
      await load(roster?.week_start);
    } catch (e: any) {
      toast.push({ type: "error", title: "Failed", message: e?.response?.data?.detail || String(e) });
    }
  }

  async function openRotate() {
    setRotateOpen(true);
    setPreview(null);
    // default to current roster window start
    if (roster) setRotateStart(roster.week_start);
  }

  async function generatePreview() {
    if (!rotateStart) return;
    setBusy(true);
    try {
      const r = await autoRotateDuty({ start: rotateStart, weeks: rotateWeeks, apply: false });
      setPreview(r.plan);
    } catch (e: any) {
      toast.push({ type: "error", title: "Could not plan rotation", message: e?.response?.data?.detail || String(e) });
    } finally { setBusy(false); }
  }

  async function applyRotation() {
    if (!rotateStart) return;
    setBusy(true);
    try {
      const r = await autoRotateDuty({ start: rotateStart, weeks: rotateWeeks, apply: true });
      toast.push({
        type: "success",
        title: "Rotation applied",
        message: `${r.plan.length} week(s) planned`,
      });
      setRotateOpen(false); setPreview(null);
      await load(rotateStart);
    } catch (e: any) {
      toast.push({ type: "error", title: "Apply failed", message: e?.response?.data?.detail || String(e) });
    } finally { setBusy(false); }
  }

  function Slot({ cell, weekStart, shift }: { cell: any; weekStart: string; shift: DutyShiftKind }) {
    const isDay = shift === "DAY";
    const accent = isDay ? AMBER : BLUE;
    const Icon = isDay ? Sun : Moon;
    if (cell) {
      return (
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "10px 12px", borderRadius: 10,
          background: accent + "11", border: `1px solid ${accent}55`,
        }}>
          <Avatar name={cell.teacher_name} code={cell.teacher_code} size={36} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 800, color: "#0f172a", fontSize: "0.85rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {cell.teacher_name}
            </div>
            <div style={{ fontSize: "0.68rem", color: MUTED, fontWeight: 700, letterSpacing: 0.4 }}>
              {cell.teacher_code}
            </div>
          </div>
          <button
            title="Clear"
            onClick={() => doUnassign(cell.id, cell.teacher_name)}
            style={{ background: "transparent", border: "none", cursor: "pointer", color: RED, padding: 4 }}
          ><Trash2 size={14} /></button>
        </div>
      );
    }
    return (
      <button
        onClick={() => { setAssignCell({ week_start: weekStart, shift }); setPickTeacher(""); }}
        style={{
          display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
          padding: "14px 12px", borderRadius: 10, width: "100%",
          border: `1px dashed ${accent}88`, background: accent + "08",
          color: accent, fontWeight: 700, fontSize: "0.8rem", cursor: "pointer",
        }}
      >
        <Icon size={13} /> <UserPlus size={13} /> Assign
      </button>
    );
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: 1200, margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        <button onClick={() => navigate("/admin")} style={{
          padding: "0.4rem 0.8rem", borderRadius: 6,
          border: `1px solid ${BORDER}`, background: "#fff",
          cursor: "pointer", fontSize: "0.82rem",
        }}>
          <ArrowLeft size={14} /> Back
        </button>
        <CalendarDays size={22} color={BROWN} />
        <h1 style={{ margin: 0, fontSize: "1.4rem", color: BROWN, fontWeight: 700 }}>
          Duty Roster
        </h1>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
          <button onClick={() => navWeeks(-1)} style={{ padding: "0.4rem 0.6rem", borderRadius: 6, border: `1px solid ${BORDER}`, background: "#fff", cursor: "pointer" }}>
            <ChevronLeft size={14} />
          </button>
          <select
            value={weeksToShow}
            onChange={(e) => { const n = Number(e.target.value); setWeeksToShow(n); load(roster?.week_start); }}
            style={{ padding: "0.35rem 0.6rem", borderRadius: 6, border: `1px solid ${BORDER}`, background: "#fff", fontSize: "0.82rem" }}
          >
            <option value={4}>4 weeks</option>
            <option value={8}>8 weeks</option>
            <option value={13}>13 weeks</option>
            <option value={26}>26 weeks</option>
          </select>
          <button onClick={() => navWeeks(1)} style={{ padding: "0.4rem 0.6rem", borderRadius: 6, border: `1px solid ${BORDER}`, background: "#fff", cursor: "pointer" }}>
            <ChevronRight size={14} />
          </button>
          <button
            onClick={openRotate}
            style={{
              marginLeft: 6, padding: "0.45rem 0.9rem", borderRadius: 8,
              border: "none", background: BROWN, color: "#fff",
              cursor: "pointer", fontSize: "0.82rem", fontWeight: 700,
              display: "inline-flex", alignItems: "center", gap: 6,
            }}
          >
            <Sparkles size={14} /> Auto-rotate
          </button>
        </div>
      </header>

      {loading && <div style={{ padding: "2rem", textAlign: "center", color: MUTED }}>Loading…</div>}
      {err && !loading && <div style={{ padding: 14, background: "#fef2f2", color: "#991b1b", borderRadius: 12 }}>{err}</div>}

      {roster && !loading && (
        <>
          <div style={{
            display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8,
            padding: "10px 14px", background: "#f8fafc", borderRadius: 10,
            fontSize: "0.72rem", fontWeight: 800, letterSpacing: 0.5,
            color: MUTED, textTransform: "uppercase", marginBottom: 8,
          }}>
            <div style={{ color: AMBER }}><Sun size={11} style={{ verticalAlign: "middle", marginRight: 4 }} /> Day — 6am to 6pm</div>
            <div style={{ color: BLUE }}><Moon size={11} style={{ verticalAlign: "middle", marginRight: 4 }} /> Night — 6pm to 6am</div>
          </div>

          <div style={{ display: "grid", gap: 10 }}>
            {roster.weeks.map((w: DutyWeek) => (
              <div key={w.week_start} style={{
                display: "grid", gridTemplateColumns: "220px 1fr 1fr", gap: 14,
                alignItems: "center",
                background: "#fff", border: `1px solid ${BORDER}`,
                borderRadius: 14, padding: "12px 16px",
              }}>
                <div>
                  <div style={{ fontSize: "0.9rem", fontWeight: 800, color: BROWN2 }}>
                    {fmtRange(w.week_start, w.week_end)}
                  </div>
                  <div style={{ fontSize: "0.68rem", color: MUTED, marginTop: 2 }}>
                    Monday to Sunday
                  </div>
                </div>
                <Slot cell={w.day} weekStart={w.week_start} shift="DAY" />
                <Slot cell={w.night} weekStart={w.week_start} shift="NIGHT" />
              </div>
            ))}
          </div>
        </>
      )}

      {/* Assign modal */}
      {assignCell && (
        <div onClick={() => setAssignCell(null)} style={{
          position: "fixed", inset: 0, zIndex: 10000,
          background: "rgba(10,18,29,0.45)", backdropFilter: "blur(4px)",
          display: "grid", placeItems: "center",
        }}>
          <div onClick={(e) => e.stopPropagation()} style={{
            width: 460, maxWidth: "calc(100vw - 2rem)",
            background: "#fff", borderRadius: 16, padding: "1.25rem 1.5rem",
            boxShadow: "0 24px 60px rgba(10,18,29,0.28)",
          }}>
            <div style={{ fontWeight: 800, fontSize: "1.05rem", color: "#1e2e40", marginBottom: 4 }}>
              Assign {assignCell.shift === "DAY" ? "Day" : "Night"} duty
            </div>
            <div style={{ fontSize: "0.82rem", color: MUTED, marginBottom: 12 }}>
              Week of {weekLabel(assignCell.week_start)} · {assignCell.shift === "DAY" ? "6am–6pm" : "6pm–6am"}
            </div>
            <label style={{ display: "block", fontSize: "0.72rem", fontWeight: 800, letterSpacing: 0.5, color: MUTED, textTransform: "uppercase", marginBottom: 4 }}>
              Teacher
            </label>
            <select
              value={pickTeacher}
              onChange={(e) => setPickTeacher(e.target.value)}
              style={{ width: "100%", padding: "0.55rem 0.7rem", borderRadius: 8, border: `1px solid ${BORDER}`, fontSize: "0.88rem", background: "#fff" }}
            >
              <option value="">— Select —</option>
              {eligible(assignCell.shift).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.code} · {t.name}{t.preference === "DAY_ONLY" ? " · day only" : ""}
                </option>
              ))}
            </select>
            {assignCell.shift === "NIGHT" && (
              <div style={{ fontSize: "0.72rem", color: MUTED, marginTop: 6 }}>
                Only on-campus teachers appear here.
              </div>
            )}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
              <button onClick={() => setAssignCell(null)} style={{
                padding: "0.55rem 1rem", borderRadius: 8, border: `1px solid ${BORDER}`,
                background: "#fff", cursor: "pointer", fontWeight: 600, fontSize: "0.85rem", color: "#475569",
              }}>Cancel</button>
              <button
                disabled={!pickTeacher || busy}
                onClick={doAssign}
                style={{
                  padding: "0.55rem 1.1rem", borderRadius: 8, border: "none",
                  background: !pickTeacher || busy ? "#94a3b8" : BROWN,
                  color: "#fff", cursor: "pointer", fontWeight: 700, fontSize: "0.85rem",
                }}
              >{busy ? "Assigning…" : "Assign"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Auto-rotate modal */}
      {rotateOpen && (
        <div onClick={() => setRotateOpen(false)} style={{
          position: "fixed", inset: 0, zIndex: 10000,
          background: "rgba(10,18,29,0.45)", backdropFilter: "blur(4px)",
          display: "grid", placeItems: "center",
        }}>
          <div onClick={(e) => e.stopPropagation()} style={{
            width: 720, maxWidth: "calc(100vw - 2rem)",
            maxHeight: "90vh", overflowY: "auto",
            background: "#fff", borderRadius: 16, padding: "1.5rem 1.75rem",
            boxShadow: "0 24px 60px rgba(10,18,29,0.28)",
          }}>
            <div style={{ fontWeight: 800, fontSize: "1.15rem", color: "#1e2e40", marginBottom: 4 }}>
              ✨ Auto-rotate duty
            </div>
            <div style={{ fontSize: "0.85rem", color: MUTED, marginBottom: 16 }}>
              Generates a fair rotation across the weeks. Each teacher gets 2–3 duties depending on term length.
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
              <div>
                <label style={{ display: "block", fontSize: "0.72rem", fontWeight: 800, letterSpacing: 0.5, color: MUTED, textTransform: "uppercase", marginBottom: 4 }}>Start week</label>
                <input
                  type="date"
                  value={rotateStart}
                  onChange={(e) => setRotateStart(e.target.value)}
                  style={{ width: "100%", padding: "0.55rem 0.7rem", borderRadius: 8, border: `1px solid ${BORDER}`, fontSize: "0.88rem" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.72rem", fontWeight: 800, letterSpacing: 0.5, color: MUTED, textTransform: "uppercase", marginBottom: 4 }}>Number of weeks</label>
                <input
                  type="number"
                  min={1}
                  max={26}
                  value={rotateWeeks}
                  onChange={(e) => setRotateWeeks(Number(e.target.value) || 1)}
                  style={{ width: "100%", padding: "0.55rem 0.7rem", borderRadius: 8, border: `1px solid ${BORDER}`, fontSize: "0.88rem" }}
                />
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
              <button
                onClick={generatePreview}
                disabled={busy || !rotateStart}
                style={{
                  padding: "0.5rem 1rem", borderRadius: 8, border: `1px solid ${BORDER}`,
                  background: "#fff", cursor: "pointer", fontWeight: 700, fontSize: "0.85rem", color: BROWN,
                }}
              >{busy ? "…" : "Preview"}</button>
              {preview && preview.length > 0 && (
                <button
                  onClick={applyRotation}
                  disabled={busy}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: 8, border: "none",
                    background: GREEN, color: "#fff", cursor: "pointer", fontWeight: 700, fontSize: "0.85rem",
                  }}
                >Apply this rotation</button>
              )}
            </div>
            {preview && (
              <div style={{ border: `1px solid ${BORDER}`, borderRadius: 10, overflow: "hidden" }}>
                <div style={{
                  padding: "10px 14px", background: "#f8fafc", borderBottom: `1px solid ${BORDER}`,
                  fontSize: "0.72rem", fontWeight: 800, textTransform: "uppercase",
                  letterSpacing: 0.5, color: MUTED,
                }}>Preview · {preview.length} week(s)</div>
                {preview.map((row: any, i: number) => (
                  <div key={i} style={{
                    padding: "10px 14px",
                    display: "grid", gridTemplateColumns: "180px 1fr 1fr", gap: 10,
                    alignItems: "center", fontSize: "0.85rem",
                    borderTop: i === 0 ? "none" : "1px solid #f1f5f9",
                  }}>
                    <div style={{ fontWeight: 700, color: BROWN2 }}>{fmtRange(row.week_start, row.week_end)}</div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Sun size={12} color={AMBER} />
                      <b>{row.day.code}</b> {row.day.name}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Moon size={12} color={BLUE} />
                      <b>{row.night.code}</b> {row.night.name}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
              <button onClick={() => setRotateOpen(false)} style={{
                padding: "0.55rem 1rem", borderRadius: 8, border: `1px solid ${BORDER}`,
                background: "#fff", cursor: "pointer", fontWeight: 600, fontSize: "0.85rem", color: "#475569",
              }}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
