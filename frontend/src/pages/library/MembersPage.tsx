import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Users, RefreshCw, Wallet, Loader2, Mail, Phone,
  GraduationCap, Briefcase, BookOpen, AlertCircle, TrendingUp,
  XCircle, ArrowLeftRight,
} from "lucide-react";
import * as lib from "../../services/library";

const LIB_BG =
  "radial-gradient(1400px 600px at 85% -5%, rgba(122,78,42,0.07), transparent 60%)," +
  "radial-gradient(900px 500px at -5% 20%, rgba(30,64,175,0.05), transparent 55%)," +
  "linear-gradient(180deg, #f5ecd9 0%, #ecdfc8 100%)";

type Stats = { active: number; returned: number; overdue: number; lost: number; finesUnpaid: number; finesPaid: number; total: number };
type MemberWithStats = lib.Member & { _stats?: Stats; class_name?: string };
type StatusFilter = "all" | "active" | "overdue" | "unpaid" | "paid" | "lost";

const TYPE_COLOURS: Record<string, string> = {
  STUDENT: "#1e3a8a", TEACHER: "#0e7490", STAFF: "#7e22ce",
  LIBRARIAN: "#a16207", EXTERNAL: "#4d7c0f",
};
const TYPE_LABEL: Record<string, string> = {
  STUDENT: "Student", TEACHER: "Teacher", STAFF: "Staff",
  LIBRARIAN: "Librarian", EXTERNAL: "External",
};
const FILTER_CHIPS: { key: StatusFilter; label: string; colour: string; Icon: any }[] = [
  { key: "all",     label: "All",           colour: "#475569", Icon: Users },
  { key: "active",  label: "Active loans",  colour: "#1e3a8a", Icon: BookOpen },
  { key: "overdue", label: "Overdue",       colour: "#991b1b", Icon: AlertCircle },
  { key: "unpaid",  label: "Unpaid fines",  colour: "#a16207", Icon: Wallet },
  { key: "paid",    label: "Paid fines",    colour: "#166534", Icon: TrendingUp },
  { key: "lost",    label: "Lost books",    colour: "#7e22ce", Icon: XCircle },
];

function initials(name: string): string {
  const p = name.trim().split(/\s+/).filter(Boolean);
  if (!p.length) return "?";
  if (p.length === 1) return p[0].slice(0, 2).toUpperCase();
  return (p[0][0] + p[p.length - 1][0]).toUpperCase();
}

