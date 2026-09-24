import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import {
  AlertCircle, BookOpen, CalendarDays, CheckCircle2, DoorOpen,
  GraduationCap, PlayCircle, TrendingUp, Users,
} from "lucide-react";
import api from "../api";
import {
  fetchSchedulingDashboard,
  type SchedulingDashboard,
} from "../services/scheduling";
import { fetchDashboard as fetchAcademicDashboard } from "../services/analysis";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0";
const GREEN = "#10b981", RED = "#ef4444";

export default function Dashboard() {
  const [counts, setCounts] = useState({
    teachingGroups: 0, teachers: 0, subjects: 0, rooms: 0,
  });
  const [scheduling, setScheduling] = useState<SchedulingDashboard | null>(null);
  const [academic, setAcademic] = useState<{ overall_mean?: number; pass_rate?: number; trend?: Array<{assessment_name: string; mean: number}> } | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [tg, t, s, r] = await Promise.all([
          api.get("/academics/management/teaching-groups/"),
          api.get("/academics/management/teachers/"),
          api.get("/academics/management/subjects/"),
          api.get("/academics/management/rooms/"),
        ]);
        setCounts({
          teachingGroups: Array.isArray(tg.data) ? tg.data.length : 0,
          teachers: Array.isArray(t.data) ? t.data.length : 0,
          subjects: Array.isArray(s.data) ? s.data.length : 0,
          rooms: Array.isArray(r.data) ? r.data.length : 0,
        });
      } catch { /* ignore */ }
    })();
    fetchSchedulingDashboard().then(setScheduling).catch(() => setScheduling(null));
    fetchAcademicDashboard().then((d) => setAcademic({
      overall_mean: d.overall_mean,
      pass_rate: d.pass_rate,
      trend: d.trend,
    })).catch(() => setAcademic(null));
  }, []);

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Overview of timetable management and scheduling.</p>
        </div>
        <NavLink to="/scheduling" className="primary-button">
          <PlayCircle size={18} /> Generate Timetable
        </NavLink>
      </div>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon"><GraduationCap size={21} /></div>
          <div>
            <div className="stat-label">Teaching Groups</div>
            <div className="stat-value">{counts.teachingGroups}</div>
            <div className="stat-note">From academic data</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon"><Users size={21} /></div>
          <div>
            <div className="stat-label">Teachers</div>
            <div className="stat-value">{counts.teachers}</div>
            <div className="stat-note">Teacher assignments</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon"><BookOpen size={21} /></div>
          <div>
            <div className="stat-label">Subjects</div>
            <div className="stat-value">{counts.subjects}</div>
            <div className="stat-note">Active subjects</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon"><DoorOpen size={21} /></div>
          <div>
            <div className="stat-label">Rooms</div>
            <div className="stat-value">{counts.rooms}</div>
            <div className="stat-note">Available rooms</div>
          </div>
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Timetable Generation</h2>
              <p>Run the scheduling engine to generate a new timetable.</p>
            </div>
          </div>
          <div className="generation-panel">
            <div className="generation-icon"><PlayCircle size={32} /></div>
            <div className="generation-content">
              <h3>Ready to generate</h3>
              <p>
                The scheduling engine will enforce teacher clashes, room
                clashes, availability, lesson requirements and teacher
                free-afternoon constraints.
              </p>
              <NavLink to="/scheduling" className="secondary-button">Open Scheduling</NavLink>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>System Status</h2>
              <p>Core platform components.</p>
            </div>
          </div>
          <div className="status-list">
            <div className="status-row"><span>Backend API</span><span className="status-badge ready">Ready</span></div>
            <div className="status-row"><span>Scheduling Engine</span><span className="status-badge ready">Ready</span></div>
            <div className="status-row"><span>Validation Engine</span><span className="status-badge ready">Ready</span></div>
            <div className="status-row"><span>Database</span><span className="status-badge ready">Ready</span></div>
          </div>
        </div>
      </section>

      {/* Recent scheduling runs */}
      <section className="panel recent-panel" style={{ marginTop: "1rem" }}>
        <div className="panel-header">
          <div>
            <h2>Recent Scheduling Runs</h2>
            <p>Latest completed and approved timetable generations.</p>
          </div>
          <NavLink to="/scheduling" className="text-button">View all</NavLink>
        </div>

        {scheduling && scheduling.recent_runs.length > 0 ? (
          <div style={{ display: "grid", gap: "0.5rem", padding: "0.5rem 0" }}>
            {scheduling.recent_runs.slice(0, 5).map((r) => {
              const isApproved = !!r.approved_at;
              return (
                <div key={r.id} style={{
                  display: "grid", gridTemplateColumns: "1.6fr 1fr 1fr auto",
                  gap: "0.75rem", padding: "0.6rem 0.9rem",
                  background: isApproved ? "#f0fdf4" : "#fff",
                  border: `1px solid ${isApproved ? GREEN : "#e5e7eb"}`,
                  borderRadius: "10px", alignItems: "center",
                  fontSize: "0.85rem",
                }}>
                  <div>
                    <div style={{ fontWeight: 700, color: isApproved ? "#166534" : "#1e2e40" }}>
                      {r.version_name ?? `Run ${r.id.slice(0, 8)}`}
                    </div>
                    <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>{r.term_name}</div>
                  </div>
                  <div style={{ fontSize: "0.78rem", color: "#64748b" }}>
                    {new Date(r.completed_at ?? r.created_at ?? "").toLocaleString()}
                  </div>
                  <div style={{ fontSize: "0.78rem", color: isApproved ? "#166534" : "#94a3b8" }}>
                    {isApproved ? <><CheckCircle2 size={12} /> Approved</> : "Completed"}
                  </div>
                  <span style={{
                    padding: "2px 9px", borderRadius: "999px",
                    background: isApproved ? "#dcfce7" : "#f1f5f9",
                    color: isApproved ? "#166534" : "#64748b",
                    fontSize: "0.72rem", fontWeight: 700,
                  }}>
                    {isApproved ? "APPROVED" : "COMPLETED"}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="empty-state">
            <CalendarDays size={38} />
            <h3>No scheduling runs displayed yet</h3>
            <p>Once the scheduling engine has been run, recent runs will appear here.</p>
          </div>
        )}

        {scheduling && scheduling.failed_runs.length > 0 && (
          <div style={{
            marginTop: "0.75rem", paddingTop: "0.75rem",
            borderTop: "1px solid #fee2e2",
          }}>
            <div style={{ fontSize: "0.7rem", letterSpacing: "0.12em", textTransform: "uppercase", color: RED, fontWeight: 800, marginBottom: "0.5rem" }}>
              RECENT FAILURES
            </div>
            {scheduling.failed_runs.slice(0, 3).map((r) => (
              <div key={r.id} style={{
                display: "flex", alignItems: "flex-start", gap: "8px",
                padding: "0.5rem 0.75rem", background: "#fef2f2",
                border: `1px solid ${RED}`, borderRadius: "9px",
                fontSize: "0.8rem", marginBottom: "0.4rem",
              }}>
                <AlertCircle size={14} color={RED} style={{ marginTop: "2px", flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, color: "#991b1b" }}>{r.term_name}</div>
                  <div style={{ color: "#7f1d1d", fontSize: "0.75rem", lineHeight: 1.4 }}>
                    {r.error_message || "Unknown failure."}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Assessment history */}
      <section className="panel recent-panel" style={{ marginTop: "1rem" }}>
        <div className="panel-header">
          <div>
            <h2>Assessment History</h2>
            <p>Latest assessment performance across the school.</p>
          </div>
          <NavLink to="/academics/analysis" className="text-button">Open Analysis</NavLink>
        </div>

        {academic && academic.trend && academic.trend.length > 0 ? (
          <>
            <div style={{
              display: "grid", gridTemplateColumns: "1fr 1fr",
              gap: "1rem", marginBottom: "0.75rem",
            }}>
              <div style={{
                padding: "0.75rem 1rem", borderRadius: "10px",
                background: `linear-gradient(135deg, ${SKY}22, #ffffff)`,
                border: `1px solid ${SKY}`,
              }}>
                <div style={{ fontSize: "0.7rem", letterSpacing: "0.12em", textTransform: "uppercase", color: "#64748b", fontWeight: 800 }}>
                  LATEST MEAN
                </div>
                <div style={{ fontSize: "1.6rem", fontWeight: 800, color: BROWN2 }}>
                  {academic.overall_mean ?? "—"}%
                </div>
              </div>
              <div style={{
                padding: "0.75rem 1rem", borderRadius: "10px",
                background: "linear-gradient(135deg, #dcfce722, #ffffff)",
                border: `1px solid ${GREEN}`,
              }}>
                <div style={{ fontSize: "0.7rem", letterSpacing: "0.12em", textTransform: "uppercase", color: "#64748b", fontWeight: 800 }}>
                  PASS RATE
                </div>
                <div style={{ fontSize: "1.6rem", fontWeight: 800, color: GREEN }}>
                  {academic.pass_rate ?? "—"}%
                </div>
              </div>
            </div>

            <div style={{ display: "grid", gap: "0.4rem" }}>
              {academic.trend.map((t, i) => (
                <div key={i} style={{
                  display: "grid", gridTemplateColumns: "1.5fr 1fr",
                  gap: "0.75rem", padding: "0.55rem 0.85rem",
                  background: "#f8fafc", borderRadius: "9px",
                  fontSize: "0.83rem", alignItems: "center",
                }}>
                  <span style={{ fontWeight: 600, color: BROWN2 }}>{t.assessment_name}</span>
                  <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <TrendingUp size={14} color={SKY} />
                    <strong style={{ color: BROWN2 }}>{t.mean}%</strong>
                  </span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="empty-state">
            <BookOpen size={38} />
            <h3>No assessment data yet</h3>
            <p>Once assessments are entered, performance trends will appear here.</p>
          </div>
        )}
      </section>
    </>
  );
}