import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Printer,
  RefreshCw,
} from "lucide-react";

import {
  getSchedulingRuns,
  getSchedulingRunResults,
  type SchedulingRun,
} from "../services/scheduling";
import {
  getInstructionalGroups,
  type InstructionalGroup,
} from "../services/core";

type JsonRecord = Record<string, unknown>;

type TimetableEntry = {
  id?: string;
  day?: string;
  day_display?: string;

  period?: string;
  period_number?: number;
  period_name?: string;
  period_start_time?: string;
  period_end_time?: string;

  teaching_group?: string;
  teaching_group_name?: string;

  instructional_group?: string;
  instructional_group_name?: string;

  teacher?: string;
  teacher_name?: string;
  teacher_code?: string;
  employee_code?: string;

  subject?: string;
  subject_name?: string;
  subject_code?: string;

  lesson_requirement?: string;
  lesson_requirement_name?: string;

  room?: string;
  room_name?: string;

  [key: string]: unknown;
};

type TimetableVersion = {
  id?: string;
  term?: string;
  term_name?: string;
  name?: string;
  version_number?: number;
  is_published?: boolean;
  is_active?: boolean;
  entries_count?: number;
  entries?: TimetableEntry[];
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
};

type SchoolClass = {
  id: string;
  label: string;
};

type TimetableSlot =
  | {
      key: string;
      title: string;
      time: string;
      periodNumber: number | null;
      kind: "lesson";
    }
  | {
      key: string;
      title: string;
      time: string;
      periodNumber: number | null;
      kind: "tea" | "lunch" | "prayer" | "activity";
    };

const DAYS = [
  { code: "MON", label: "Mon" },
  { code: "TUE", label: "Tue" },
  { code: "WED", label: "Wed" },
  { code: "THU", label: "Thur" },
  { code: "FRI", label: "Fri" },
] as const;


const SLOTS: TimetableSlot[] = [
  {
    key: "P1",
    title: "Pd 1",
    time: "8:00–8:40",
    periodNumber: 1,
    kind: "lesson",
  },
  {
    key: "P2",
    title: "Pd 2",
    time: "8:40–9:20",
    periodNumber: 2,
    kind: "lesson",
  },
  {
    key: "P3",
    title: "Pd 3",
    time: "9:20–10:00",
    periodNumber: 3,
    kind: "lesson",
  },
  {
    key: "P4",
    title: "Pd 4",
    time: "10:00–10:40",
    periodNumber: 4,
    kind: "lesson",
  },
  {
    key: "TEA",
    title: "Tea",
    time: "10:40–11:00",
    periodNumber: null,
    kind: "tea",
  },
  {
    key: "P6",
    title: "Pd 6",
    time: "11:00–11:40",
    periodNumber: 6,
    kind: "lesson",
  },
  {
    key: "P7",
    title: "Pd 7",
    time: "11:40–12:20",
    periodNumber: 7,
    kind: "lesson",
  },
  {
    key: "P8",
    title: "Pd 8",
    time: "12:20–1:00",
    periodNumber: 8,
    kind: "lesson",
  },
  {
    key: "LUNCH",
    title: "Lunch",
    time: "1:00–2:00",
    periodNumber: null,
    kind: "lunch",
  },
  {
    key: "P10",
    title: "Pd 10",
    time: "2:00–2:40",
    periodNumber: 10,
    kind: "lesson",
  },
  {
    key: "P11",
    title: "Pd 11",
    time: "2:40–3:20",
    periodNumber: 11,
    kind: "lesson",
  },
  {
    key: "P12",
    title: "Pd 12",
    time: "3:20–4:00",
    periodNumber: 12,
    kind: "lesson",
  },
  {
    key: "PRAYER",
    title: "Prayer",
    time: "4:00–4:30",
    periodNumber: null,
    kind: "prayer",
  },
  {
    key: "ACTIVITY",
    title: "Activity",
    time: "4:30–5:45",
    periodNumber: null,
    kind: "activity",
  },
];