export default function MembersPage() {
  const [rows, setRows] = useState<MemberWithStats[]>([]);
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncNotice, setSyncNotice] = useState("");
  const [error, setError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try {
      const r = await lib.listMembers({ q: q || undefined, type: type || undefined });
      const members = r as MemberWithStats[];
      setRows(members);
      await Promise.all(members.map(async (m) => {
        try {
          const loans = await lib.listMemberLoans(m.id);
          const stats: Stats = {
            active: loans.filter((l) => l.status === "ACTIVE").length,
            returned: loans.filter((l) => l.status === "RETURNED").length,
            overdue: loans.filter((l) => l.status === "OVERDUE").length,
            lost: loans.filter((l) => l.status === "LOST").length,
            finesUnpaid: loans.reduce((s, l) =>
              s + Math.max(0, Number(l.fine_accrued || 0) - Number(l.fine_paid || 0)), 0),
            finesPaid: loans.reduce((s, l) => s + Number(l.fine_paid || 0), 0),
            total: loans.length,
          };
          setRows((prev) => prev.map((x) => x.id === m.id ? { ...x, _stats: stats } : x));
        } catch { /* leave without stats */ }
      }));
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Could not load members.");
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); /* eslint-disable-next-line */ }, [q, type]);

  async function doSync() {
    setSyncing(true); setSyncNotice("");
    try {
      const r = await lib.rosterSync();
      setSyncNotice(`Synced: +${r.created_students} students, +${r.created_teachers} teachers, ${r.updated} updated.`);
      await load();
    } catch (e: any) {
      setSyncNotice(e?.response?.data?.detail || "Sync failed.");
    } finally { setSyncing(false); }
  }

  // Apply status filter
  const filteredRows = useMemo(() => {
    if (statusFilter === "all") return rows;
    return rows.filter((m) => {
      const st = m._stats;
      if (!st) return false;
      switch (statusFilter) {
        case "active":  return st.active > 0;
        case "overdue": return st.overdue > 0;
        case "unpaid":  return st.finesUnpaid > 0;
        case "paid":    return st.finesPaid > 0;
        case "lost":    return st.lost > 0;
        default:        return true;
      }
    });
  }, [rows, statusFilter]);

  // Group: type -> (students: class_name | others: "All") -> list
  const grouped = useMemo(() => {
    const out: Record<string, Record<string, MemberWithStats[]>> = {};
    for (const r of filteredRows) {
      const t = r.member_type || "OTHER";
      out[t] ||= {};
      const sub = t === "STUDENT" ? ((r.class_name || "Unassigned Class") as string) : "All";
      out[t][sub] ||= [];
      out[t][sub].push(r);
    }
    return out;
  }, [filteredRows]);

  // Counts per chip
  const chipCounts = useMemo(() => {
    const c: Record<StatusFilter, number> = { all: rows.length, active: 0, overdue: 0, unpaid: 0, paid: 0, lost: 0 };
    for (const m of rows) {
      const st = m._stats;
      if (!st) continue;
      if (st.active > 0) c.active++;
      if (st.overdue > 0) c.overdue++;
      if (st.finesUnpaid > 0) c.unpaid++;
      if (st.finesPaid > 0) c.paid++;
      if (st.lost > 0) c.lost++;
    }
    return c;
  }, [rows]);

  return (
    <div style={{ padding: "1.5rem", minHeight: "100vh", background: LIB_BG }}>
      <div style={{ marginBottom: "1.5rem", padding: "1.5rem",
                    background: "rgba(255,255,255,0.94)", borderRadius: 16,
                    borderLeft: "6px solid #1e3a8a", boxShadow: "0 6px 18px rgba(15,23,42,0.08)",
                    display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <span style={{ fontSize: "0.72rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 800 }}>LIBRARY MANAGEMENT</span>
          <h1 style={{ margin: "0.35rem 0 0", color: "#111827", fontSize: "1.6rem", fontWeight: 800 }}>Members</h1>
          <p style={{ margin: "0.25rem 0 0", color: "#748095", fontSize: "0.9rem" }}>
            {filteredRows.length} of {rows.length} member{rows.length === 1 ? "" : "s"}
            {statusFilter !== "all" ? ` · ${FILTER_CHIPS.find((c) => c.key === statusFilter)?.label}` : ""}
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignSelf: "flex-start" }}>
          <button type="button" onClick={doSync} disabled={syncing} className="mem-btn mem-btn-teal">
            {syncing ? <Loader2 size={14} className="spin" /> : <RefreshCw size={14} />}
            {syncing ? "Syncing…" : "Sync from roster"}
          </button>
          <Link to="/library/members/new" className="mem-btn mem-btn-primary">Add Member</Link>
        </div>
      </div>

      {syncNotice ? (
        <div style={{ background: "#ecfdf5", border: "1px solid #86efac", color: "#065f46",
                      padding: "0.6rem 0.9rem", borderRadius: 8, fontSize: "0.85rem",
                      marginBottom: "1rem", fontWeight: 600 }}>{syncNotice}</div>
      ) : null}
      {error ? <div style={{ background: "#fef2f2", border: "1px solid #fecaca", color: "#7f1d1d",
                             padding: "0.6rem 0.9rem", borderRadius: 8, marginBottom: "1rem" }}>{error}</div> : null}

      {/* Filter chips row */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        {FILTER_CHIPS.map(({ key, label, colour, Icon }) => {
          const active = statusFilter === key;
          const count = chipCounts[key];
          return (
            <button key={key} onClick={() => setStatusFilter(key)}
                    style={{
                      display: "inline-flex", alignItems: "center", gap: "0.4rem",
                      padding: "0.5rem 0.85rem", borderRadius: 999,
                      border: `2px solid ${active ? colour : "#cbd5e1"}`,
                      background: active ? colour : "rgba(255,255,255,0.9)",
                      color: active ? "#fff" : "#334155",
                      fontSize: "0.8rem", fontWeight: 800, cursor: "pointer",
                      fontFamily: "inherit",
                      transition: "transform 180ms ease, background 180ms ease, border-color 180ms ease",
                    }}>
              <Icon size={13} />
              {label}
              <span style={{
                background: active ? "rgba(255,255,255,0.25)" : "#f1f5f9",
                color: active ? "#fff" : "#475569",
                padding: "0.05rem 0.45rem", borderRadius: 999,
                fontSize: "0.7rem", fontWeight: 800,
              }}>{count}</span>
            </button>
          );
        })}
      </div>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        <input value={q} onChange={(e) => setQ(e.target.value)}
               placeholder="Search name or member number…"
               style={{ flex: "1 1 240px", padding: "0.65rem 0.85rem", borderRadius: 10,
                        border: "1px solid #cbd5e1", fontSize: "0.9rem",
                        background: "rgba(255,255,255,0.9)", fontFamily: "inherit" }} />
        <select value={type} onChange={(e) => setType(e.target.value)}
                style={{ padding: "0.65rem 0.85rem", borderRadius: 10, border: "1px solid #cbd5e1",
                         fontWeight: 700, background: "rgba(255,255,255,0.9)", fontFamily: "inherit" }}>
          <option value="">All types</option>
          <option value="STUDENT">Students</option>
          <option value="TEACHER">Teachers</option>
          <option value="STAFF">Staff</option>
          <option value="LIBRARIAN">Librarians</option>
          <option value="EXTERNAL">External</option>
        </select>
      </div>

      {loading ? (
        <div style={{ padding: "3rem", color: "#64748b", textAlign: "center" }}>
          <Loader2 size={22} className="spin" style={{ marginBottom: "0.5rem" }} />
          <div>Loading members…</div>
        </div>
      ) : filteredRows.length === 0 ? (
        <div style={{ padding: "3rem 2rem", background: "rgba(255,255,255,0.94)",
                      borderRadius: 16, textAlign: "center", color: "#64748b",
                      border: "2px dashed #cbd5e1" }}>
          No members match those filters.
        </div>
      ) : (
        Object.entries(grouped).map(([typeKey, byClass]) => {
          const typeTotal = Object.values(byClass).reduce((s, arr) => s + arr.length, 0);
          return (
            <section key={typeKey} style={{ marginBottom: "2.5rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "1.1rem" }}>
                <span style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem",
                               padding: "0.45rem 1rem", borderRadius: 999,
                               background: TYPE_COLOURS[typeKey] || "#475569", color: "#fff",
                               fontSize: "0.85rem", fontWeight: 800,
                               boxShadow: "0 3px 10px rgba(15,23,42,0.18)" }}>
                  {typeKey === "STUDENT" ? <GraduationCap size={14} /> : typeKey === "TEACHER" ? <Users size={14} /> : <Briefcase size={14} />}
                  {TYPE_LABEL[typeKey] || typeKey}
                </span>
                <span style={{ color: "#748095", fontSize: "0.82rem", fontWeight: 600 }}>
                  {typeTotal} member{typeTotal === 1 ? "" : "s"}
                  {typeKey === "STUDENT" ? ` · ${Object.keys(byClass).length} class${Object.keys(byClass).length === 1 ? "" : "es"}` : ""}
                </span>
              </div>

              {Object.entries(byClass).sort(([a], [b]) => a.localeCompare(b)).map(([subKey, list]) => (
                <div key={subKey} style={{ marginBottom: "1.5rem" }}>
                  {subKey !== "All" ? (
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.85rem",
                                  paddingLeft: "0.3rem" }}>
                      <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%",
                                     background: TYPE_COLOURS[typeKey] || "#475569" }} />
                      <span style={{ fontSize: "0.9rem", fontWeight: 800, color: "#111827" }}>
                        {subKey}
                      </span>
                      <span style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 600 }}>
                        {list.length} member{list.length === 1 ? "" : "s"}
                      </span>
                    </div>
                  ) : null}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1rem" }}>
                    {list.map((m, i) => <MemberTile key={m.id} member={m} index={i} />)}
                  </div>
                </div>
              ))}
            </section>
          );
        })
      )}

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
        .mem-btn {
          display: inline-flex; align-items: center; gap: 0.4rem;
          padding: 0.65rem 1.1rem; border-radius: 10px; border: 2px solid transparent;
          color: #fff; font-weight: 800; font-size: 0.82rem; cursor: pointer;
          text-decoration: none; font-family: inherit;
          transition: transform 220ms cubic-bezier(0.34, 1.56, 0.64, 1),
                      box-shadow 220ms ease, filter 220ms ease;
        }
        .mem-btn-primary { background: #1e3a8a; border-color: #1e3a8a; box-shadow: 0 4px 12px rgba(30,58,138,0.25); }
        .mem-btn-teal    { background: #0e7490; border-color: #0e7490; box-shadow: 0 4px 12px rgba(14,116,144,0.25); }
        .mem-btn:hover { transform: translateY(-3px) scale(1.02); filter: brightness(1.12) saturate(1.08); box-shadow: 0 12px 24px rgba(15,23,42,0.25); }
        .mem-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .tile-action {
          display: inline-flex; align-items: center; justify-content: center; gap: 0.35rem;
          padding: 0.45rem 0.6rem; border-radius: 8px;
          font-size: 0.75rem; font-weight: 800; text-decoration: none;
          transition: transform 180ms ease, filter 180ms ease, box-shadow 180ms ease;
          flex: 1;
        }
        .tile-action-primary { background: #1e3a8a; color: #fff; }
        .tile-action-teal    { background: #0e7490; color: #fff; }
        .tile-action:hover { transform: translateY(-2px); filter: brightness(1.12); box-shadow: 0 6px 14px rgba(15,23,42,0.2); }
      `}</style>
    </div>
  );
}

function MemberTile({ member: m, index }: { member: MemberWithStats; index: number }) {
  const st = m._stats;
  const colour = TYPE_COLOURS[m.member_type] || "#475569";
  const [hover, setHover] = useState(false);
  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: "rgba(255,255,255,0.96)",
        borderRadius: 16,
        border: `2px solid ${hover ? "#93c5fd" : "#e5e7eb"}`,
        borderLeft: `6px solid ${colour}`,
        padding: "1.15rem 1.25rem",
        boxShadow: hover ? "0 20px 40px rgba(15,23,42,0.20)" : "0 4px 14px rgba(15,23,42,0.06)",
        transform: hover ? "translateY(-6px) scale(1.02)" : "translateY(0) scale(1)",
        transition: "transform 240ms cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 240ms ease, border-color 240ms ease",
        animation: `memFade 340ms ease ${Math.min(index * 40, 400)}ms both`,
        willChange: "transform",
        display: "flex", flexDirection: "column",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.9rem", marginBottom: "0.85rem" }}>
        <div style={{
          width: 56, height: 56, borderRadius: "50%",
          background: colour, color: "#fff",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "1.15rem", fontWeight: 800,
          flexShrink: 0, boxShadow: "0 4px 12px rgba(15,23,42,0.2)",
          transform: hover ? "scale(1.06) rotate(-3deg)" : "scale(1) rotate(0)",
          transition: "transform 240ms cubic-bezier(0.34, 1.56, 0.64, 1)",
        }}>
          {initials(m.full_name || "?")}
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <Link to={`/library/members/${m.id}`}
                style={{ color: "#111827", fontWeight: 800, fontSize: "1rem",
                         textDecoration: "none", display: "block",
                         overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {m.full_name || "Unnamed"}
          </Link>
          <div style={{ fontSize: "0.75rem", color: "#64748b", fontFamily: "monospace", marginTop: "0.15rem" }}>
            {m.member_number}
            {m.class_name ? ` · ${m.class_name}` : ""}
          </div>
          <div style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem",
                        marginTop: "0.35rem", padding: "0.15rem 0.55rem", borderRadius: 999,
                        background: `${colour}18`, color: colour,
                        fontSize: "0.7rem", fontWeight: 800, letterSpacing: "0.04em",
                        textTransform: "uppercase" }}>
            {TYPE_LABEL[m.member_type] || m.member_type}
            {!m.is_active ? " · Inactive" : ""}
          </div>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem", fontSize: "0.8rem",
                    color: "#475569", marginBottom: "0.75rem" }}>
        {m.email ? <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <Mail size={12} style={{ color: "#64748b" }} />
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.email}</span>
        </div> : null}
        {m.phone ? <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <Phone size={12} style={{ color: "#64748b" }} />
          <span style={{ fontFamily: "monospace" }}>{m.phone}</span>
        </div> : null}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "0.4rem",
                    padding: "0.6rem 0.4rem", borderRadius: 10, background: "#f8fafc",
                    border: "1px solid #e2e8f0", marginBottom: "0.75rem" }}>
        <Stat label="Active" value={st?.active} colour="#1e3a8a" Icon={BookOpen} />
        <Stat label="Returned" value={st?.returned} colour="#0e7490" Icon={TrendingUp} />
        <Stat label="Overdue" value={st?.overdue} colour="#991b1b" Icon={AlertCircle} />
        <Stat label="Fines" value={st?.finesUnpaid} colour="#a16207" Icon={Wallet} money />
      </div>
      <div style={{ display: "flex", gap: "0.4rem" }}>
        <Link to={`/library/circulation?member=${m.id}`} className="tile-action tile-action-primary">
          <BookOpen size={12} /> Issue Book
        </Link>
        <Link to={`/library/circulation?member=${m.id}&tab=return`} className="tile-action tile-action-teal">
          <ArrowLeftRight size={12} /> Return Book
        </Link>
      </div>
      <style>{`@keyframes memFade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }`}</style>
    </div>
  );
}

function Stat({ label, value, colour, Icon, money }: {
  label: string; value?: number; colour: string; Icon: any; money?: boolean;
}) {
  return (
    <div style={{ textAlign: "center", minWidth: 0 }}>
      <div style={{ display: "inline-flex", alignItems: "center", gap: "0.2rem",
                    color: colour, fontSize: "0.6rem", fontWeight: 800,
                    textTransform: "uppercase", letterSpacing: "0.04em" }}>
        <Icon size={10} />
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{label}</span>
      </div>
      <div style={{ fontSize: "1rem", fontWeight: 800, color: "#111827", marginTop: "0.1rem", fontFamily: "monospace" }}>
        {value === undefined ? "—" : money ? `KSh ${value.toLocaleString()}` : value}
      </div>
    </div>
  );
}