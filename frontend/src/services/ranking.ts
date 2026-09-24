import http from "./http";

export type RankingRule = {
  id: string;
  name: string;
  description: string;
  method: "TOTAL" | "MEAN_PCT" | "MEAN_POINTS" | "SUBJECT_COMBO";
  tie_policy: "COMPETITION" | "DENSE" | "ORDINAL";
  subject_codes: string[];
  min_subjects: number;
  is_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
};

export type RankingEntry = {
  student_id: string;
  admission_number: string;
  name: string;
  score: number;
  total: number;
  mean_pct: number;
  mean_points: number;
  subjects_count: number;
  grade: string;
  rank: number;
  percentile: number;
};

export type RankingResult = {
  rule: {
    id: string;
    name: string;
    method: string;
    tie_policy: string;
    subject_codes: string[];
    min_subjects: number;
    version: number;
  };
  run_id: string | null;
  scope_type: string;
  scope_label: string;
  assessment_id: string | null;
  count: number;
  entries: RankingEntry[];
};

export async function listRankingRules(): Promise<RankingRule[]> {
  const { data } = await http.get<RankingRule[]>("/academics/ranking-rules/");
  return data;
}

export async function createRankingRule(payload: Partial<RankingRule>): Promise<RankingRule> {
  const { data } = await http.post<RankingRule>("/academics/ranking-rules/", payload);
  return data;
}

export async function updateRankingRule(id: string, patch: Partial<RankingRule>): Promise<RankingRule> {
  const { data } = await http.patch<RankingRule>(`/academics/ranking-rules/${id}/`, patch);
  return data;
}

export async function deleteRankingRule(id: string): Promise<void> {
  await http.delete(`/academics/ranking-rules/${id}/`);
}

export async function previewRanking(params: {
  rule: string;
  assessment?: string;
  teaching_group?: string;
  persist?: boolean;
}): Promise<RankingResult> {
  const qs = new URLSearchParams({ rule: params.rule });
  if (params.assessment) qs.set("assessment", params.assessment);
  if (params.teaching_group) qs.set("teaching_group", params.teaching_group);
  if (params.persist) qs.set("persist", "1");
  const { data } = await http.get<RankingResult>(`/academics/ranking/preview/?${qs.toString()}`);
  return data;
}