function asRecord(value: unknown): JsonRecord {
  if (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  ) {
    return value as JsonRecord;
  }

  return {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === "string" && value.trim() !== "") {
      return value.trim();
    }
  }

  return null;
}

function firstNumber(...values: unknown[]): number | null {
  for (const value of values) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }

    if (
      typeof value === "string" &&
      value.trim() !== "" &&
      Number.isFinite(Number(value))
    ) {
      return Number(value);
    }
  }

  return null;
}

function getRunDate(run: SchedulingRun): string {
  return (
    run.completed_at ||
    run.started_at ||
    run.created_at ||
    run.updated_at ||
    ""
  );
}

function isCompletedRun(run: SchedulingRun): boolean {
  return String(run.status || "").toUpperCase() === "COMPLETED";
}

function hasTimetable(run: SchedulingRun): boolean {
  if (run.timetable_version) {
    return true;
  }

  const statistics = asRecord(run.statistics);

  const entriesCreated = firstNumber(
    statistics.entries_created,
    statistics.timetable_entries,
    statistics.entries_count,
  );

  return entriesCreated !== null && entriesCreated > 0;
}

function normalizeDay(value: unknown): string {
  const text = String(value ?? "")
    .trim()
    .toUpperCase();

  if (text === "MON" || text === "MONDAY") return "MON";
  if (text === "TUE" || text === "TUESDAY") return "TUE";
  if (text === "WED" || text === "WEDNESDAY") return "WED";
  if (text === "THU" || text === "THUR" || text === "THURSDAY") {
    return "THU";
  }
  if (text === "FRI" || text === "FRIDAY") return "FRI";

  return text;
}


function extractEntriesFromCandidate(
  candidate: unknown,
): TimetableEntry[] {
  const record = asRecord(candidate);

  const entries = asArray(record.entries);

  return entries
    .map((entry) => asRecord(entry) as TimetableEntry)
    .filter((entry) => Object.keys(entry).length > 0);
}

function normalizeVersion(
  candidate: unknown,
  fallback?: JsonRecord,
): TimetableVersion | null {
  const direct = asRecord(candidate);
  const backup = fallback || {};

  const entries =
    extractEntriesFromCandidate(direct).length > 0
      ? extractEntriesFromCandidate(direct)
      : extractEntriesFromCandidate(backup);

  if (entries.length === 0) {
    return null;
  }

  return {
    ...backup,
    ...direct,
    entries,
    entries_count:
      firstNumber(
        direct.entries_count,
        backup.entries_count,
        entries.length,
      ) ?? entries.length,
  };
}

function extractTimetableVersion(
  payload: unknown,
): TimetableVersion | null {
  const root = asRecord(payload);

  const candidates: unknown[] = [
    root.timetable_version,
    root.version,
    root.data,
    root.result,
    root,
  ];

  for (const candidate of candidates) {
    const candidateRecord = asRecord(candidate);

    const directVersion = normalizeVersion(
      candidateRecord,
      root,
    );

    if (directVersion) {
      return directVersion;
    }

    const nestedVersion = normalizeVersion(
      candidateRecord.timetable_version,
      root,
    );

    if (nestedVersion) {
      return nestedVersion;
    }
  }

  return null;
}

