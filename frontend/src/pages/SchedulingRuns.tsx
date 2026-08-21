import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  LoaderCircle,
  Play,
  RefreshCw,
} from "lucide-react";
import api from "../services/api";

type AcademicTerm = {
  id: string;
  name: string;
  academic_year: string;
  academic_year_name: string;
  number: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
};

type SchedulingRun = {
  id: string;
  term: string;
  term_name: string;
  timetable_version: string | null;
  status: string;
  status_display: string;
  solver_status: string | null;
  solver_status_display: string | null;
  started_at: string | null;
  completed_at: string | null;
  objective_value: string | number | null;
  error_message: string;
  statistics: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

function statusClass(status: string) {
  switch (status.toUpperCase()) {
    case "COMPLETED":
      return "status-success";
    case "FAILED":
      return "status-error";
    case "RUNNING":
      return "status-running";
    default:
      return "status-pending";
  }
}

function formatDate(value: string | null) {
  if (!value) return "â€”";
  return new Date(value).toLocaleString();
}

export default function SchedulingRuns() {
  const [terms, setTerms] = useState<AcademicTerm[]>([]);
  const [selectedTerm, setSelectedTerm] = useState("");
  const [runs, setRuns] = useState<SchedulingRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [termsResponse, runsResponse] = await Promise.all([
        api.get<AcademicTerm[]>("/core/terms/"),
        api.get<SchedulingRun[]>("/scheduling/runs/"),
      ]);

      setTerms(
        Array.isArray(termsResponse.data)
          ? termsResponse.data
          : []
      );

      setRuns(
        Array.isArray(runsResponse.data)
          ? runsResponse.data
          : []
      );
    } catch {
      setError(
        "Unable to load academic terms and scheduling runs. " +
          "Make sure the Django API is running."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  async function createRun() {
    if (!selectedTerm) {
      setError("Select an academic term first.");
      return;
    }

    setCreating(true);
    setMessage(null);
    setError(null);

    try {
      const response = await api.post<SchedulingRun>(
        "/scheduling/runs/",
        {
          term: selectedTerm,
        }
      );

      setRuns((current) => [response.data, ...current]);
      setMessage(
        `Scheduling run created for ${response.data.term_name}.`
      );
    } catch (requestError: any) {
      setError(
        requestError?.response?.data?.term?.[0] ??
          requestError?.response?.data?.detail ??
          "Unable to create the scheduling run."
      );
    } finally {
      setCreating(false);
    }
  }

  async function executeRun(run: SchedulingRun) {
    setExecutingId(run.id);
    setMessage(null);
    setError(null);

    try {
      const response = await api.post<SchedulingRun>(
        `/scheduling/runs/${run.id}/execute/`,
        {
          version_name: "Generated Timetable",
          version_number: 1,
        }
      );

      setRuns((current) =>
        current.map((item) =>
          item.id === run.id ? response.data : item
        )
      );

      setMessage(
        `Scheduling run ${run.id} completed successfully.`
      );
    } catch (requestError: any) {
      setError(
        requestError?.response?.data?.detail ??
          "Scheduling execution failed."
      );

      await loadData();
    } finally {
      setExecutingId(null);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">SCHEDULING ENGINE</span>
          <h1>Scheduling Runs</h1>
          <p>
            Create, execute and monitor automated timetable
            generation runs.
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button
            className="secondary-button"
            onClick={() => void loadData()}
            disabled={loading}
          >
            <RefreshCw
              size={17}
              className={loading ? "spin" : undefined}
            />
            Refresh
          </button>

          <button
            className="primary-button"
            onClick={() => void createRun()}
            disabled={creating || !selectedTerm}
          >
            {creating ? (
              <LoaderCircle className="spin" size={17} />
            ) : (
              <Play size={17} />
            )}
            {creating ? "Creating..." : "New Scheduling Run"}
          </button>
        </div>
      </div>

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
            disabled={loading || creating}
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
                {term.name} â€” {term.academic_year}
              </option>
            ))}
          </select>
        </div>
      </div>

      {message && (
        <div className="section-card">
          <div className="empty-state">
            <CheckCircle2 size={24} />
            <p>{message}</p>
          </div>
        </div>
      )}

      {error && (
        <div className="section-card">
          <div className="empty-state">
            <AlertCircle size={24} />
            <p>{error}</p>
          </div>
        </div>
      )}

      <div className="section-card">
        <div className="section-card-header">
          <div>
            <span className="eyebrow">RUN HISTORY</span>
            <h2>Scheduling Runs</h2>
          </div>

          <span>{runs.length} run(s)</span>
        </div>

        {loading ? (
          <div className="empty-state">
            <LoaderCircle className="spin" size={28} />
            <h2>Loading scheduling runs...</h2>
          </div>
        ) : runs.length === 0 ? (
          <div className="empty-state">
            <Clock3 size={28} />
            <h2>No scheduling runs</h2>
            <p>
              Select an academic term and create a scheduling run.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Term</th>
                  <th>Status</th>
                  <th>Solver</th>
                  <th>Objective</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {runs.map((run) => {
                  const executable = run.status === "PENDING";

                  const executing = executingId === run.id;

                  return (
                    <tr key={run.id}>
                      <td>
                        <strong>{run.term_name}</strong>
                      </td>

                      <td>
                        <span
                          className={`status-badge ${statusClass(
                            run.status
                          )}`}
                        >
                          {run.status_display}
                        </span>
                      </td>

                      <td>
                        {run.solver_status_display ??
                          run.solver_status ??
                          "â€”"}
                      </td>

                      <td>{run.objective_value ?? "â€”"}</td>

                      <td>{formatDate(run.created_at)}</td>

                      <td>
                        {executable ? (
                          <button
                            className="secondary-button"
                            onClick={() => void executeRun(run)}
                            disabled={executing}
                          >
                            {executing ? (
                              <LoaderCircle
                                size={15}
                                className="spin"
                              />
                            ) : (
                              <Play size={15} />
                            )}
                            {executing
                              ? "Generating..."
                              : "Execute"}
                          </button>
                        ) : (
                          <span>
                            {run.completed_at
                              ? formatDate(run.completed_at)
                              : "â€”"}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
