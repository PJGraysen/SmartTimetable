import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  PlayCircle,
  RefreshCw,
} from "lucide-react";

import {
  createSchedulingRun,
  executeSchedulingRun,
  getSchedulingRuns,
  type SchedulingRun,
} from "./services/scheduling";

import {
  getAcademicTerms,
  type AcademicTerm,
} from "./services/core";

/*
 * IMPORTANT:
 * Timetable.tsx is the single authoritative timetable renderer.
 *
 * Scheduling.tsx deliberately does NOT contain another timetable
 * implementation. This guarantees that the timetable shown here
 * is exactly the same timetable shown on the Timetable page.
 */
import Timetable from "./pages/Timetable";

function Scheduling() {
  const [terms, setTerms] = useState<AcademicTerm[]>([]);
  const [selectedTerm, setSelectedTerm] = useState("");
  const [runs, setRuns] = useState<SchedulingRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  /*
   * Changing this value forces the authoritative Timetable component
   * to remount and retrieve the newest completed timetable from the
   * database.
   */
  const [timetableRefreshKey, setTimetableRefreshKey] = useState(0);

  async function loadData(refreshTimetable = false) {
    setLoading(true);
    setError("");

    try {
      const [termsData, runsData] = await Promise.all([
        getAcademicTerms(),
        getSchedulingRuns(),
      ]);

      setTerms(termsData);
      setRuns(runsData);
      setLastSyncTime(new Date());

      const activeTerm = termsData.find((term) => term.is_active);

      if (activeTerm && !selectedTerm) {
        setSelectedTerm(activeTerm.id);
      }

      if (refreshTimetable) {
        setTimetableRefreshKey((current) => current + 1);
      }
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.response?.data?.error ||
          err?.detail ||
          err?.error ||
          "Unable to load academic terms and scheduling runs. Make sure the Django API is running.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function generateTimetable() {
    if (!selectedTerm) {
      setError("Select an academic term before generating a timetable.");
      return;
    }

    setGenerating(true);
    setError("");

    try {
      /*
       * Preserve the established database generation workflow:
       *
       * 1. Create scheduling run.
       * 2. Execute scheduling run.
       * 3. Backend persists the timetable version and entries.
       * 4. Reload scheduling runs.
       * 5. Remount the authoritative Timetable component.
       */
      const run = await createSchedulingRun({
        term: selectedTerm,
      });

      const result = await executeSchedulingRun(run.id, {
        version_name: "Generated Timetable",
      });

      /*
       * The backend persists FAILED runs and returns the authoritative
       * error_message in the SchedulingRun response. Do not discard that
       * response and do not refresh the timetable when generation failed.
       */
      if (result.status?.toUpperCase() === "FAILED") {
        const diagnostic =
          result.error_message?.trim() ||
          result.solver_status_display?.trim() ||
          result.solver_status?.trim() ||
          "Timetable generation failed.";

        /*
         * Refresh run history first. loadData() clears the transient
         * page error while reloading, so the authoritative diagnostic
         * must be restored after the refresh completes.
         */
        await loadData(false);

        /*
         * Display the backend-persisted diagnostic to the user.
         */
        setError(diagnostic);
        return;
      }

      /*
       * Only a successful scheduling run is allowed to refresh the
       * authoritative timetable renderer.
       */
      await loadData(true);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.response?.data?.error ||
          err?.detail ||
          err?.error ||
          "Timetable generation failed.",
      );
    } finally {
      setGenerating(false);
    }
  }

  useEffect(() => {
    void loadData(true);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      void loadData(false);
    }, 30000);

    return () => clearInterval(interval);
  }, [selectedTerm]);

  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">SCHEDULING ENGINE</span>

          <h1>Scheduling</h1>

          <p>
            Generate and monitor automated timetable scheduling runs.
          </p>
        </div>

        <div className="page-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => void loadData(true)}
            disabled={loading || generating}
          >
            <RefreshCw
              size={17}
              className={loading ? "spin" : undefined}
            />

            Refresh
          </button>

          <button
            type="button"
            className="primary-button"
            onClick={() => void generateTimetable()}
            disabled={generating || loading || !selectedTerm}
          >
            {generating ? (
              <RefreshCw size={17} className="spin" />
            ) : (
              <PlayCircle size={17} />
            )}

            {generating ? "Generating..." : "Generate Timetable"}
          </button>
        </div>
      </div>

      {error ? (
        <div
          className="section-card"
          style={{
            marginBottom: "1.25rem",
            borderColor: "#fecaca",
            background: "#fff7f7",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.65rem",
              color: "#b91c1c",
              padding: "1rem",
            }}
          >
            <AlertCircle size={19} />

            <span>{error}</span>
          </div>
        </div>
      ) : null}

      {runs.some((run) => run.status.toUpperCase() === "COMPLETED") && (
        <div
          className="section-card"
          style={{
            marginBottom: "1.5rem",
            background: "linear-gradient(135deg, #f5f7fb 0%, #eef2ff 100%)",
            borderColor: "#d1d5db",
          }}
        >
          <div className="section-card-header">
            <div>
              <span className="eyebrow">LATEST RESULT</span>
              <h2>Generated Timetable Status</h2>
            </div>
          </div>

          <div
            style={{
              padding: "1.25rem",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "1.5rem",
            }}
          >
            {(() => {
              const latestCompleted = runs.find(
                (run) => run.status.toUpperCase() === "COMPLETED"
              );

              return (
                <>
                  <div>
                    <div style={{ color: "#748095", fontSize: "11px", fontWeight: 700 }}>
                      TIMETABLE VERSION
                    </div>
                    <div
                      style={{
                        fontSize: "15px",
                        fontWeight: 700,
                        color: "#172033",
                        marginTop: "6px",
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                      }}
                    >
                      <CheckCircle2 size={18} style={{ color: "#22c55e" }} />
                      Generated
                    </div>
                  </div>

                  <div>
                    <div style={{ color: "#748095", fontSize: "11px", fontWeight: 700 }}>
                      CREATED AT
                    </div>
                    <div
                      style={{
                        fontSize: "15px",
                        fontWeight: 700,
                        color: "#172033",
                        marginTop: "6px",
                      }}
                    >
                      {latestCompleted?.created_at
                        ? new Date(latestCompleted.created_at).toLocaleTimeString()
                        : "--"}
                    </div>
                  </div>

                  <div>
                    <div style={{ color: "#748095", fontSize: "11px", fontWeight: 700 }}>
                      LAST SYNC
                    </div>
                    <div
                      style={{
                        fontSize: "15px",
                        fontWeight: 700,
                        color: "#172033",
                        marginTop: "6px",
                      }}
                    >
                      {lastSyncTime ? lastSyncTime.toLocaleTimeString() : "--"}
                    </div>
                  </div>

                  <div>
                    <div style={{ color: "#748095", fontSize: "11px", fontWeight: 700 }}>
                      CURRENT TIME
                    </div>
                    <div
                      style={{
                        fontSize: "15px",
                        fontWeight: 700,
                        color: "#172033",
                        marginTop: "6px",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <Clock size={16} />
                      {currentTime.toLocaleTimeString()}
                    </div>
                  </div>
                </>
              );
            })()}
          </div>
        </div>
      )}

      <div className="section-card">
        <div className="section-card-header">
          <div>
            <span className="eyebrow">NEW RUN</span>

            <h2>Select Academic Term</h2>
          </div>
        </div>

        <div style={{ padding: "1rem 0" }}>
          <select
            value={selectedTerm}
            onChange={(event) =>
              setSelectedTerm(event.target.value)
            }
            disabled={loading || generating}
            style={{
              width: "100%",
              maxWidth: "520px",
              padding: "0.75rem",
              borderRadius: "8px",
              border: "1px solid #d1d5db",
              fontSize: "0.95rem",
            }}
          >
            <option value="">
              {loading
                ? "Loading academic terms..."
                : "Select an academic term"}
            </option>

            {terms.map((term) => (
              <option key={term.id} value={term.id}>
                {term.name} — {term.academic_year_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <section
        className="section-card"
        style={{
          marginTop: "1.5rem",
        }}
      >
        <div className="section-card-header">
          <div>
            <span className="eyebrow">SCHEDULING RESULTS</span>

            <h2>Generated Timetable</h2>

            <p>
              The timetable below is the same authoritative database-backed
              timetable displayed on the Timetable page.
            </p>
          </div>
        </div>

        <div
          style={{
            padding: "1rem",
          }}
        >
          <Timetable key={timetableRefreshKey} />
        </div>
      </section>

      <section
        className="section-card"
        style={{
          marginTop: "1.5rem",
        }}
      >
        <div className="section-card-header">
          <div>
            <span className="eyebrow">RUN HISTORY</span>

            <h2>Scheduling Runs</h2>
          </div>
        </div>

        {loading ? (
          <div className="table-state">
            <RefreshCw size={20} className="spin" />
            Loading scheduling data...
          </div>
        ) : runs.length === 0 ? (
          <div className="empty-state">
            <Clock size={38} />

            <h3>No scheduling runs</h3>

            <p>
              No timetable generation runs have been recorded yet.
              Select an academic term and generate the first timetable.
            </p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Term</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Completed</th>
                  <th>Timetable Version</th>
                  <th>Diagnostic</th>
                </tr>
              </thead>

              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td>
                      <strong>
                        {run.term_name || run.term || "--"}
                      </strong>
                    </td>

                    <td>
                      <span
                        className={`status-badge ${run.status.toLowerCase()}`}
                      >
                        {run.status.toUpperCase() === "COMPLETED" ? (
                          <CheckCircle2 size={15} />
                        ) : run.status.toUpperCase() === "FAILED" ? (
                          <AlertCircle size={15} />
                        ) : (
                          <Clock size={15} />
                        )}

                        {run.status_display}
                      </span>
                    </td>

                    <td>
                      {run.created_at
                        ? new Date(run.created_at).toLocaleString()
                        : "--"}
                    </td>

                    <td>
                      {run.completed_at
                        ? new Date(run.completed_at).toLocaleString()
                        : "--"}
                    </td>

                    <td>
                      {run.timetable_version ? (
                        <span className="timetable-created">
                          <CheckCircle2 size={15} />
                          Available
                        </span>
                      ) : (
                        "--"
                      )}
                    </td>

                    <td>
                      {run.status.toUpperCase() === "FAILED" ? (
                        <span
                          style={{
                            display: "inline-block",
                            maxWidth: "520px",
                            whiteSpace: "normal",
                            lineHeight: 1.4,
                          }}
                        >
                          {run.error_message?.trim() ||
                            run.solver_status_display ||
                            run.solver_status ||
                            "Scheduling run failed without a diagnostic."}
                        </span>
                      ) : (
                        "--"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

export default Scheduling;



