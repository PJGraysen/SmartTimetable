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

export async function getAcademicTerms() {
  const response = await http.get<AcademicTerm[]>("/core/terms/");
  return response.data;
}
