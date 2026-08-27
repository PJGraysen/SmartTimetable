import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import {
  getSchedulingRunResults,
  getSchedulingRuns,
  type SchedulingRun,
  type TimetableEntryResult,
  type TimetableVersionResult,
} from "../services/scheduling";
import "./Timetable.css";

type TimetableColumn =
  | {
      kind: "period";
      number: number;
      label: string;
      start: string;
      end: string;
    }
  | {
      kind: "break" | "activity";
      label: string;
      start: string;
      end: string;
    };

const DAYS = [
  { code: "MON", label: "Mon" },
  { code: "TUE", label: "Tue" },
  { code: "WED", label: "Wed" },
  { code: "THU", label: "Thur" },
  { code: "FRI", label: "Fri" },
] as const;

const COLUMNS: TimetableColumn[] = [
  { kind: "period", number: 1, label: "Pd 1", start: "8:00", end: "8:40" },
  { kind: "period", number: 2, label: "Pd 2", start: "8:40", end: "9:20" },
  { kind: "period", number: 3, label: "Pd 3", start: "9:20", end: "10:00" },
  { kind: "period", number: 4, label: "Pd 4", start: "10:00", end: "10:40" },
  {
    kind: "break",
    label: "Tea",
    start: "10:40",
    end: "11:00",
  },
  { kind: "period", number: 5, label: "Pd 5", start: "11:00", end: "11:40" },
  { kind: "period", number: 6, label: "Pd 6", start: "11:40", end: "12:20" },
  { kind: "period", number: 7, label: "Pd 7", start: "12:20", end: "1:00" },
  {
    kind: "break",
    label: "Lunch",
    start: "1:00",
    end: "2:00",
  },
  { kind: "period", number: 8, label: "Pd 8", start: "2:00", end: "2:40" },
  { kind: "period", number: 9, label: "Pd 9", start: "2:40", end: "3:20" },
  { kind: "period", number: 10, label: "Pd 10", start: "3:20", end: "4:00" },
  {
    kind: "break",
    label: "Prayer",
    start: "4:00",
    end: "4:40",
  },
  {
    kind: "activity",
    label: "Activity",
    start: "4:40",
    end: "5:45",
  },
];

const SUBJECT_ABBREVIATIONS: Record<string, string> = {
  mathematics: "MAT",
  math: "MAT",
  english: "ENG",
  kiswahili: "KIS",
  "christian religious education": "CRE",
  "christian religious studies": "CRE",
  physics: "PHY",
  biology: "BIO",
  chemistry: "CHEM",
  ict: "ICT",
  "information communication technology": "ICT",
  "computer studies": "COMP",
  "computer science": "COMP",
  commerce: "COMP",
  business: "A/B",
  "business studies": "A/B",
  geography: "G/H",
  history: "HIST",
  agriculture: "AGRI",
  music: "MUS",
  "physical education": "PE",
};

function abbreviateSubject(value: string) {
  const normalized = value.trim().toLowerCase();

  if (SUBJECT_ABBREVIATIONS[normalized]) {
    return SUBJECT_ABBREVIATIONS[normalized];
  }

  for (const [name, abbreviation] of Object.entries(
    SUBJECT_ABBREVIATIONS,
  )) {
    if (normalized.includes(name)) {
      return abbreviation;
    }
  }

  const words = value
    .replace(/[^A-Za-z0-9 ]/g, " ")
    .split(/\s+/)
    .filter(Boolean);

  if (words.length === 1) {
    return words[0].slice(0, 5).toUpperCase();
  }

  return words
    .slice(0, 3)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

function teacherCode(entry: TimetableEntryResult) {
  const candidate =
    entry.teacher_code ??
    entry.employee_code ??
    entry.teacher_name ??
    "";

  return candidate.trim() || "--";
}

function subjectCode(entry: TimetableEntryResult) {
  if (entry.subject_code?.trim()) {
    return entry.subject_code.trim().toUpperCase();
  }

  return abbreviateSubject(
    entry.subject_name ||
      entry.lesson_requirement_name ||
      "Subject",
  );
}

function entryLabel(entry: TimetableEntryResult) {
  const subject = subjectCode(entry);
  const teacher = teacherCode(entry);

  return `${subject} ${teacher}`;
}

function groupEntries(entries: TimetableEntryResult[]) {
  const grouped = new Map<string, TimetableEntryResult[]>();

  for (const entry of entries) {
    const key = `${entry.day}:${entry.period_number}`;

    const existing = grouped.get(key);

    if (existing) {
      existing.push(entry);
    } else {
      grouped.set(key, [entry]);
    }
  }

  return grouped;
}

function formatRunDate(value: string | null) {
  if (!value) {
    return "--";
  }

  return new Date(value).toLocaleString();
}

function extractTimetableVersion(
  value: unknown,
): TimetableVersionResult | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  return value as TimetableVersionResult;
}

