import http from "./http";


// ---------------------------------------------------------------------
// Scoped regeneration support (1b)
// ---------------------------------------------------------------------
export type MasterScope  = { kind: "master";  id: null;   label: string };
export type GradeScope   = { kind: "grade";   id: string; label: string; groups: string[] };
export type SubjectScope = { kind: "subject"; id: string; label: string; code: string };
export type ScopePick = MasterScope | GradeScope | SubjectScope;

export type ScopeList = {
  term: { id: string; name: string };
  master: MasterScope;
  grades: GradeScope[];
  subjects: SubjectScope[];
};

export async function getSchedulingScopes(termId?: string): Promise<ScopeList> {
  const { data } = await http.get<ScopeList>("/scheduling/scopes/", {
    params: termId ? { term: termId } : undefined,
  });
  return data;
}

export type ExecuteRunOpts = {
  version_name?: string;
  version_number?: number;
  scope_kind?: string | null;
  scope_id?: string | null;
};

export type SchedulingRunStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";

export type SchedulingRun = {
  id: string;
  term: string;
  term_name?: string;
  status: SchedulingRunStatus;
  status_display?: string;
  solver_status?: string;
  solver_status_display?: string;
  started_at?: string | null;
  completed_at?: string | null;
  objective_value?: string | null;
  error_message?: string;
  statistics?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  approved_at?: string | null;
  approved_by?: number | null;
  approval_note?: string;
};

export type ScheduleRunSummary = {
  id: string;
  status: SchedulingRunStatus;
  status_display: string;
  term_name: string;
  created_at: string | null;
  completed_at: string | null;
  approved_at: string | null;
  approved_by: string | null;
  version_name: string | null;
  version_number: number | null;
  error_message: string;
};

export type SchedulingDashboard = {
  active_term: { id: string; name: string; academic_year_name: string; is_active: boolean } | null;
  terms: Array<{ id: string; name: string; academic_year_name: string; is_active: boolean }>;
  active_version: {
    id: string;
    name: string;
    version_number: number;
    created_at: string;
    is_published: boolean;
    entries_count: number;
    days: number;
    classes: number;
  } | null;
  last_successful_sync: string | null;
  recent_runs: ScheduleRunSummary[];
  failed_runs: ScheduleRunSummary[];
  counts: { total: number; completed: number; failed: number; cancelled: number; approved: number };
};

export async function fetchSchedulingDashboard(): Promise<SchedulingDashboard> {
  const { data } = await http.get<SchedulingDashboard>("/scheduling/dashboard/");
  return data;
}

export async function fetchSchedulingRuns(): Promise<SchedulingRun[]> {
  const { data } = await http.get<SchedulingRun[]>("/scheduling/runs/", {
    params: { _t: Date.now() },
  });
  return Array.isArray(data) ? data : ((data as { results?: SchedulingRun[] }).results ?? []);
}

export async function fetchSchedulingRun(
  id: string,
  opts: { silent?: boolean } = {},
): Promise<SchedulingRun> {
  const { data } = await http.get<SchedulingRun>(`/scheduling/runs/${id}/`, {
    params: { _t: Date.now() },
    // Polling retries on transient failure; the loop itself decides when
    // a failure is fatal. Do not spam the user with toasts each tick.
    ...(opts.silent ? ({ skipGlobalError: true } as any) : {}),
  });
  return data;
}

export async function createSchedulingRun(termId: string): Promise<SchedulingRun> {
  const { data } = await http.post<SchedulingRun>("/scheduling/runs/", { term: termId });
  return data;
}

export async function executeSchedulingRun(
  id: string,
  opts: ExecuteRunOpts = {},
): Promise<SchedulingRun> {
  const body: Record<string, unknown> = {
    version_name: opts.version_name ?? "Generated Timetable",
    version_number: opts.version_number ?? 1,
  };
  if (opts.scope_kind) body.scope_kind = opts.scope_kind;
  if (opts.scope_id) body.scope_id = opts.scope_id;
  const { data } = await http.post<SchedulingRun>(
    `/scheduling/runs/${id}/execute/`,
    body,
  );
  return data;
}

