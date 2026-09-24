import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Activity, AlertTriangle, ArrowLeft, CheckCircle2, Info, KeyRound,
  Plus, RefreshCw, Save, Shield, Trash2, UserCog, Users, X,
} from "lucide-react";
import {
  createGroup, createUser, deleteGroup, deleteUser,
  fetchHealth, fetchWarnings, listGroups, listUsers,
  resetPassword, updateUser,
  type AdminGroup, type AdminHealth, type AdminUser, type AdminWarning,
} from "../services/admin";
import "../styles/analysis.css";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0", CREAM = "#f5eee2";
const cardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
  padding: "1.1rem 1.25rem", boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};

type TabKey = "users" | "roles" | "health" | "warnings" | "audit";

export default function AdminConsole() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<TabKey>("users");

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [groups, setGroups] = useState<AdminGroup[]>([]);
  const [health, setHealth] = useState<AdminHealth | null>(null);
  const [warnings, setWarnings] = useState<AdminWarning[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState<Partial<AdminUser>>({});
  const [creating, setCreating] = useState(false);
  const [newUser, setNewUser] = useState<{ username: string; email: string; first_name: string; last_name: string; password: string; groups: string[] }>({
    username: "", email: "", first_name: "", last_name: "", password: "", groups: ["Teacher"],
  });

  async function loadAll() {
    setLoading(true); setError(null); setForbidden(false);
    try {
      const [u, g, h, w] = await Promise.all([
        listUsers(search || undefined),
        listGroups(),
        fetchHealth(),
        fetchWarnings(),
      ]);
      setUsers(u.results);
      setGroups(g);
      setHealth(h);
      setWarnings(w.warnings);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      const status = (e as { response?: { status?: number } })?.response?.status;
      if (status === 403 || status === 401) setForbidden(true);
      else setError(msg);
    } finally { setLoading(false); }
  }

  useEffect(() => { loadAll(); /* eslint-disable-next-line */ }, []);
  useEffect(() => { if (!loading) { listUsers(search || undefined).then((u) => setUsers(u.results)); } /* eslint-disable-next-line */ }, [search]);

  async function saveEdit() {
    if (editing === null) return;
    try {
      const updated = await updateUser(editing, draft);
      setUsers((prev) => prev.map((u) => u.id === editing ? updated : u));
      setEditing(null); setDraft({});
    } catch (e) { setError(e instanceof Error ? e.message : "Save failed"); }
  }

  async function doResetPassword(id: number, username: string) {
    const pw = prompt(`New password for ${username} (leave blank for "ChangeMe123!")`, "");
    if (pw === null) return;
    try {
      await resetPassword(id, pw || "ChangeMe123!");
      alert(`Password updated for ${username}`);
    } catch (e) { setError(e instanceof Error ? e.message : "Reset failed"); }
  }

  async function toggleActive(u: AdminUser) {
    try {
      const updated = await updateUser(u.id, { is_active: !u.is_active });
      setUsers((prev) => prev.map((x) => x.id === u.id ? updated : x));
    } catch (e) { setError(e instanceof Error ? e.message : "Toggle failed"); }
  }

  async function removeUser(u: AdminUser) {
    if (!confirm(`Delete user ${u.username}? This cannot be undone.`)) return;
    try { await deleteUser(u.id); setUsers((prev) => prev.filter((x) => x.id !== u.id)); }
    catch (e) { setError(e instanceof Error ? e.message : "Delete failed"); }
  }

  async function doCreateUser() {
    try {
      const created = await createUser({
        username: newUser.username.trim(),
        email: newUser.email.trim(),
        first_name: newUser.first_name.trim(),
        last_name: newUser.last_name.trim(),
        password: newUser.password || undefined,
        groups: newUser.groups,
      });
      setUsers((prev) => [...prev, created]);
      setCreating(false);
      setNewUser({ username: "", email: "", first_name: "", last_name: "", password: "", groups: ["Teacher"] });
    } catch (e) { setError(e instanceof Error ? e.message : "Create failed"); }
  }

  async function doCreateGroup() {
    const name = prompt("New role name (e.g. Librarian)");
    if (!name) return;
    try { const g = await createGroup(name); setGroups((prev) => [...prev, g]); }
    catch (e) { setError(e instanceof Error ? e.message : "Create failed"); }
  }

  async function doDeleteGroup(g: AdminGroup) {
    if (!confirm(`Delete role ${g.name}? Users will lose its permissions.`)) return;
    try { await deleteGroup(g.id); setGroups((prev) => prev.filter((x) => x.id !== g.id)); }
    catch (e) { setError(e instanceof Error ? e.message : "Delete failed"); }
  }

  const warningCounts = useMemo(() => {
    const m: Record<AdminWarning["severity"], number> = { info: 0, warning: 0, danger: 0 };
    for (const w of warnings) m[w.severity]++;
    return m;
  }, [warnings]);

  if (forbidden) {
    return (
      <div style={{ padding: "4rem 2rem", textAlign: "center", maxWidth: "560px", margin: "0 auto" }}>
        <Shield size={48} color="#94a3b8" />
        <h1 style={{ color: "#1e2e40", marginTop: "1rem" }}>Administrator access required</h1>
        <p style={{ color: "#748095" }}>Your account does not have staff or superuser privileges.</p>
        <button onClick={() => navigate("/home")} style={{ marginTop: "1rem", background: SKY, color: "#fff", border: "none", padding: "0.6rem 1.2rem", borderRadius: "10px", fontWeight: 700, cursor: "pointer" }}>
          Go home
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "1500px", margin: "0 auto" }}>
      <button type="button" onClick={() => navigate(-1)} style={{
        display: "inline-flex", alignItems: "center", gap: "6px",
        background: "transparent", border: "none", color: BROWN2,
        fontWeight: 600, cursor: "pointer", marginBottom: "1rem",
      }}><ArrowLeft size={16} /> Back</button>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{
            width: "52px", height: "52px", borderRadius: "14px",
            background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`,
            color: CREAM, display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 6px 18px rgba(43,26,15,0.35)",
          }}><UserCog size={26} /></div>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.7rem", color: "#1e2e40", fontWeight: 800 }}>Admin Console</h1>
            <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.9rem" }}>
              Users · Roles · System Health · Warnings
            </p>
          </div>
        </div>
        <button type="button" onClick={loadAll} disabled={loading}
          style={{
            display: "inline-flex", alignItems: "center", gap: "6px",
            background: SKY, color: "#fff", border: "none",
            padding: "0.55rem 1rem", borderRadius: "10px",
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: 700, fontSize: "0.85rem",
          }}>
          <RefreshCw size={15} /> Refresh
        </button>
      </div>

      {error && <div style={{ padding: "0.7rem 1rem", borderRadius: "10px", background: "#fee2e2", color: "#991b1b", marginBottom: "1rem" }}>{error}</div>}

      <div className="anim-rise" style={{ display: "flex", gap: "6px", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        {([
          ["users", "Users", Users, users.length],
          ["roles", "Roles", Shield, groups.length],
          ["health", "System Health", Activity, 0],
          ["warnings", "Warnings", AlertTriangle, warnings.length],
          ["audit", "Recent Activity", Info, 0],
        ] as Array<[TabKey, string, React.ComponentType<{ size?: number }>, number]>).map(([k, label, Icon, count]) => {
          const on = tab === k;
          return (
            <button key={k} type="button" onClick={() => setTab(k)}
              style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                background: on ? BROWN2 : "#fff",
                color: on ? CREAM : "#64748b",
                border: on ? `1px solid ${BROWN2}` : "1px solid #e5e7eb",
                padding: "0.6rem 1.1rem", borderRadius: "10px",
                cursor: "pointer", fontWeight: 700, fontSize: "0.85rem",
              }}>
              <Icon size={15} /> {label}
              {count > 0 && (
                <span style={{
                  marginLeft: "4px", padding: "1px 7px", borderRadius: "999px",
                  background: on ? "rgba(255,255,255,0.2)" : "#f1f5f9",
                  color: on ? CREAM : "#64748b",
                  fontSize: "0.72rem", fontWeight: 800,
                }}>{count}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* ================= USERS ================= */}
      {tab === "users" && (
        <>
          <div style={{ ...cardStyle, display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap", marginBottom: "1rem" }}>
            <input placeholder="Search username / name…" value={search} onChange={(e) => setSearch(e.target.value)}
              style={{ flex: "1 1 260px", padding: "0.55rem 0.9rem", border: "1px solid #cbd5e1", borderRadius: "10px", fontSize: "0.9rem" }} />
            <button type="button" onClick={() => setCreating(true)}
              style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                background: SKY, color: "#fff", border: "none",
                padding: "0.55rem 1rem", borderRadius: "10px",
                cursor: "pointer", fontWeight: 700, fontSize: "0.85rem",
              }}>
              <Plus size={15} /> New user
            </button>
          </div>

          {creating && (
            <div style={{ ...cardStyle, border: `1px solid ${SKY}`, marginBottom: "1rem" }}>
              <h3 style={{ margin: "0 0 0.75rem", color: BROWN2, fontSize: "0.95rem", fontWeight: 700 }}>New user</h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr 1fr auto auto", gap: "8px", alignItems: "end" }}>
                <input placeholder="username*" value={newUser.username} onChange={(e) => setNewUser({ ...newUser, username: e.target.value })} style={{ padding: "6px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
                <input placeholder="first name" value={newUser.first_name} onChange={(e) => setNewUser({ ...newUser, first_name: e.target.value })} style={{ padding: "6px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
                <input placeholder="last name" value={newUser.last_name} onChange={(e) => setNewUser({ ...newUser, last_name: e.target.value })} style={{ padding: "6px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
                <input placeholder="email" value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} style={{ padding: "6px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
                <input placeholder="password (default ChangeMe123!)" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} style={{ padding: "6px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
                <input placeholder="groups (comma-sep)" value={newUser.groups.join(",")} onChange={(e) => setNewUser({ ...newUser, groups: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} style={{ padding: "6px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
                <button type="button" onClick={doCreateUser} style={{ background: SKY, color: "#fff", border: "none", padding: "6px 14px", borderRadius: "6px", fontWeight: 700, cursor: "pointer" }}>Create</button>
                <button type="button" onClick={() => setCreating(false)} style={{ background: "#e5e7eb", color: "#374151", border: "none", padding: "6px 14px", borderRadius: "6px", fontWeight: 700, cursor: "pointer" }}>Cancel</button>
              </div>
            </div>
          )}

          <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.86rem" }}>
                <thead>
                  <tr style={{ background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM }}>
                    <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Username</th>
                    <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Name</th>
                    <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Email</th>
                    <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Groups</th>
                    <th style={{ textAlign: "center", padding: "0.7rem 1rem" }}>Flags</th>
                    <th style={{ textAlign: "center", padding: "0.7rem 1rem" }}>Active</th>
                    <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => {
                    const isEdit = editing === u.id;
                    return (
                      <tr key={u.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "0.55rem 1rem", fontWeight: 600, color: BROWN2 }}>{u.username}</td>
                        {isEdit ? (
                          <>
                            <td style={{ padding: "0.55rem 1rem" }}>
                              <input value={draft.first_name ?? u.first_name} onChange={(e) => setDraft({ ...draft, first_name: e.target.value })} placeholder="first" style={{ width: "100%", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "4px", marginBottom: "2px" }} />
                              <input value={draft.last_name ?? u.last_name} onChange={(e) => setDraft({ ...draft, last_name: e.target.value })} placeholder="last" style={{ width: "100%", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "4px" }} />
                            </td>
                            <td style={{ padding: "0.55rem 1rem" }}>
                              <input value={draft.email ?? u.email} onChange={(e) => setDraft({ ...draft, email: e.target.value })} style={{ width: "100%", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "4px" }} />
                            </td>
                            <td style={{ padding: "0.55rem 1rem" }}>
                              <input value={(draft.groups ?? u.groups).join(",")} onChange={(e) => setDraft({ ...draft, groups: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} style={{ width: "100%", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "4px" }} />
                            </td>
                            <td style={{ padding: "0.55rem 1rem", textAlign: "center" }}>
                              <label style={{ marginRight: "6px", fontSize: "0.78rem" }}>staff <input type="checkbox" checked={draft.is_staff ?? u.is_staff} onChange={(e) => setDraft({ ...draft, is_staff: e.target.checked })} /></label>
                              <label style={{ fontSize: "0.78rem" }}>super <input type="checkbox" checked={draft.is_superuser ?? u.is_superuser} onChange={(e) => setDraft({ ...draft, is_superuser: e.target.checked })} /></label>
                            </td>
                            <td style={{ padding: "0.55rem 1rem", textAlign: "center" }}>
                              <input type="checkbox" checked={draft.is_active ?? u.is_active} onChange={(e) => setDraft({ ...draft, is_active: e.target.checked })} />
                            </td>
                            <td style={{ padding: "0.55rem 1rem", textAlign: "right", whiteSpace: "nowrap" }}>
                              <button type="button" onClick={saveEdit} style={{ background: SKY, color: "#fff", border: "none", padding: "4px 10px", borderRadius: "4px", fontWeight: 700, cursor: "pointer", fontSize: "0.78rem", marginRight: "4px" }}><Save size={12} /> Save</button>
                              <button type="button" onClick={() => { setEditing(null); setDraft({}); }} style={{ background: "#e5e7eb", color: "#374151", border: "none", padding: "4px 10px", borderRadius: "4px", fontWeight: 700, cursor: "pointer", fontSize: "0.78rem" }}><X size={12} /></button>
                            </td>
                          </>
                        ) : (
                          <>
                            <td style={{ padding: "0.55rem 1rem" }}>{[u.first_name, u.last_name].filter(Boolean).join(" ") || <span style={{ color: "#cbd5e1" }}>—</span>}</td>
                            <td style={{ padding: "0.55rem 1rem", color: "#748095" }}>{u.email || <span style={{ color: "#cbd5e1" }}>—</span>}</td>
                            <td style={{ padding: "0.55rem 1rem" }}>
                              {u.groups.length === 0 ? <span style={{ color: "#cbd5e1" }}>—</span> :
                                u.groups.map((g) => (
                                  <span key={g} style={{ display: "inline-block", marginRight: "4px", padding: "1px 8px", background: "#f1f5f9", borderRadius: "999px", fontSize: "0.72rem", fontWeight: 700, color: "#475569" }}>{g}</span>
                                ))}
                            </td>
                            <td style={{ padding: "0.55rem 1rem", textAlign: "center" }}>
                              {u.is_superuser && <span title="superuser" style={{ marginRight: "4px" }}>👑</span>}
                              {u.is_staff && !u.is_superuser && <span title="staff">🛡️</span>}
                            </td>
                            <td style={{ padding: "0.55rem 1rem", textAlign: "center" }}>
                              <input type="checkbox" checked={u.is_active} onChange={() => toggleActive(u)} />
                            </td>
                            <td style={{ padding: "0.55rem 1rem", textAlign: "right", whiteSpace: "nowrap" }}>
                              <button type="button" onClick={() => { setEditing(u.id); setDraft({}); }} style={{ background: "transparent", border: "1px solid #94a3b8", color: "#475569", padding: "4px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", fontSize: "0.78rem", marginRight: "4px" }}>Edit</button>
                              <button type="button" onClick={() => doResetPassword(u.id, u.username)} title="Reset password" style={{ background: "transparent", border: "1px solid #f59e0b", color: "#b45309", padding: "4px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", fontSize: "0.78rem", marginRight: "4px" }}><KeyRound size={12} /></button>
                              {u.username !== "admin" && (
                                <button type="button" onClick={() => removeUser(u)} style={{ background: "transparent", border: "1px solid #ef4444", color: "#ef4444", padding: "4px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", fontSize: "0.78rem" }}><Trash2 size={12} /></button>
                              )}
                            </td>
                          </>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ================= ROLES ================= */}
      {tab === "roles" && (
        <>
          <div style={{ ...cardStyle, display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <div>
              <h3 style={{ margin: 0, color: BROWN2, fontSize: "0.98rem", fontWeight: 800 }}>Roles (Django Groups)</h3>
              <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.82rem" }}>System roles cannot be deleted. Users assigned to a role inherit its permissions.</p>
            </div>
            <button type="button" onClick={doCreateGroup}
              style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: SKY, color: "#fff", border: "none", padding: "0.55rem 1rem", borderRadius: "10px", fontWeight: 700, cursor: "pointer", fontSize: "0.85rem" }}>
              <Plus size={15} /> New role
            </button>
          </div>
          <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
              <thead>
                <tr style={{ background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM }}>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Role</th>
                  <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Users</th>
                  <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Permissions</th>
                  <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {groups.map((g) => {
                  const system = ["Teacher","Administrator","Viewer"].includes(g.name);
                  return (
                    <tr key={g.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "0.7rem 1rem", fontWeight: 700, color: "#1e2e40" }}>
                        {g.name} {system && <span style={{ color: "#94a3b8", fontWeight: 500, fontSize: "0.78rem" }}>· system</span>}
                      </td>
                      <td style={{ padding: "0.7rem 1rem", textAlign: "right" }}>{g.user_count}</td>
                      <td style={{ padding: "0.7rem 1rem", textAlign: "right" }}>{g.permission_count}</td>
                      <td style={{ padding: "0.7rem 1rem", textAlign: "right" }}>
                        {!system && <button type="button" onClick={() => doDeleteGroup(g)} style={{ background: "transparent", border: "1px solid #ef4444", color: "#ef4444", padding: "4px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", fontSize: "0.78rem" }}><Trash2 size={12} /></button>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ================= HEALTH ================= */}
      {tab === "health" && (
        <>
          {health && (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
                <div className="anim-rise" style={cardStyle}>
                  <div style={{ fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700 }}>Database</div>
                  <div style={{ fontSize: "1.3rem", fontWeight: 800, color: health.db_ok ? "#10b981" : "#ef4444" }}>{health.db_ok ? "Healthy" : "Down"}</div>
                </div>
                <div className="anim-rise" style={{ ...cardStyle, animationDelay: "60ms" }}>
                  <div style={{ fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700 }}>Disk used</div>
                  <div style={{ fontSize: "1.3rem", fontWeight: 800, color: health.disk.used_pct > 85 ? "#ef4444" : "#1e2e40" }}>{health.disk.used_pct}%</div>
                  <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>{health.disk.used_gb} / {health.disk.total_gb} GB</div>
                </div>
                <div className="anim-rise" style={{ ...cardStyle, animationDelay: "120ms" }}>
                  <div style={{ fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700 }}>Users</div>
                  <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#1e2e40" }}>{health.counts.users}</div>
                </div>
                <div className="anim-rise" style={{ ...cardStyle, animationDelay: "180ms" }}>
                  <div style={{ fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700 }}>Results</div>
                  <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#1e2e40" }}>{health.counts.results}</div>
                </div>
              </div>

              <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
                <div style={{ padding: "0.8rem 1.25rem", borderBottom: "1px solid #eef2f7" }}>
                  <h3 style={{ margin: 0, color: BROWN2, fontSize: "0.95rem", fontWeight: 700 }}>Data counts</h3>
                </div>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
                  <tbody>
                    {Object.entries(health.counts).map(([k, v], i) => (
                      <tr key={k} style={{ borderTop: i ? "1px solid #f1f5f9" : "none" }}>
                        <td style={{ padding: "0.6rem 1.25rem", color: "#475569", textTransform: "capitalize" }}>{k.replace(/_/g, " ")}</td>
                        <td style={{ padding: "0.6rem 1.25rem", textAlign: "right", fontWeight: 700 }}>{v}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}

      {/* ================= WARNINGS ================= */}
      {tab === "warnings" && (
        <>
          <div style={{ display: "flex", gap: "10px", marginBottom: "1rem" }}>
            <span style={{ padding: "4px 12px", borderRadius: "999px", background: "#e0f2fe", color: "#075985", fontWeight: 700, fontSize: "0.82rem" }}>Info · {warningCounts.info}</span>
            <span style={{ padding: "4px 12px", borderRadius: "999px", background: "#fef3c7", color: "#92400e", fontWeight: 700, fontSize: "0.82rem" }}>Warning · {warningCounts.warning}</span>
            <span style={{ padding: "4px 12px", borderRadius: "999px", background: "#fee2e2", color: "#991b1b", fontWeight: 700, fontSize: "0.82rem" }}>Critical · {warningCounts.danger}</span>
          </div>
          <div style={{ display: "grid", gap: "8px" }}>
            {warnings.length === 0 ? (
              <div style={{ ...cardStyle, textAlign: "center", color: "#10b981", padding: "2rem" }}>
                <CheckCircle2 size={36} style={{ marginBottom: "0.5rem" }} />
                <p style={{ margin: 0, fontWeight: 700 }}>All clear — no warnings.</p>
              </div>
            ) : warnings.map((w, i) => {
              const colors: Record<string, { bg: string; fg: string; icon: React.ComponentType<{ size?: number }> }> = {
                info:    { bg: "#e0f2fe", fg: "#075985", icon: Info },
                warning: { bg: "#fef3c7", fg: "#92400e", icon: AlertTriangle },
                danger:  { bg: "#fee2e2", fg: "#991b1b", icon: AlertTriangle },
              };
              const c = colors[w.severity];
              const Icon = c.icon;
              return (
                <div key={i} className="anim-rise" style={{
                  ...cardStyle, background: c.bg,
                  animationDelay: `${i * 40}ms`,
                  display: "flex", gap: "12px", alignItems: "flex-start",
                }}>
                  <Icon size={20} />
                  <div>
                    <div style={{ fontWeight: 700, color: c.fg, fontSize: "0.92rem" }}>{w.title}</div>
                    <div style={{ color: c.fg, fontSize: "0.82rem", opacity: 0.85 }}>{w.detail}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* ================= AUDIT ================= */}
      {tab === "audit" && (
        <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid #eef2f7" }}>
            <h3 style={{ margin: 0, color: BROWN2, fontSize: "0.95rem", fontWeight: 700 }}>Recent activity (last 10 events)</h3>
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.86rem" }}>
            <thead>
              <tr style={{ background: "#f8fafc", color: "#748095" }}>
                <th style={{ textAlign: "left", padding: "0.6rem 1rem" }}>When</th>
                <th style={{ textAlign: "left", padding: "0.6rem 1rem" }}>Action</th>
                <th style={{ textAlign: "left", padding: "0.6rem 1rem" }}>Entity</th>
                <th style={{ textAlign: "left", padding: "0.6rem 1rem" }}>Label</th>
              </tr>
            </thead>
            <tbody>
              {(health?.recent_audit ?? []).map((ev, i) => (
                <tr key={i} style={{ borderTop: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "0.55rem 1rem", color: "#748095", fontSize: "0.8rem" }}>{new Date(ev.created_at).toLocaleString()}</td>
                  <td style={{ padding: "0.55rem 1rem", fontWeight: 700, color: BROWN2 }}>{ev.action}</td>
                  <td style={{ padding: "0.55rem 1rem" }}>{ev.entity_type}</td>
                  <td style={{ padding: "0.55rem 1rem" }}>{ev.entity_label}</td>
                </tr>
              ))}
              {(health?.recent_audit ?? []).length === 0 && (
                <tr><td colSpan={4} style={{ padding: "2rem", textAlign: "center", color: "#94a3b8" }}>No activity yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}