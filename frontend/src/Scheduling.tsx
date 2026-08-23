import { useEffect, useState } from "react";
import { AlertCircle, PlayCircle, RefreshCw } from "lucide-react";

import http from "./services/http";
import {
  createSchedulingRun,
  executeSchedulingRun,
} from "./services/scheduling";

import Timetable from "./pages/Timetable";

type AcademicTerm = {
  id: string;
  name: string;
  academic_year_name?: string;
  number?: number;
  start_date?: string;
  end_date?: string;
  is_active?: boolean;
};

export default function Scheduling() {
  const [terms, setTerms] = useState<AcademicTerm[]>([]);
  const [selectedTerm, setSelectedTerm] = useState("");

  const [versionName, setVersionName] =
    useState("Generated Timetable");

  const [versionNumber, setVersionNumber] = useState(1);

  const [loadingTerms, setLoadingTerms] = useState(true);
  const [generating, setGenerating] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  /*
   * Changing this key remounts Timetable.tsx.
   *
   * Timetable.tsx remains the SINGLE SOURCE OF TRUTH
   * for displaying generated timetable data.
   */
  const [timetableKey, setTimetableKey] = useState(0);

  useEffect(() => {
    let mounted = true;

    async function loadTerms() {
      try {
        setLoadingTerms(true);
        setError("");

        const response = await http.get<AcademicTerm[]>(
          "/core/terms/",
        );

        if (!mounted) {
          return;
        }

        const data = response.data ?? [];

        setTerms(data);

        const activeTerm =
          data.find((term) => term.is_active) ?? data[0];

        if (activeTerm) {
          setSelectedTerm(activeTerm.id);
        }
      } catch (requestError: any) {
        if (!mounted) {
          return;
        }

        setError(
          requestError?.response?.data?.detail ??
            requestError?.response?.data?.error ??
            requestError?.message ??
            "Unable to load academic terms.",
        );
      } finally {
        if (mounted) {
          setLoadingTerms(false);
        }
      }
    }

    void loadTerms();

    return () => {
      mounted = false;
    };
  }, []);

  async function handleGenerate() {
    if (!selectedTerm) {
      setError("Please select an academic term.");
      return;
    }

    try {
      setGenerating(true);
      setError("");
      setSuccess("");

      /*
       * STEP 1
       * Create the scheduling run.
       */
      const run = await createSchedulingRun({
        term: selectedTerm,
        version_name:
          versionName.trim() || "Generated Timetable",
        version_number:
          Number.isFinite(versionNumber) && versionNumber > 0
            ? versionNumber
            : 1,
      });

      /*
       * STEP 2
       * Execute the backend scheduling engine.
       */
      const completedRun = await executeSchedulingRun(run.id, {
        version_name:
          versionName.trim() || "Generated Timetable",
        version_number:
          Number.isFinite(versionNumber) && versionNumber > 0
            ? versionNumber
            : 1,
      });

      /*
       * The backend has generated and persisted the timetable.
       *
       * We do NOT construct or maintain another timetable here.
       */
      if (
        completedRun.status?.toUpperCase() !== "COMPLETED"
      ) {
        throw new Error(
          completedRun.error_message ||
            "Timetable generation did not complete successfully.",
        );
      }

      /*
       * Force Timetable.tsx to remount.
       *
       * Its own loadTimetable() then requests the latest
       * completed scheduling run and displays its persisted
       * TimetableVersion.
       */
      setTimetableKey((current) => current + 1);

      setSuccess(
        "Timetable generated successfully. The live timetable below has been refreshed.",
      );

      /*
       * Prepare the next version number.
       */
      setVersionNumber((current) => current + 1);
    } catch (requestError: any) {
      setError(
        requestError?.response?.data?.detail ??
          requestError?.response?.data?.error ??
          requestError?.message ??
          "Timetable generation failed.",
      );
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="scheduling-page">
      <div className="page-header">
        <div>
          <span className="eyebrow">SCHEDULING ENGINE</span>

          <h1>Generate Timetable</h1>

          <p>
            Generate a complete school timetable using the
            scheduling engine and view the newly generated
            timetable immediately below.
          </p>
        </div>
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Timetable Generation</h2>

            <p>
              The scheduling engine enforces teacher clashes,
              room clashes, availability, lesson requirements
              and teacher free-afternoon constraints.
            </p>
          </div>
        </div>

        <div className="generation-panel">
          <div className="generation-icon">
            <PlayCircle size={32} />
          </div>

          <div className="generation-content">
            <h3>Generate a new timetable</h3>

            <div
              style={{
                display: "grid",
                gap: "14px",
                marginTop: "18px",
                maxWidth: "720px",
              }}
            >
              <label>
                <strong>Academic Term</strong>

                <select
                  value={selectedTerm}
                  onChange={(event) =>
                    setSelectedTerm(event.target.value)
                  }
                  disabled={loadingTerms || generating}
                  style={{
                    display: "block",
                    width: "100%",
                    marginTop: "6px",
                    padding: "10px",
                  }}
                >
                  <option value="">
                    {loadingTerms
                      ? "Loading terms..."
                      : "Select term"}
                  </option>

                  {terms.map((term) => (
                    <option key={term.id} value={term.id}>
                      {term.name}
                      {term.academic_year_name
                        ? ` - ${term.academic_year_name}`
                        : ""}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                <strong>Version Name</strong>

                <input
                  type="text"
                  value={versionName}
                  onChange={(event) =>
                    setVersionName(event.target.value)
                  }
                  disabled={generating}
                  style={{
                    display: "block",
                    width: "100%",
                    marginTop: "6px",
                    padding: "10px",
                  }}
                />
              </label>

              <label>
                <strong>Version Number</strong>

                <input
                  type="number"
                  min="1"
                  value={versionNumber}
                  onChange={(event) =>
                    setVersionNumber(
                      Math.max(
                        1,
                        Number(event.target.value) || 1,
                      ),
                    )
                  }
                  disabled={generating}
                  style={{
                    display: "block",
                    width: "160px",
                    marginTop: "6px",
                    padding: "10px",
                  }}
                />
              </label>

              <button
                type="button"
                className="primary-button"
                onClick={() => void handleGenerate()}
                disabled={
                  generating ||
                  loadingTerms ||
                  !selectedTerm
                }
              >
                {generating ? (
                  <>
                    <RefreshCw
                      size={18}
                      className="spin"
                    />
                    Generating...
                  </>
                ) : (
                  <>
                    <PlayCircle size={18} />
                    Generate Timetable
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </section>

      {error && (
        <div className="timetable-error">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div
          className="status-badge ready"
          style={{ marginTop: "16px" }}
        >
          {success}
        </div>
      )}

      <section style={{ marginTop: "24px" }}>
        <Timetable key={timetableKey} />
      </section>
    </div>
  );
}
