import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Clock, PlayCircle, RefreshCw } from "lucide-react";
import api from "./api";

type SchedulingRun = {
  id: string;
  status: string;
  term: string;
  term_name?: string;
  created_at?: string;
  started_at?: string | null;
  completed_at?: string | null;
  timetable_version?: string | null;
};

type SchedulingRunsResponse = {
  value?: SchedulingRun[];
  Count?: number;
};

function Scheduling() {
  const [runs, setRuns] = useState<SchedulingRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  async function loadRuns() {
    setLoading(true);
    setError("");

    try {
      const response = await api.get<SchedulingRunsResponse | SchedulingRun[]>(
        "/scheduling/runs/",
      );

      const data = response.data;
      setRuns(Array.isArray(data) ? data : data.value ?? []);
    } catch {
      setError(
        "Unable to load scheduling runs. Make sure the Django API is running.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function generateTimetable() {
    setGenerating(true);
    setError("");

    try {
      const response = await api.post("/scheduling/runs/", {
        term: "2026 Term 3",
      });

      const run = response.data;

      await api.post(`/scheduling/runs/${run.id}/execute/`, {
        version_name: "Generated Timetable",
      });

      await loadRuns();
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.response?.data?.error ||
          "Timetable generation failed.",
      );
    } finally {
      setGenerating(false);
    }
  }

  useEffect(() => {
    loadRuns();
  }, []);

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Scheduling</h1>
          <p>Generate and monitor automated timetable schedules.</p>
        </div>

        <div className="page-actions">
          <button
            className="secondary-button"
            onClick={loadRuns}
            disabled={loading || generating}
          >
            <RefreshCw size={17} />
            Refresh
          </button>

          <button
            className="primary-button"
            onClick={generateTimetable}
            disabled={generating}
          >
            <PlayCircle size={18} />
            {generating ? "Generating..." : "Generate Timetable"}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert error">
          <AlertCircle size={19} />
          <span>{error}</span>
        </div>
      )}

      <section className="scheduling-info">
        <div className="info-card">
          <CheckCircle2 size={20} />
          <div>
            <strong>Hard Constraints</strong>
            <span>
              Teacher clashes, group clashes, room clashes, availability and
              free afternoons are enforced.
            </span>
          </div>
        </div>

        <div className="info-card">
          <Clock size={20} />
          <div>
            <strong>Optimization</strong>
            <span>
              The solver optimizes timetable quality after satisfying hard
              constraints.
            </span>
          </div>
        </div>
      </section>

      <section className="panel scheduling-panel">
        <div className="panel-header">
          <div>
            <h2>Scheduling Runs</h2>
            <p>History of timetable generation attempts.</p>
          </div>
        </div>

        {loading ? (
          <div className="table-state">Loading scheduling runs...</div>
        ) : runs.length === 0 ? (
          <div className="empty-state">
            <PlayCircle size={38} />
            <h3>No scheduling runs yet</h3>
            <p>
              Start a timetable generation run to create your first automated
              timetable.
            </p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Term</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Timetable</th>
                </tr>
              </thead>

              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td>
                      <strong>{run.id}</strong>
                    </td>
                    <td>{run.term_name ?? run.term}</td>
                    <td>
                      <span
                        className={`status-badge ${run.status.toLowerCase()}`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td>
                      {run.created_at
                        ? new Date(run.created_at).toLocaleString()
                        : "—"}
                    </td>
                    <td>
                      {run.timetable_version ? (
                        <span className="timetable-created">
                          <CheckCircle2 size={15} />
                          Available
                        </span>
                      ) : (
                        "—"
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
