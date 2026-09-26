import { useState } from "react";
import { Download, FileText, AlertTriangle, BookOpen, Users } from "lucide-react";
import * as lib from "../../services/library";
import LibraryTabs from "../../components/library/LibraryTabs";

const REPORTS = [
  { name: "circulation", title: "Circulation", icon: BookOpen, text: "All loans issued with status and dates." },
  { name: "overdue", title: "Overdue", icon: AlertTriangle, text: "Active loans past their due date." },
  { name: "inventory", title: "Inventory", icon: FileText, text: "Every copy with shelf and status." },
  { name: "popular", title: "Popular titles", icon: Users, text: "Top 100 books by loan count." },
];

export default function ReportsPage() {
  const [busy, setBusy] = useState<string>("");

  async function download(reportName: string, format: "csv" | "json") {
    setBusy(`${reportName}:${format}`);
    try {
      const data = await lib.downloadReport(reportName, format);
      const blob = format === "csv"
        ? new Blob([data as any], { type: "text/csv" })
        : new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `library-${reportName}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("Export failed", e);
    } finally {
      setBusy("");
    }
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ marginBottom: "1rem" }}>
        <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>
          LIBRARY MANAGEMENT
        </span>
        <h1 style={{ marginTop: "0.35rem" }}>Reports</h1>
        <p style={{ color: "#748095" }}>Download circulation, inventory and usage data.</p>
      </div>

      <LibraryTabs />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem" }}>
        {REPORTS.map((r) => {
          const Icon = r.icon;
          return (
            <div key={r.name} style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "1.25rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Icon size={20} style={{ color: "#1e3a8a" }} />
                <div style={{ fontWeight: 700, color: "#111827" }}>{r.title}</div>
              </div>
              <p style={{ color: "#748095", fontSize: "0.83rem", marginTop: "0.4rem", minHeight: "2.2rem" }}>{r.text}</p>
              <div style={{ display: "flex", gap: "0.4rem", marginTop: "0.6rem" }}>
                <button type="button" onClick={() => download(r.name, "csv")}
                        disabled={busy === `${r.name}:csv`}
                        style={btnStyle}>
                  <Download size={13} /> {busy === `${r.name}:csv` ? "…" : "CSV"}
                </button>
                <button type="button" onClick={() => download(r.name, "json")}
                        disabled={busy === `${r.name}:json`}
                        style={btnStyle}>
                  <Download size={13} /> {busy === `${r.name}:json` ? "…" : "JSON"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: "0.3rem",
  padding: "0.4rem 0.75rem", fontSize: "0.8rem", fontWeight: 700,
  background: "#f1f5f9", color: "#1e3a8a", border: "1px solid #cbd5e1",
  borderRadius: "6px", cursor: "pointer",
};
