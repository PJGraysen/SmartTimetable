import { useCallback, useEffect, useMemo, useState } from "react";
import { Printer, RefreshCw } from "lucide-react";
import {
  getSchedulingRunResults,
  getSchedulingRuns,
  type SchedulingRun,
  type TimetableEntryResult,
} from "../services/scheduling";

type TimetableColumn = {
  key: string;
  label: string;
  time: string;
  kind: "lesson" | "tea" | "lunch" | "prayers" | "activities";
  period?: number;
};

type ClassDefinition = {
  label: string;
  aliases: string[];
};

type DayDefinition = {
  code: string;
  label: string;
};

const DAYS: DayDefinition[] = [
  { code: "MON", label: "MONDAY" },
  { code: "TUE", label: "TUESDAY" },
  { code: "WED", label: "WEDNESDAY" },
  { code: "THU", label: "THURSDAY" },
  { code: "FRI", label: "FRIDAY" },
];

const CLASSES: ClassDefinition[] = [
  {
    label: "Form 4E",
    aliases: ["form 4e", "form 4 east", "f4 east", "4e", "f4e"],
  },
  {
    label: "Form 4W",
    aliases: ["form 4w", "form 4 west", "f4 west", "4w", "f4w"],
  },
  {
    label: "Form 3E",
    aliases: ["form 3e", "form 3 east", "f3 east", "3e", "f3e"],
  },
  {
    label: "Form 3W",
    aliases: ["form 3w", "form 3 west", "f3 west", "3w", "f3w"],
  },
  {
    label: "Grade 10E",
    aliases: [
      "grade 10e",
      "grade 10 east",
      "10e",
      "10 east",
      "grade10e",
      "g10e",
    ],
  },
  {
    label: "Grade 10W",
    aliases: [
      "grade 10w",
      "grade 10 west",
      "10w",
      "10 west",
      "grade10w",
      "g10w",
    ],
  },
  {
    label: "Grade 9E",
    aliases: [
      "grade 9e",
      "grade 9 east",
      "9e",
      "9 east",
      "grade9e",
      "g9e",
    ],
  },
  {
    label: "Grade 9W",
    aliases: [
      "grade 9w",
      "grade 9 west",
      "9w",
      "9 west",
      "grade9w",
      "g9w",
    ],
  },
  {
    label: "Grade 8E",
    aliases: [
      "grade 8e",
      "grade 8 east",
      "8e",
      "8 east",
      "grade8e",
      "g8e",
    ],
  },
  {
    label: "Grade 8W",
    aliases: [
      "grade 8w",
      "grade 8 west",
      "8w",
      "8 west",
      "grade8w",
      "g8w",
    ],
  },
];

const COLUMNS: TimetableColumn[] = [
  {
    key: "p1",
    label: "P1",
    time: "08:00–08:40",
    kind: "lesson",
    period: 1,
  },
  {
    key: "p2",
    label: "P2",
    time: "08:40–09:20",
    kind: "lesson",
    period: 2,
  },
  {
    key: "p3",
    label: "P3",
    time: "09:20–10:00",
    kind: "lesson",
    period: 3,
  },
  {
    key: "p4",
    label: "P4",
    time: "10:00–10:40",
    kind: "lesson",
    period: 4,
  },
  {
    key: "tea",
    label: "TEA",
    time: "10:40–11:00",
    kind: "tea",
  },
  {
    key: "p5",
    label: "P5",
    time: "11:00–11:40",
    kind: "lesson",
    period: 6,
  },
  {
    key: "p6",
    label: "P6",
    time: "11:40–12:20",
    kind: "lesson",
    period: 7,
  },
  {
    key: "p7",
    label: "P7",
    time: "12:20–13:00",
    kind: "lesson",
    period: 8,
  },
  {
    key: "lunch",
    label: "LUNCH",
    time: "13:00–14:00",
    kind: "lunch",
  },
  {
    key: "p8",
    label: "P8",
    time: "14:00–14:40",
    kind: "lesson",
    period: 10,
  },
  {
    key: "p9",
    label: "P9",
    time: "14:40–15:20",
    kind: "lesson",
    period: 11,
  },
  {
    key: "p10",
    label: "P10",
    time: "15:20–16:00",
    kind: "lesson",
    period: 12,
  },
  {
    key: "prayers",
    label: "PRAYERS",
    time: "16:00–16:30",
    kind: "prayers",
  },
  {
    key: "activities",
    label: "ACTIVITIES",
    time: "16:30–17:45",
    kind: "activities",
  },
];

