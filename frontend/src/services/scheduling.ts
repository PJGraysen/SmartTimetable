import http from "./http";

export type AcademicTerm = {
  id: string;
  name: string;
  academic_year: string;
  academic_year_name: string;
  number: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
};

export type SchedulingRun = {
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

export async function getSchedulingRuns() {
  const response = await http.get<SchedulingRun[]>("/scheduling/runs/");
  return response.data;
}

export async function getSchedulingRun(id: string) {
  const response = await http.get<SchedulingRun>(`/scheduling/runs/${id}/`);
  return response.data;
}

export async function executeSchedulingRun(
  id: string,
  payload: {
    version_name?: string;
    version_number?: number;
  } = {},
) {
  const response = await http.post<SchedulingRun>(
    `/scheduling/runs/${id}/execute/`,
    payload,
  );
  return response.data;
}

export async function getSchedulingRunResults(id: string) {
  const response = await http.get(`/scheduling/runs/${id}/results/`);
  return response.data;
}

export type CreateSchedulingRunPayload = {
  term: string;
  version_name?: string;
  version_number?: number;
};

export async function createSchedulingRun(
  payload: CreateSchedulingRunPayload,
) {
  const response = await http.post<SchedulingRun>(
    "/scheduling/runs/",
    payload,
  );
  return response.data;
}
