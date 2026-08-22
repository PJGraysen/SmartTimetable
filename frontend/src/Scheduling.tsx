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
  getSchedulingRunResults,
  getSchedulingRuns,
  type SchedulingRun,
} from "./services/scheduling";
import {
  getAcademicTerms,
  type AcademicTerm,
} from "./services/core";

type GeneratedResult = {
  id: string;
  term: string;
  status: string;
  solver_status: string | null;
  started_at: string | null;
  completed_at: string | null;
  objective_value: string | number | null;
  error_message: string;
  statistics: Record<string, unknown> | null;
  timetable_version: {
    id: string;
    term: string;
    term_name: string;
    name: string;
    version_number: number;
    is_published: boolean;
    is_active: boolean;
    entries_count: number;
    entries: Array<{
      id: string;
      day: string;
      day_display: string;
      period: string;
      period_number: number;
      period_name: string;
      period_start_time: string;
      period_end_time: string;
      teaching_group: string;
      teaching_group_name: string;
      teacher: string;
      teacher_name: string;
      lesson_requirement: string;
      lesson_requirement_name: string;
      room: string | null;
      room_name: string | null;
    }>;
  } | null;
};

function Scheduling() {
  const [terms, setTerms] = useState<AcademicTerm[]>([]);
  const [selectedTerm, setSelectedTerm] = useState("");
  const [runs, setRuns] = useState<SchedulingRun[]>([]);
  const [generatedResult, setGeneratedResult] =
    useState<GeneratedResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const [termsData, runsData] = await Promise.all([
        getAcademicTerms(),
        getSchedulingRuns(),
      ]);

      setTerms(termsData);
      setRuns(runsData);

      const activeTerm = termsData.find((term) => term.is_active);

      if (activeTerm && !selectedTerm) {
        setSelectedTerm(activeTerm.id);
      }
    } catch {
      setError(
        "Unable to load academic terms and scheduling runs. " +
          "Make sure the Django API is running.",
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
    setGeneratedResult(null);

    try {
      const run = await createSchedulingRun({
        term: selectedTerm,
        version_name: "Generated Timetable",
        version_number: 1,
      });

      const executedRun = await executeSchedulingRun(run.id, {
        version_name: "Generated Timetable",
        version_number: 1,
      });

      const result = await getSchedulingRunResults(run.id);

      setGeneratedResult(result);

      setRuns((current) =>
        current.map((item) =>
          item.id === run.id ? executedRun : item,
        ),
      );

      await loadData();
    } catch (err: any) {
      setError(
        err?.response?.data?.error ||
          err?.response?.data?.detail ||
          err?.detail ||
          err?.error ||
          "Timetable generation failed.",
      );

      await loadData();
    } finally {
      setGenerating(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const entries =
    generatedResult?.timetable_version?.entries ?? [];

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Scheduling</h1>
          <p>
            Generate and monitor automated timetable scheduling runs.
          </p>
        </div>

        <div className="page-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => void loadData()}
            disabled={loading || generating}
          >
            <RefreshCw
              size={17}
              className={loading ? "spin" : ""}
            />
            Refresh
          </button>

          <button
            type="button"
            className="primary-button"
            onClick={() => void generateTimetable()}
            disabled={generating || loading || !selectedTerm}
          >
            <PlayCircle size={18} />
            {generating ? "Generating..." : "Generate Timetable"}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert error">
          <AlertCircle size={19} />

          <div>
            <strong>Scheduling error</strong>
            <span>{error}</span>
          </div>
        </div>
      )}

      <section className="panel scheduling-panel">
        <div className="panel-header">
          <div>
            <h2>Generate Timetable</h2>
            <p>
              Select the academic term for timetable generation.
            </p>
          </div>
        </div>

        <div className="scheduling-form">
          <div className="form-group">
            <label htmlFor="academic-term">
              Academic Term
            </label>

            <select
              id="academic-term"
              value={selectedTerm}
              onChange={(event) =>
                setSelectedTerm(event.target.value)
              }
              disabled={loading || generating}
            >
              <option value="">
                {loading
                  ? "Loading academic terms..."
                  : "Select academic term"}
              </option>

              {terms.map((term) => (
                <option key={term.id} value={term.id}>
                  {term.academic_year_name} — {term.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {entries.length > 0 && (
        <section className="panel scheduling-panel">
          <div className="panel-header">
            <div>
              <h2>Generated Timetable</h2>
              <p>
                {entries.length} timetable entries generated
                successfully.
              </p>
            </div>

            <span className="timetable-created">
              <CheckCircle2 size={15} />
              {generatedResult?.timetable_version?.name ??
                "Generated Timetable"}
            </span>
          </div>

          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Day</th>
                  <th>Period</th>
                  <th>Subject</th>
                  <th>Teacher</th>
                  <th>Group</th>
                  <th>Room</th>
                </tr>
              </thead>

              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id}>
                    <td>
                      {entry.day_display || entry.day}
                    </td>

                    <td>
                      {entry.period_number}
                      {entry.period_name
                        ? ` — ${entry.period_name}`
                        : ""}
                    </td>

                    <td>
                      {entry.lesson_requirement_name}
                    </td>

                    <td>
                      {entry.teacher_name}
                    </td>

                    <td>
                      {entry.teaching_group_name}
                    </td>

                    <td>
                      {entry.room_name ?? "--"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="panel scheduling-panel">
        <div className="panel-header">
          <div>
            <h2>Scheduling Runs</h2>
            <p>
              Recent timetable generation attempts and their
              current status.
            </p>
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
              No timetable generation runs have been recorded
              yet. Select an academic term and generate the
              first timetable.
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
                  <th>Timetable Version</th>
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
                        {run.status.toUpperCase() ===
                        "COMPLETED" ? (
                          <CheckCircle2 size={15} />
                        ) : run.status.toUpperCase() ===
                          "FAILED" ? (
                          <AlertCircle size={15} />
                        ) : (
                          <Clock size={15} />
                        )}

                        {run.status_display}
                      </span>
                    </td>

                    <td>
                      {run.created_at
                        ? new Date(
                            run.created_at,
                          ).toLocaleString()
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