function normalise(value: unknown): string {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function text(value: unknown): string {
  if (typeof value === "string") {
    return value.trim();
  }

  if (typeof value === "number") {
    return String(value);
  }

  return "";
}

function normalisedSubjectCode(entry: TimetableEntryResult): string {
  return text(entry.subject_code);
}

function subjectName(entry: TimetableEntryResult): string {
  return text(entry.subject_name);
}

function teacherCode(entry: TimetableEntryResult): string {
  return text(entry.teacher_code) || text(entry.employee_code);
}

function teacherName(entry: TimetableEntryResult): string {
  return text(entry.teacher_name);
}

function groupName(entry: TimetableEntryResult): string {
  return text(entry.instructional_group_name);
}

function canonicalDayCode(entry: TimetableEntryResult): string {
  const raw = normalise(entry.day || entry.day_display);

  if (raw === "mon" || raw === "monday") {
    return "MON";
  }

  if (raw === "tue" || raw === "tuesday" || raw === "tues") {
    return "TUE";
  }

  if (raw === "wed" || raw === "wednesday") {
    return "WED";
  }

  if (raw === "thu" || raw === "thursday" || raw === "thur" || raw === "thurs") {
    return "THU";
  }

  if (raw === "fri" || raw === "friday") {
    return "FRI";
  }

  return raw.toUpperCase();
}

function periodNumber(entry: TimetableEntryResult): number {
  const value = Number(entry.period_number);
  return Number.isFinite(value) ? value : 0;
}

function classMatches(
  entry: TimetableEntryResult,
  definition: ClassDefinition,
): boolean {
  const group = normalise(groupName(entry));

  if (!group) {
    return false;
  }

  return definition.aliases.some((alias) => {
    const candidate = normalise(alias);

    return (
      group === candidate ||
      group.includes(candidate) ||
      candidate.includes(group)
    );
  });
}

function electiveLabel(entry: TimetableEntryResult): string {
  const raw = entry as unknown as Record<string, unknown>;

  const candidates = [
    raw.elective_option,
    raw.electiveOption,
    raw.option,
    raw.option_name,
    raw.optionName,
    raw.elective_block,
    raw.electiveBlock,
    raw.pathway,
    raw.pathway_name,
    raw.pathwayName,
  ];

  for (const candidate of candidates) {
    const value = text(candidate);

    if (value) {
      return value;
    }
  }

  const requirement = text(entry.lesson_requirement_name);

  const optionMatch = requirement.match(
    /\b(option\s*[1-4]|elective\s*(?:option\s*)?[1-4])\b/i,
  );

  return optionMatch ? optionMatch[1] : "";
}

function formatLesson(entry: TimetableEntryResult) {
  return {
    code: normalisedSubjectCode(entry),
    name: subjectName(entry),
    teacher: teacherCode(entry),
    teacherName: teacherName(entry),
    elective: electiveLabel(entry),
  };
}

function completedRuns(runs: SchedulingRun[]): SchedulingRun[] {
  return [...runs]
    .filter((run) => {
      const status = normalise(run.status);

      return (
        status === "completed" ||
        status === "complete" ||
        status === "success" ||
        status === "successful"
      );
    })
    .sort((a, b) => {
      const left = Date.parse(a.completed_at || a.created_at || "");
      const right = Date.parse(b.completed_at || b.created_at || "");

      return right - left;
    });
}

function cellClass(column: TimetableColumn): string {
  if (column.kind === "tea") {
    return "tt-cell tt-break tt-tea";
  }

  if (column.kind === "lunch") {
    return "tt-cell tt-break tt-lunch";
  }

  if (column.kind === "prayers") {
    return "tt-cell tt-break tt-prayers";
  }

  if (column.kind === "activities") {
    return "tt-cell tt-break tt-activities";
  }

  return "tt-cell";
}

function Timetable() {
  const [entries, setEntries] = useState<TimetableEntryResult[]>([]);
  const [version, setVersion] = useState("Live timetable");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadTimetable = useCallback(async () => {
    setRefreshing(true);
    setError("");

    try {
      const runsData = await getSchedulingRuns();
      const runs = Array.isArray(runsData) ? runsData : [];
      const completed = completedRuns(runs);

      if (completed.length === 0) {
        setEntries([]);
        setVersion("No completed timetable");
        return;
      }

      const latestRun = completed[0];
      const result = await getSchedulingRunResults(latestRun.id);
      const timetableVersion = result.timetable_version;

      if (!timetableVersion) {
        setEntries([]);
        setVersion("Completed run has no timetable version");
        setError(
          "The latest completed scheduling run did not return a timetable version.",
        );
        return;
      }

      const backendEntries = Array.isArray(timetableVersion.entries)
        ? timetableVersion.entries
        : [];

      setEntries(backendEntries);

      setVersion(
        timetableVersion.name ||
          latestRun.timetable_version ||
          "Live timetable",
      );
    } catch (err) {
      console.error("Timetable loading failed:", err);

      setEntries([]);
      setVersion("Live timetable");

      setError(
        "Unable to load the latest completed timetable from the backend.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadTimetable();
  }, [loadTimetable]);

  const scheduledEntries = entries.length;

  const entriesBySlot = useMemo(() => {
    const map = new Map<string, TimetableEntryResult[]>();

    for (const entry of entries) {
      const day = canonicalDayCode(entry);
      const period = periodNumber(entry);

      if (!day || !period) {
        continue;
      }

      const key = `${day}:${period}`;
      const existing = map.get(key) || [];

      existing.push(entry);
      map.set(key, existing);
    }

    return map;
  }, [entries]);

  function getSlotEntries(
    dayCode: string,
    definition: ClassDefinition,
    period: number,
  ): TimetableEntryResult[] {
    const slot = entriesBySlot.get(`${dayCode}:${period}`) || [];

    return slot.filter((entry) => classMatches(entry, definition));
  }

  return (
    <>
      <style>{`
        .tt-page {
          min-width: 0;
          width: 100%;
          padding: 18px;
          box-sizing: border-box;
          background: #ffffff;
        }

        .tt-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 18px;
          margin-bottom: 14px;
        }

        .tt-title {
          margin: 0;
          font-size: 24px;
          line-height: 1.1;
          font-weight: 800;
          letter-spacing: -0.4px;
          color: #12315b;
        }

        .tt-subtitle {
          margin: 5px 0 0;
          color: #718096;
          font-size: 13px;
        }

        .tt-live {
          display: inline-flex;
          align-items: center;
          margin-left: 8px;
          padding: 3px 8px;
          border-radius: 5px;
          background: #22a447;
          color: white;
          font-size: 11px;
          font-weight: 800;
          vertical-align: middle;
        }

        .tt-actions {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .tt-status {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          border: 1px solid #cfe5d5;
          border-radius: 5px;
          background: #f5fbf6;
          color: #27783b;
          font-size: 13px;
          white-space: nowrap;
        }

        .tt-status-dot {
          width: 9px;
          height: 9px;
          border-radius: 50%;
          background: #20a347;
        }

        .tt-button {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          height: 40px;
          padding: 0 16px;
          border: 1px solid #2878dc;
          border-radius: 5px;
          background: white;
          color: #1262bd;
          font-weight: 700;
          cursor: pointer;
        }

        .tt-button:disabled {
          opacity: 0.6;
          cursor: wait;
        }

        .tt-table-wrap {
          width: 100%;
          overflow-x: auto;
          border: 1px solid #b9cbe0;
          box-sizing: border-box;
        }

        .tt-table {
          width: 100%;
          min-width: 1760px;
          table-layout: fixed;
          border-collapse: collapse;
          background: white;
        }

        .tt-table th,
        .tt-table td {
          border-right: 1px solid #d3dfeb;
          border-bottom: 1px solid #d3dfeb;
          padding: 0;
          box-sizing: border-box;
        }

        .tt-day-head,
        .tt-class-head {
          height: 54px;
          background: #244b72;
          color: white;
          text-align: center;
          font-size: 14px;
          font-weight: 800;
        }

        .tt-day-head {
          width: 112px;
        }

        .tt-class-head {
          width: 112px;
        }

        .tt-period-head {
          height: 54px;
          background: #edf4fa;
          color: #16263a;
          text-align: center;
          vertical-align: middle;
          font-weight: 800;
        }

        .tt-period-head .tt-period-label {
          display: block;
          font-size: 14px;
          line-height: 18px;
        }

        .tt-period-head .tt-period-time {
          display: block;
          margin-top: 2px;
          font-size: 10px;
          font-weight: 500;
          white-space: nowrap;
        }

        .tt-period-head.tt-tea {
          background: #fff8dd;
        }

        .tt-period-head.tt-lunch {
          background: #eff9e9;
        }

        .tt-period-head.tt-prayers,
        .tt-period-head.tt-activities {
          background: #f0edf9;
        }

        .tt-day {
          width: 112px;
          min-width: 112px;
          text-align: center;
          vertical-align: middle;
          background: #f5f9fd;
          color: #17366a;
          font-size: 16px;
          font-weight: 800;
        }

        .tt-class {
          width: 112px;
          min-width: 112px;
          height: 28px;
          padding-left: 8px !important;
          background: #ffffff;
          color: #1c2735;
          font-size: 12px;
          font-weight: 700;
          text-align: left;
          white-space: nowrap;
        }

        .tt-cell {
          height: 28px;
          min-height: 28px;
          background: #ffffff;
          color: #4b5563;
          text-align: center;
          vertical-align: middle;
          font-size: 10px;
          font-weight: 600;
          white-space: nowrap;
        }

        .tt-cell.tt-tea {
          background: #fff9df;
          color: #1f2937;
          font-weight: 800;
        }

        .tt-cell.tt-lunch {
          background: #eff9e9;
          color: #1f2937;
          font-weight: 800;
        }

        .tt-cell.tt-prayers,
        .tt-cell.tt-activities {
          background: #f2effa;
          color: #1f2937;
          font-weight: 800;
        }

        .tt-lesson {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 28px;
          line-height: 12px;
        }

        .tt-subject {
          font-weight: 800;
          color: #18395f;
        }

        .tt-subject-name {
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          font-size: 8px;
          color: #59697b;
          font-weight: 600;
        }

        .tt-teacher {
          font-size: 9px;
          color: #68778a;
          font-weight: 700;
        }

        .tt-elective {
          margin-top: 1px;
          padding: 1px 4px;
          border-radius: 3px;
          background: #eef3ff;
          color: #35558c;
          font-size: 7px;
          font-weight: 800;
          text-transform: uppercase;
        }

        .tt-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 4px;
          color: #718096;
          font-size: 11px;
        }

        .tt-error {
          margin: 10px 0;
          padding: 10px 12px;
          border: 1px solid #f0b5b5;
          background: #fff5f5;
          color: #a33a3a;
          font-size: 13px;
        }

        @media print {
          .tt-page {
            padding: 0;
          }

          .tt-actions {
            display: none;
          }

          .tt-table-wrap {
            overflow: visible;
            border: 1px solid #9fb4cb;
          }

          .tt-table {
            min-width: 1760px;
          }

          .tt-header {
            margin-bottom: 8px;
          }
        }
      `}</style>

      <main className="tt-page">
        <header className="tt-header">
          <div>
            <h1 className="tt-title">
              SCHOOL TIMETABLE
              <span className="tt-live">LIVE</span>
            </h1>

            <p className="tt-subtitle">
              {version} • 5 Days • {CLASSES.length} Classes • Backend-defined Learning Periods
            </p>
          </div>

          <div className="tt-actions">
            <div className="tt-status">
              <span className="tt-status-dot" />

              {loading
                ? "Loading timetable..."
                : `${scheduledEntries} backend entries loaded`}
            </div>

            <button
              type="button"
              className="tt-button"
              onClick={() => void loadTimetable()}
              disabled={refreshing}
            >
              <RefreshCw size={16} />
              Refresh
            </button>

            <button
              type="button"
              className="tt-button"
              onClick={() => window.print()}
            >
              <Printer size={16} />
              Print
            </button>
          </div>
        </header>

        {error ? <div className="tt-error">{error}</div> : null}

        <div className="tt-table-wrap">
          <table className="tt-table">
            <thead>
              <tr>
                <th className="tt-day-head">DAY</th>
                <th className="tt-class-head">CLASS</th>

                {COLUMNS.map((column) => (
                  <th
                    key={column.key}
                    className={[
                      "tt-period-head",
                      column.kind === "tea" ? "tt-tea" : "",
                      column.kind === "lunch" ? "tt-lunch" : "",
                      column.kind === "prayers" ? "tt-prayers" : "",
                      column.kind === "activities" ? "tt-activities" : "",
                    ].join(" ")}
                  >
                    <span className="tt-period-label">
                      {column.label}
                    </span>

                    <span className="tt-period-time">
                      {column.time}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {DAYS.map((day) =>
                CLASSES.map((classDefinition, classIndex) => (
                  <tr
                    key={`${day.code}-${classDefinition.label}`}
                  >
                    {classIndex === 0 ? (
                      <th
                        rowSpan={CLASSES.length}
                        className="tt-day"
                      >
                        {day.label}
                      </th>
                    ) : null}

                    <th className="tt-class">
                      {classDefinition.label}
                    </th>

                    {COLUMNS.map((column) => {
                      if (column.kind === "tea") {
                        return (
                          <td
                            key={column.key}
                            className={cellClass(column)}
                          >
                            TEA BREAK
                          </td>
                        );
                      }

                      if (column.kind === "lunch") {
                        return (
                          <td
                            key={column.key}
                            className={cellClass(column)}
                          >
                            LUNCH
                          </td>
                        );
                      }

                      if (column.kind === "prayers") {
                        return (
                          <td
                            key={column.key}
                            className={cellClass(column)}
                          >
                            PRAYERS
                          </td>
                        );
                      }

                      if (column.kind === "activities") {
                        return (
                          <td
                            key={column.key}
                            className={cellClass(column)}
                          >
                            ACTIVITIES
                          </td>
                        );
                      }

                      const period = column.period || 0;

                      const slotEntries = getSlotEntries(
                        day.code,
                        classDefinition,
                        period,
                      );

                      const isMondayAssembly =
                        day.code === "MON" && period === 1;

                      return (
                        <td
                          key={column.key}
                          className={cellClass(column)}
                        >
                          {isMondayAssembly ? (
                            <div className="tt-lesson">
                              <span className="tt-subject">
                                ASSEMBLY
                              </span>
                            </div>
                          ) : slotEntries.length > 0 ? (
                            slotEntries.map((entry) => {
                              const lesson = formatLesson(entry);

                              return (
                                <div
                                  className="tt-lesson"
                                  key={entry.id}
                                >
                                  <span className="tt-subject">
                                    {lesson.code ||
                                      lesson.name ||
                                      "SUBJECT"}
                                  </span>

                                  {lesson.name && lesson.code ? (
                                    <span className="tt-subject-name">
                                      {lesson.name}
                                    </span>
                                  ) : null}

                                  {lesson.elective ? (
                                    <span className="tt-elective">
                                      {lesson.elective}
                                    </span>
                                  ) : null}

                                  {lesson.teacher ? (
                                    <span className="tt-teacher">
                                      {lesson.teacher}
                                    </span>
                                  ) : null}
                                </div>
                              );
                            })
                          ) : (
                            "—"
                          )}
                        </td>
                      );
                    })}
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>

        <footer className="tt-footer">
          <span>Subject • Teacher Code • Elective Option</span>

          <span>✓ {scheduledEntries} backend entries</span>

          <span>All times are local time</span>
        </footer>
      </main>
    </>
  );
}

export default Timetable;