export default function Timetable() {
  const [runs, setRuns] = useState<SchedulingRun[]>([]);
  const [timetable, setTimetable] =
    useState<TimetableVersionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadTimetable = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const runsData = await getSchedulingRuns();
      setRuns(runsData);

      const completedRun = runsData.find(
        (run) =>
          run.status.toUpperCase() === "COMPLETED" &&
          Boolean(run.timetable_version),
      );

      if (!completedRun) {
        setTimetable(null);
        return;
      }

      const result = await getSchedulingRunResults(completedRun.id);

      const version = extractTimetableVersion(
        result?.timetable_version,
      );

      setTimetable(version);
    } catch (requestError: any) {
      setError(
        requestError?.response?.data?.detail ??
          requestError?.response?.data?.error ??
          "Unable to load the generated timetable.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTimetable();
  }, [loadTimetable]);

  const groupedEntries = useMemo(
    () => groupEntries(timetable?.entries ?? []),
    [timetable],
  );

  const latestRun = runs.find(
    (run) =>
      run.status.toUpperCase() === "COMPLETED" &&
      Boolean(run.timetable_version),
  );

  return (
    <div className="timetable-page">
      <div className="timetable-toolbar">
        <div>
          <span className="eyebrow">GENERATED TIMETABLE</span>
          <h1>Whole-School Timetable</h1>
          <p>
            Compact weekly timetable showing subjects and teacher codes.
          </p>
        </div>

        <button
          type="button"
          className="secondary-button timetable-refresh"
          onClick={() => void loadTimetable()}
          disabled={loading}
        >
          <RefreshCw
            size={16}
            className={loading ? "spin" : undefined}
          />
          Refresh
        </button>
      </div>

      {error && (
        <div className="timetable-error">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="timetable-state">
          <RefreshCw size={22} className="spin" />
          <span>Loading generated timetable...</span>
        </div>
      ) : !timetable ? (
        <div className="timetable-state">
          <strong>No generated timetable available.</strong>
          <span>
            Generate a timetable from the Scheduling page first.
          </span>
        </div>
      ) : (
        <>
          <section className="timetable-heading-card">
            <div>
              <strong>QUEEN OF APOSTLE SEMINARY</strong>
              <span>WHOLE-SCHOOL TIMETABLE</span>
            </div>

            <div className="timetable-meta">
              <span>
                {timetable.term_name || latestRun?.term_name || "--"}
              </span>
              <span>
                {timetable.name || "Generated Timetable"}
              </span>
              <span>
                Version {timetable.version_number ?? "--"}
              </span>
              <span>
                {formatRunDate(latestRun?.completed_at ?? null)}
              </span>
            </div>
          </section>

          <section className="timetable-card">
            <div className="timetable-scroll">
              <table className="whole-school-timetable">
                <colgroup>
                  <col className="day-column" />

                  {COLUMNS.map((column) => (
                    <col
                      key={`${column.kind}-${column.label}`}
                      className={
                        column.kind === "period"
                          ? "period-column"
                          : "special-column"
                      }
                    />
                  ))}
                </colgroup>

                <thead>
                  <tr>
                    <th className="days-header">DAYS</th>

                    {COLUMNS.map((column) => (
                      <th
                        key={`${column.kind}-${column.label}`}
                        className={`timetable-header ${column.kind}`}
                      >
                        <span>{column.label}</span>
                        <small>
                          {column.start}–{column.end}
                        </small>
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {DAYS.map((day) => (
                    <tr key={day.code}>
                      <th className="day-label">{day.label}</th>

                      {COLUMNS.map((column) => {
                        if (column.kind !== "period") {
                          return (
                            <td
                              key={`${day.code}-${column.label}`}
                              className={`special-cell ${column.kind}`}
                            >
                              <strong>
                                {column.label === "Tea"
                                  ? "TEA"
                                  : column.label === "Lunch"
                                    ? "LUNCH"
                                    : column.label === "Prayer"
                                      ? "PRAYER"
                                      : "ACTIVITY"}
                              </strong>
                              <small>
                                {column.start}–{column.end}
                              </small>
                            </td>
                          );
                        }

                        const entries =
                          groupedEntries.get(
                            `${day.code}:${column.number}`,
                          ) ?? [];

                        return (
                          <td
                            key={`${day.code}-pd-${column.number}`}
                            className="lesson-cell"
                          >
                            {entries.length === 0 ? (
                              <span className="empty-slot">—</span>
                            ) : (
                              <div className="lesson-stack">
                                {entries.map((entry) => (
                                  <div
                                    className="lesson-entry"
                                    key={entry.id}
                                    title={`${entry.lesson_requirement_name} — ${entry.teacher_name}`}
                                  >
                                    <strong>
                                      {entryLabel(entry)}
                                    </strong>

                                    {entry.teaching_group_name && (
                                      <small>
                                        {entry.teaching_group_name}
                                      </small>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="timetable-legend">
              <span>
                <strong>Subject</strong> + <strong>Teacher code</strong>
              </span>
              <span>
                {timetable.entries_count ?? timetable.entries.length}{" "}
                scheduled entries
              </span>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