export async function fetchSchedulingRunResult(id: string): Promise<unknown> {
  const { data } = await http.get(`/scheduling/runs/${id}/results/`, {
    params: { _t: Date.now() },
  });
  return data;
}

export async function approveSchedulingRun(id: string, note = ""): Promise<{ ok: boolean }> {
  const { data } = await http.post<{ ok: boolean }>(`/scheduling/runs/${id}/approve/`, { note });
  return data;
}

export async function unapproveSchedulingRun(id: string): Promise<{ ok: boolean }> {
  const { data } = await http.post<{ ok: boolean }>(`/scheduling/runs/${id}/unapprove/`, {});
  return data;
}

// ---------------------------------------------------------------------
// Backwards-compatibility aliases (Timetable.tsx uses these names)
// ---------------------------------------------------------------------
export const getSchedulingRuns = fetchSchedulingRuns;
export const getSchedulingRunResults = fetchSchedulingRunResult;
export const getSchedulingRun = fetchSchedulingRun;

export async function resolveValidation(runId: string, validationId: string, resolved: boolean): Promise<{ ok: boolean; is_resolved: boolean }> {
  const { data } = await http.post(`/scheduling/runs/${runId}/validation/${validationId}/resolve/`, { resolved });
  return data;
}

// ------------------------------------------------------------
// Async generation helpers
// ------------------------------------------------------------

export type TerminalStatus = "COMPLETED" | "FAILED" | "CANCELLED";

export interface PollOptions {
  intervalMs?: number;
  timeoutMs?: number;
  onTick?: (run: SchedulingRun, elapsedMs: number) => void;
}

/**
 * Poll /scheduling/runs/<id>/ until the run reaches a terminal status.
 * Returns the final run object.
 */
export async function pollRunUntilDone(
  id: string,
  opts: PollOptions = {},
): Promise<SchedulingRun> {
  const interval = opts.intervalMs ?? 3000;
  const timeout = opts.timeoutMs ?? 45 * 60 * 1000; // 45 min hard cap
  const started = Date.now();

  for (;;) {
    let run: SchedulingRun;
    try {
      run = await fetchSchedulingRun(id, { silent: true });
    } catch (err) {
      // Transient poll failure — wait and retry. The loop's timeout is
      // the real kill switch; do not surface this to the user.
      await new Promise((r) => setTimeout(r, interval));
      if (Date.now() - started > timeout) {
        throw new Error("Run did not complete within " + Math.round(timeout / 60000) + " minutes.");
      }
      continue;
    }
    opts.onTick?.(run, Date.now() - started);

    if (
      run.status === "COMPLETED" ||
      run.status === "FAILED" ||
      run.status === "CANCELLED"
    ) {
      return run;
    }

    if (Date.now() - started > timeout) {
      throw new Error("Run did not complete within " + Math.round(timeout / 60000) + " minutes.");
    }

    await new Promise((r) => setTimeout(r, interval));
  }
}

export async function discardSchedulingRun(id: string): Promise<{ ok: boolean }> {
  const { data } = await http.post<{ ok: boolean }>(
    `/scheduling/runs/${id}/discard/`,
    {},
  );
  return data;
}


// --- Requirements report for a run ---
export type RunReportSubject = {
  subject: string;
  required: number;
  placed: number;
  status: "OK" | "MISSING" | "EXTRA";
};

export type RunReportClass = {
  class_name: string;
  required_total: number;
  placed_total: number;
  subjects: RunReportSubject[];
};

export type RunReport = {
  run_id: string;
  version_id: string;
  version_number: number;
  version_name: string;
  classes: RunReportClass[];
};

export async function getSchedulingRunReport(id: string): Promise<RunReport> {
  const { data } = await http.get<RunReport>(`/scheduling/runs/${id}/report/`);
  return data;
}