function formatGeneratedDate(value: string | null): string {
  if (!value) {
    return "Generated time unavailable";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function entryMatches(
  entry: TimetableEntry,
  dayCode: string,
  schoolClass: SchoolClass,
  periodNumber: number,
): boolean {
  if (normalizeDay(entry.day) !== dayCode) {
    const displayDay = normalizeDay(entry.day_display);

    if (displayDay !== dayCode) {
      return false;
    }
  }

  if (Number(entry.period_number) !== periodNumber) {
    return false;
  }

  return String(entry.instructional_group ?? "") === schoolClass.id;
}

function findEntries(
  entries: TimetableEntry[],
  dayCode: string,
  schoolClass: SchoolClass,
  periodNumber: number,
): TimetableEntry[] {
  return entries.filter((entry) =>
    entryMatches(
      entry,
      dayCode,
      schoolClass,
      periodNumber,
    )
  );
}

function formatEntry(entry: TimetableEntry) {
  const subjectCode = firstString(
    entry.subject_code,
    asRecord(entry.subject).code,
  );

  const subjectName = firstString(
    entry.subject_name,
    asRecord(entry.subject).name,
  );

  const teacherCode = firstString(
    entry.teacher_code,
    entry.employee_code,
  );

  const teacherName = firstString(
    entry.teacher_name,
  );

  const lessonName = firstString(
    entry.lesson_requirement_name,
  );

  const title =
    subjectCode ||
    subjectName ||
    lessonName ||
    "LESSON";

  const subtitle =
    teacherCode ||
    teacherName ||
    "";

  return {
    title,
    subtitle,
    subject: subjectName || subjectCode || lessonName || "",
    teacher: teacherName || teacherCode || "",
  };
}

function activityLabel(dayCode: string): string {
  switch (dayCode) {
    case "MON":
      return "MON ACTIVITY";
    case "TUE":
      return "TUE ACTIVITY";
    case "WED":
      return "WED ACTIVITY";
    case "THU":
      return "THUR ACTIVITY";
    case "FRI":
      return "FRI ACTIVITY";
    default:
      return "ACTIVITY";
  }
}

function Timetable() {
  const [run, setRun] = useState<SchedulingRun | null>(null);
  const [version, setVersion] = useState<TimetableVersion | null>(null);
  const [schoolClasses, setSchoolClasses] = useState<SchoolClass[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadTimetable = useCallback(async () => {
    setError("");

    try {
      const [runs, instructionalGroups] = await Promise.all([
        getSchedulingRuns(),
        getInstructionalGroups(),
      ]);

      setSchoolClasses(
        instructionalGroups
          .filter((group: InstructionalGroup) => group.is_active)
          .map((group: InstructionalGroup) => ({
            id: group.id,
            label: group.name,
          })),
      );

      const completedRuns = Array.isArray(runs)
        ? runs
            .filter(isCompletedRun)
            .filter(hasTimetable)
            .sort((a, b) => {
              const aTime = new Date(
                getRunDate(a),
              ).getTime();

              const bTime = new Date(
                getRunDate(b),
              ).getTime();

              return bTime - aTime;
            })
        : [];

      const latestRun = completedRuns[0];

      if (!latestRun) {
        setRun(null);
        setVersion(null);
        return;
      }

      const resultsPayload =
        await getSchedulingRunResults(
          String(latestRun.id),
        );

      const resolvedVersion =
        extractTimetableVersion(resultsPayload);

      if (!resolvedVersion) {
        throw new Error(
          "The latest completed scheduling run did not return its timetable entries.",
        );
      }

      setRun(latestRun);
      setVersion(resolvedVersion);
    } catch (requestError: unknown) {
      const record = asRecord(requestError);
      const response = asRecord(record.response);
      const responseData = asRecord(response.data);

      const message =
        firstString(
          responseData.detail,
          responseData.error,
          record.message,
        ) ||
        "Unable to load the generated timetable. Make sure the Django API is running.";

      setError(message);
      setRun(null);
      setVersion(null);
      setSchoolClasses([]);
    }
  }, []);

  useEffect(() => {
    let mounted = true;

    async function initialLoad() {
      setLoading(true);

      try {
        await loadTimetable();
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void initialLoad();

    return () => {
      mounted = false;
    };
  }, [loadTimetable]);

  async function refresh() {
    setRefreshing(true);

    try {
      await loadTimetable();
    } finally {
      setRefreshing(false);
    }
  }

  const entries = useMemo(
    () => version?.entries ?? [],
    [version],
  );

  const versionName =
    firstString(
      version?.name,
      "Generated Timetable",
    ) || "Generated Timetable";

  const versionNumber =
    firstNumber(version?.version_number);

  const termName =
    firstString(
      version?.term_name,
      run?.term_name,
      "Term 1",
    ) || "Term 1";

  const generatedAt = formatGeneratedDate(
    firstString(
      version?.created_at,
      run ? getRunDate(run) : "",
    ),
  );

  const scheduledEntries =
    firstNumber(
      version?.entries_count,
      entries.length,
    ) ?? entries.length;

  return (
    <>
      <style>{`
        .whole-school-page {
          min-height: 100%;
          box-sizing: border-box;
          background: #f7f9fc;
          padding: 14px 18px 18px;
          color: #172033;
        }

        .whole-school-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 18px;
          margin-bottom: 8px;
        }

        .whole-school-title {
          margin: 0;
          font-size: 18px;
          line-height: 1.1;
          font-weight: 800;
          letter-spacing: .02em;
          color: #14213d;
        }

        .whole-school-subtitle {
          margin: 3px 0 0;
          font-size: 9px;
          font-weight: 700;
          letter-spacing: .11em;
          color: #5d6b82;
          text-transform: uppercase;
        }

        .whole-school-actions {
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .whole-school-button {
          border: 1px solid #cbd5e1;
          background: #ffffff;
          color: #24324a;
          border-radius: 5px;
          padding: 5px 9px;
          display: inline-flex;
          align-items: center;
          gap: 5px;
          font-size: 10px;
          font-weight: 700;
          cursor: pointer;
        }

        .whole-school-button:hover {
          background: #f1f5f9;
        }

        .whole-school-button:disabled {
          opacity: .6;
          cursor: wait;
        }

        .whole-school-meta {
          display: flex;
          justify-content: flex-end;
          align-items: center;
          gap: 5px;
          margin-bottom: 7px;
          flex-wrap: wrap;
        }

        .whole-school-badge {
          border: 1px solid #d7deea;
          background: #ffffff;
          border-radius: 4px;
          padding: 4px 8px;
          font-size: 9px;
          color: #334155;
          white-space: nowrap;
        }

        .whole-school-table-wrap {
          width: 100%;
          overflow-x: auto;
          overflow-y: hidden;
          background: #ffffff;
          border: 1px solid #b9c8dc;
        }

        .whole-school-table {
          width: 100%;
          min-width: 1180px;
          border-collapse: collapse;
          table-layout: fixed;
          font-size: 8px;
        }

        .whole-school-table th,
        .whole-school-table td {
          border: 1px solid #bfd0e4;
          padding: 0;
          text-align: center;
          vertical-align: middle;
        }

        .whole-school-table thead th {
          height: 42px;
          background: #e8eef6;
          color: #1e3555;
          font-weight: 800;
        }

        .whole-school-table .day-head {
          width: 48px;
        }

        .whole-school-table .class-head {
          width: 72px;
        }

        .whole-school-table .slot-head {
          width: 78px;
        }

        .whole-school-table .head-title {
          display: block;
          font-size: 9px;
          line-height: 1.1;
        }

        .whole-school-table .head-time {
          display: block;
          margin-top: 2px;
          font-size: 6px;
          font-weight: 600;
          color: #687b94;
          line-height: 1;
        }

        .whole-school-table tbody tr {
          height: 43px;
        }

        .whole-school-table .day-cell {
          background: #f4f7fb;
          font-weight: 800;
          font-size: 9px;
          color: #1e3555;
          width: 48px;
        }

        .whole-school-table .class-cell {
          background: #f8fafc;
          text-align: left;
          padding-left: 7px;
          font-weight: 800;
          color: #233752;
          white-space: nowrap;
        }

        .whole-school-table .lesson-cell {
          background: #ffffff;
          min-width: 78px;
        }

        .whole-school-table .break-cell {
          background: #f2f5f9;
        }

        .whole-school-table .special-cell {
          background: #f5f7fa;
        }

        .whole-school-table .assembly-cell {
          background: #f8fafc;
        }

        .whole-school-table .empty-mark {
          color: #a9b7c9;
          font-size: 10px;
        }

        .cell-subject {
          display: block;
          color: #17345b;
          font-size: 8px;
          font-weight: 800;
          line-height: 1.15;
          word-break: break-word;
        }

        .cell-teacher {
          display: block;
          margin-top: 2px;
          color: #70819a;
          font-size: 6px;
          font-weight: 700;
          line-height: 1;
        }

        .special-title {
          display: block;
          color: #203858;
          font-size: 7px;
          font-weight: 900;
          letter-spacing: .04em;
        }

        .special-time {
          display: block;
          margin-top: 2px;
          color: #71839a;
          font-size: 6px;
        }

        .assembly-title {
          display: inline-block;
          border: 1px solid #c5d2e2;
          border-radius: 3px;
          padding: 5px 4px;
          color: #23466e;
          background: #f6f9fc;
          font-size: 7px;
          font-weight: 900;
        }

        .whole-school-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 5px;
          font-size: 8px;
          color: #718096;
        }

        .whole-school-error {
          border: 1px solid #e5b8b8;
          background: #fff5f5;
          color: #9b2c2c;
          padding: 10px 12px;
          margin-bottom: 10px;
          font-size: 11px;
        }

        .whole-school-loading {
          padding: 35px;
          text-align: center;
          color: #64748b;
          font-size: 12px;
          background: #ffffff;
          border: 1px solid #cbd5e1;
        }

        .whole-school-loading-inner {
          display: inline-flex;
          align-items: center;
          gap: 7px;
        }

        .whole-school-spin {
          animation: whole-school-spin 1s linear infinite;
        }

        @keyframes whole-school-spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }

        @media print {
          @page {
            size: A4 landscape;
            margin: 5mm;
          }

          .whole-school-page {
            padding: 0;
            background: #ffffff;
          }

          .whole-school-actions {
            display: none !important;
          }

          .whole-school-meta {
            margin-top: 4px;
          }

          .whole-school-table-wrap {
            overflow: visible;
            border: 1px solid #9aaabd;
          }

          .whole-school-table {
            min-width: 0;
            font-size: 7px;
          }

          .whole-school-table thead th {
            height: 35px;
          }

          .whole-school-table tbody tr {
            height: 38px;
          }
        }
      `}</style>

      <main className="whole-school-page">
        <header className="whole-school-header">
          <div>
            <h1 className="whole-school-title">
              QUEEN OF APOSTLE SEMINARY
            </h1>

            <p className="whole-school-subtitle">
              WHOLE-SCHOOL TIMETABLE
            </p>
          </div>

          <div className="whole-school-actions">
            <button
              type="button"
              className="whole-school-button"
              onClick={() => window.print()}
              title="Print timetable"
              aria-label="Print timetable"
            >
              <Printer size={12} />
              Print
            </button>

            <button
              type="button"
              className="whole-school-button"
              onClick={() => void refresh()}
              disabled={refreshing}
              title="Refresh timetable"
              aria-label="Refresh timetable"
            >
              <RefreshCw
                size={12}
                className={
                  refreshing
                    ? "whole-school-spin"
                    : ""
                }
              />
              Refresh
            </button>
          </div>
        </header>

        <div className="whole-school-meta">
          <span className="whole-school-badge">
            {termName}
          </span>

          <span className="whole-school-badge">
            {versionName}
          </span>

          <span className="whole-school-badge">
            Version {versionNumber ?? "—"}
          </span>

          <span className="whole-school-badge">
            {generatedAt}
          </span>
        </div>

        {error ? (
          <div className="whole-school-error">
            {error}
          </div>
        ) : null}

        {loading ? (
          <div className="whole-school-loading">
            <span className="whole-school-loading-inner">
              <RefreshCw
                size={16}
                className="whole-school-spin"
              />
              Loading generated timetable...
            </span>
          </div>
        ) : !version ? (
          <div className="whole-school-loading">
            No completed timetable is currently available.
          </div>
        ) : schoolClasses.length === 0 ? (
          <div className="whole-school-loading">
            No active instructional groups are configured.
          </div>
        ) : (
          <>
            <div className="whole-school-table-wrap">
              <table className="whole-school-table">
                <thead>
                  <tr>
                    <th className="day-head">
                      DAYS
                    </th>

                    <th className="class-head">
                      CLASS
                    </th>

                    {SLOTS.map((slot) => (
                      <th
                        key={slot.key}
                        className="slot-head"
                      >
                        <span className="head-title">
                          {slot.title}
                        </span>

                        <span className="head-time">
                          {slot.time}
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {DAYS.map((day) =>
                    schoolClasses.map(
                      (schoolClass, classIndex) => (
                        <tr
                          key={`${day.code}-${schoolClass.id}`}
                        >
                          {classIndex === 0 ? (
                            <td
                              className="day-cell"
                              rowSpan={schoolClasses.length}
                            >
                              {day.label}
                            </td>
                          ) : null}

                          <td className="class-cell">
                            {schoolClass.label}
                          </td>

                          {SLOTS.map((slot) => {
                            /*
                             * Monday Pd 1 is a permanent
                             * whole-school Assembly slot.
                             */
                            if (
                              day.code === "MON" &&
                              slot.periodNumber === 1
                            ) {
                              return (
                                <td
                                  key={slot.key}
                                  className="lesson-cell assembly-cell"
                                >
                                  <span className="assembly-title">
                                    ASSEMBLY
                                  </span>
                                </td>
                              );
                            }

                            if (
                              slot.kind === "tea"
                            ) {
                              return (
                                <td
                                  key={slot.key}
                                  className="break-cell"
                                >
                                  <span className="special-title">
                                    TEA
                                  </span>

                                  <span className="special-time">
                                    10:40–11:00
                                  </span>
                                </td>
                              );
                            }

                            if (
                              slot.kind === "lunch"
                            ) {
                              return (
                                <td
                                  key={slot.key}
                                  className="break-cell"
                                >
                                  <span className="special-title">
                                    LUNCH
                                  </span>

                                  <span className="special-time">
                                    1:00–2:00
                                  </span>
                                </td>
                              );
                            }

                            if (
                              slot.kind === "prayer"
                            ) {
                              return (
                                <td
                                  key={slot.key}
                                  className="special-cell"
                                >
                                  <span className="special-title">
                                    PRAYER
                                  </span>

                                  <span className="special-time">
                                    4:00–4:30
                                  </span>
                                </td>
                              );
                            }

                            if (
                              slot.kind === "activity"
                            ) {
                              return (
                                <td
                                  key={slot.key}
                                  className="special-cell"
                                >
                                  <span className="special-title">
                                    {activityLabel(
                                      day.code,
                                    )}
                                  </span>

                                  <span className="special-time">
                                    4:30–5:45
                                  </span>
                                </td>
                              );
                            }

                            const slotEntries =


                              slot.periodNumber !== null


                                ? findEntries(


                                    entries,


                                    day.code,


                                    schoolClass,


                                    slot.periodNumber,


                                  )


                                : [];



                            if (slotEntries.length === 0) {


                              return (


                                <td


                                  key={slot.key}


                                  className="lesson-cell"


                                >


                                  <span className="empty-mark">


                                    —


                                  </span>


                                </td>


                              );


                            }



                            const formattedEntries =


                              slotEntries.map((entry) => formatEntry(entry));



                            return (


                              <td


                                key={slot.key}


                                className="lesson-cell"


                                title={formattedEntries


                                  .map((formatted) =>


                                    [formatted.subject, formatted.teacher]


                                      .filter(Boolean)


                                      .join(" • ")


                                  )


                                  .filter(Boolean)


                                  .join(" | ")}


                              >


                                {formattedEntries.map((formatted, index) => (


                                  <div


                                    key={[


                                      formatted.subject,


                                      formatted.teacher,


                                      index,


                                    ].join("-")}


                                  >


                                    <span className="cell-subject">


                                      {formatted.title}


                                    </span>



                                    {formatted.subtitle ? (


                                      <span className="cell-teacher">


                                        {formatted.subtitle}


                                      </span>


                                    ) : null}


                                  </div>


                                ))}


                              </td>


                            );
                          })}
                        </tr>
                      ),
                    ),
                  )}
                </tbody>
              </table>
            </div>

            <footer className="whole-school-footer">
              <span>
                Subject • Teacher No.
              </span>

              <span>
                ✓ {scheduledEntries} scheduled entries
              </span>
            </footer>
          </>
        )}
      </main>
    </>
  );
}

export default Timetable;
