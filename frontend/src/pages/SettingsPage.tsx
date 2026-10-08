import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell, Check, Info, LayoutGrid, LogOut, Monitor, Moon,
  Palette, RotateCcw, Save, Sliders, Sun, User, Volume2,
} from "lucide-react";
import { useTheme, type AccentKey, type Density, type ThemeMode } from "../theme/ThemeContext";
import { useAuth } from "../auth/AuthContext";
import "./SettingsPage.css";

type Tab = "appearance" | "notifications" | "timetable" | "account" | "about";

const ACCENT_SWATCHES: { key: AccentKey; label: string; color: string }[] = [
  { key: "blue",   label: "Navy",   color: "#244b72" },
  { key: "green",  label: "Forest", color: "#166534" },
  { key: "purple", label: "Plum",   color: "#5b21b6" },
  { key: "amber",  label: "Amber",  color: "#b45309" },
  { key: "rose",   label: "Rose",   color: "#9f1239" },
  { key: "teal",   label: "Teal",   color: "#0f766e" },
];

export default function SettingsPage() {
  const { prefs, setPref, resetPrefs, resolvedTheme } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("appearance");
  const [savedFlash, setSavedFlash] = useState(false);

  function flashSaved() {
    setSavedFlash(true);
    window.setTimeout(() => setSavedFlash(false), 1400);
  }

  async function handleSignOut() {
    await logout();
    navigate("/login", { replace: true });
  }

  const u = user as any;
  const displayName: string = u?.display_name || u?.username || "User";
  const email: string = u?.email || "—";
  const roleLabel: string = (u?.role || "GUEST").replace(/_/g, " ");

  return (
    <div className="settings-page">
      <header className="stg-head">
        <div>
          <h1>Settings</h1>
          <p className="stg-sub">
            Personalise SmartTimetable Pro to match how you work.
          </p>
        </div>
        <button
          type="button"
          className="stg-reset"
          onClick={() => { resetPrefs(); flashSaved(); }}
          title="Reset all preferences to defaults"
        >
          <RotateCcw size={14} /> Reset to defaults
        </button>
      </header>

      <div className="stg-layout">
        <nav className="stg-tabs" role="tablist">
          <button
            className={"stg-tab" + (tab === "appearance" ? " active" : "")}
            onClick={() => setTab("appearance")}
          >
            <Palette size={16} /> Appearance
          </button>
          <button
            className={"stg-tab" + (tab === "notifications" ? " active" : "")}
            onClick={() => setTab("notifications")}
          >
            <Bell size={16} /> Notifications
          </button>
          <button
            className={"stg-tab" + (tab === "timetable" ? " active" : "")}
            onClick={() => setTab("timetable")}
          >
            <LayoutGrid size={16} /> Timetable
          </button>
          <button
            className={"stg-tab" + (tab === "account" ? " active" : "")}
            onClick={() => setTab("account")}
          >
            <User size={16} /> Account
          </button>
          <button
            className={"stg-tab" + (tab === "about" ? " active" : "")}
            onClick={() => setTab("about")}
          >
            <Info size={16} /> About
          </button>
        </nav>

        <section className="stg-body">
          {tab === "appearance" && (
            <div className="stg-panel">
              <h2>Theme</h2>
              <p className="stg-help">
                Choose how SmartTimetable Pro looks. "System" follows your device setting.
              </p>
              <div className="stg-theme-grid">
                {(["light", "dark", "system"] as ThemeMode[]).map((mode) => {
                  const Icon = mode === "light" ? Sun : mode === "dark" ? Moon : Monitor;
                  const label = mode[0].toUpperCase() + mode.slice(1);
                  const active = prefs.theme === mode;
                  return (
                    <button
                      key={mode}
                      className={"stg-theme-card" + (active ? " active" : "")}
                      onClick={() => { setPref("theme", mode); flashSaved(); }}
                    >
                      <Icon size={22} />
                      <span>{label}</span>
                      {active && <Check size={16} className="stg-tick" />}
                    </button>
                  );
                })}
              </div>

              <h2>Accent colour</h2>
              <p className="stg-help">Used for highlights, active tabs, and primary buttons.</p>
              <div className="stg-swatches">
                {ACCENT_SWATCHES.map((s) => (
                  <button
                    key={s.key}
                    className={"stg-swatch" + (prefs.accent === s.key ? " active" : "")}
                    style={{ background: s.color }}
                    onClick={() => { setPref("accent", s.key); flashSaved(); }}
                    title={s.label}
                    aria-label={s.label}
                  >
                    {prefs.accent === s.key && <Check size={14} color="#fff" />}
                  </button>
                ))}
              </div>

              <h2>Density</h2>
              <p className="stg-help">Comfortable gives more spacing; Compact fits more on screen.</p>
              <div className="stg-radio-row">
                {(["comfortable", "compact"] as Density[]).map((d) => (
                  <label key={d} className="stg-radio">
                    <input
                      type="radio"
                      name="density"
                      checked={prefs.density === d}
                      onChange={() => { setPref("density", d); flashSaved(); }}
                    />
                    <span>{d[0].toUpperCase() + d.slice(1)}</span>
                  </label>
                ))}
              </div>

              <h2>Sidebar</h2>
              <label className="stg-toggle">
                <input
                  type="checkbox"
                  checked={prefs.sidebarCollapsed}
                  onChange={(e) => { setPref("sidebarCollapsed", e.target.checked); flashSaved(); }}
                />
                <span>Start with sidebar collapsed</span>
              </label>

              <div className="stg-footer">
                <span className="stg-preview">
                  Current: <b>{resolvedTheme}</b>
                </span>
                {savedFlash && <span className="stg-saved"><Check size={14} /> Saved</span>}
              </div>
            </div>
          )}

          {tab === "notifications" && (
            <div className="stg-panel">
              <h2>Notifications</h2>
              <label className="stg-toggle">
                <input
                  type="checkbox"
                  checked={prefs.notifySound}
                  onChange={(e) => { setPref("notifySound", e.target.checked); flashSaved(); }}
                />
                <span><Volume2 size={14} /> Play a soft sound on new notifications</span>
              </label>

              <h2>Badge</h2>
              <p className="stg-help">How the notification badge should appear.</p>
              <div className="stg-radio-row">
                {(["count", "dot"] as const).map((m) => (
                  <label key={m} className="stg-radio">
                    <input
                      type="radio"
                      name="notifyBadge"
                      checked={prefs.notifyBadgeMode === m}
                      onChange={() => { setPref("notifyBadgeMode", m); flashSaved(); }}
                    />
                    <span>{m === "count" ? "Show count" : "Dot only"}</span>
                  </label>
                ))}
              </div>

              <div className="stg-footer">
                {savedFlash && <span className="stg-saved"><Check size={14} /> Saved</span>}
              </div>
            </div>
          )}

          {tab === "timetable" && (
            <div className="stg-panel">
              <h2>Default view</h2>
              <p className="stg-help">What /timetables shows first when you open it.</p>
              <div className="stg-radio-row">
                {(["master", "class", "teacher"] as const).map((v) => (
                  <label key={v} className="stg-radio">
                    <input
                      type="radio"
                      name="ttView"
                      checked={prefs.defaultTimetableView === v}
                      onChange={() => { setPref("defaultTimetableView", v); flashSaved(); }}
                    />
                    <span>{v[0].toUpperCase() + v.slice(1)}</span>
                  </label>
                ))}
              </div>

              <h2>Print size</h2>
              <p className="stg-help">Paper size for printed / exported timetables.</p>
              <div className="stg-radio-row">
                {(["A3-landscape", "A4-portrait"] as const).map((p) => (
                  <label key={p} className="stg-radio">
                    <input
                      type="radio"
                      name="printSize"
                      checked={prefs.defaultPrintSize === p}
                      onChange={() => { setPref("defaultPrintSize", p); flashSaved(); }}
                    />
                    <span>{p}</span>
                  </label>
                ))}
              </div>

              <div className="stg-footer">
                {savedFlash && <span className="stg-saved"><Check size={14} /> Saved</span>}
              </div>
            </div>
          )}

          {tab === "account" && (
            <div className="stg-panel">
              <h2>Your account</h2>
              <div className="stg-field">
                <label>Name</label>
                <input value={displayName} disabled />
              </div>
              <div className="stg-field">
                <label>Username</label>
                <input value={u?.username || ""} disabled />
              </div>
              <div className="stg-field">
                <label>Email</label>
                <input value={email} disabled />
              </div>
              <div className="stg-field">
                <label>Role</label>
                <input value={roleLabel} disabled />
              </div>
              <div className="stg-actions">
                <button
                  type="button"
                  className="stg-btn stg-btn-secondary"
                  onClick={() => navigate("/admin/change-password")}
                >
                  <Sliders size={14} /> Change password
                </button>
                <button
                  type="button"
                  className="stg-btn stg-btn-danger"
                  onClick={handleSignOut}
                >
                  <LogOut size={14} /> Sign out
                </button>
              </div>
              <p className="stg-help" style={{ marginTop: "1rem" }}>
                To edit your profile details, ask your administrator.
              </p>
            </div>
          )}

          {tab === "about" && (
            <div className="stg-panel">
              <h2>SmartTimetable Pro</h2>
              <p className="stg-help">
                Intelligent school timetable management and scheduling system.
              </p>
              <div className="stg-about-grid">
                <div><b>Version</b><span>1.0.0</span></div>
                <div><b>Build</b><span>2026.09</span></div>
                <div><b>School</b><span>Queen of Apostles Seminary Senior School</span></div>
                <div><b>Support</b><span>admin@smarttimetable.local</span></div>
              </div>
              <p className="stg-help" style={{ marginTop: "1rem" }}>
                © 2026 SmartTimetable Pro. All rights reserved.
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
