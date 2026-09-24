import http from "./http";

export type GradingBand = {
  id: string;
  min_score: string;
  max_score: string;
  grade: string;
  points: string;
  descriptor: string;
};

export type GradingScheme = {
  id: string;
  name: string;
  curriculum: string;
  effective_from: string | null;
  is_active: boolean;
  bands: GradingBand[];
};

export async function listSchemes(): Promise<GradingScheme[]> {
  const { data } = await http.get<GradingScheme[]>("/academics/grading-schemes/");
  return data;
}

export async function createScheme(payload: Partial<GradingScheme>): Promise<GradingScheme> {
  const { data } = await http.post<GradingScheme>("/academics/grading-schemes/", payload);
  return data;
}

export async function updateScheme(id: string, patch: Partial<GradingScheme>): Promise<GradingScheme> {
  const { data } = await http.patch<GradingScheme>(`/academics/grading-schemes/${id}/`, patch);
  return data;
}

export async function createBand(payload: Partial<GradingBand> & { scheme: string }): Promise<GradingBand> {
  const { data } = await http.post<GradingBand>("/academics/grading-bands/", payload);
  return data;
}

export async function updateBand(id: string, patch: Partial<GradingBand>): Promise<GradingBand> {
  const { data } = await http.patch<GradingBand>(`/academics/grading-bands/${id}/`, patch);
  return data;
}

export async function deleteBand(id: string): Promise<void> {
  await http.delete(`/academics/grading-bands/${id}/`);
}