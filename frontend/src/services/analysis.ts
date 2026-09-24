import http from "./http";

export type Assessment = {
  id: string;
  name: string;
  type: string;
  date: string;
  max_mark: number;
  status: string;
};

export type SubjectRow = {
  subject_id: string;
  subject_code: string;
  subject_name: string;
  candidates: number;
  mean: number;
  median: number;
  std_dev: number;
  highest: number;
  lowest: number;
  pass_count: number;
  pass_rate: number;
  grade_counts: Record<string, number>;
};

export type RankingRow = {
  student_id: string;
  admission_number: string;
  name: string;
  mean: number;
  grade: string;
  rank: number;
};

export type Insight = {
  severity: "positive" | "info" | "warning" | "danger";
  title: string;
  detail: string;
};

export type TrendPoint = {
  assessment_id: string;
  assessment_name: string;
  date: string;
  mean: number;
  pass_rate: number;
};

export type Dashboard = {
  assessment: Assessment;
  students: number;
  results: number;
  overall_mean: number;
  overall_median: number;
  overall_std_dev: number;
  pass_rate: number;
  highest: number;
  lowest: number;
  subject_rows: SubjectRow[];
  grade_distribution: Record<string, number>;
  ranking: RankingRow[];
  insights: Insight[];
  trend: TrendPoint[];
};

export async function listAssessments(): Promise<Assessment[]> {
  const { data } = await http.get<Assessment[]>("/academics/analysis/assessments/");
  return data;
}

export async function fetchDashboard(assessmentId?: string): Promise<Dashboard> {
  const url = assessmentId
    ? `/academics/analysis/dashboard/?assessment=${assessmentId}`
    : "/academics/analysis/dashboard/";
  const { data } = await http.get<Dashboard>(url);
  return data;
}

export type StudentAnalysis = {
  student: { id: string; admission_number: string; name: string; status: string };
  subjects: Array<{
    subject_code: string;
    subject_name: string;
    mean: number;
    trend: "improving" | "declining" | "stable";
    marks: Array<{ assessment: string; date: string; pct: number; grade: string }>;
  }>;
};

export async function fetchStudentAnalysis(id: string): Promise<StudentAnalysis> {
  const { data } = await http.get<StudentAnalysis>(`/academics/analysis/student/${id}/`);
  return data;
}


// ---------------------------------------------------------------------
// Individual student deep analysis
// ---------------------------------------------------------------------
export type StudentDeepSummary = {
  subjects_count: number;
  assessments_count: number;
  total_marks: number;
  total_max: number;
  overall_mean: number;
  overall_median: number;
  overall_std_dev: number;
  overall_grade: string;
  overall_points: number;
  rank: number | null;
  class_size: number | null;
  percentile: number | null;
  class_mean: number | null;
  vs_class_mean: number | null;
};

export type StudentDeepSubjectRow = {
  subject_id: string;
  subject_code: string;
  subject_name: string;
  mean: number;
  median: number;
  std_dev: number;
  highest: number;
  lowest: number;
  assessments_count: number;
  grade: string;
  points: number;
  descriptor: string;
  trend: "improving" | "declining" | "stable";
  delta: number;
  class_mean: number | null;
  vs_class: number | null;
  marks: Array<{
    assessment_id: string;
    assessment_name: string;
    date: string;
    raw_mark: number;
    max_mark: number;
    pct: number;
    grade: string;
  }>;
};

export type StudentDeepHistory = {
  assessment_id: string;
  assessment_name: string;
  date: string;
  total: number;
  total_max: number;
  mean_pct: number;
  grade: string;
  subjects_sat: number;
};

export type StudentDeepAnalysis = {
  student: {
    id: string;
    admission_number: string;
    first_name: string;
    middle_name: string;
    last_name: string;
    name: string;
    status: string;
    gender: string;
  };
  teaching_group: { id: string; name: string } | null;
  summary: StudentDeepSummary;
  subject_rows: StudentDeepSubjectRow[];
  history: StudentDeepHistory[];
  grade_distribution: Record<string, number>;
  strengths: string[];
  weaknesses: string[];
  insights: Insight[];
};

export async function fetchStudentDeepAnalysis(id: string): Promise<StudentDeepAnalysis> {
  const { data } = await http.get<StudentDeepAnalysis>(`/academics/analysis/student-deep/${id}/`);
  return data;
}



// ---------------------------------------------------------------------
// Class / stream comparison
// ---------------------------------------------------------------------
export type SubjectMeanDetail = {
  code: string;
  name: string;
  mean: number;
  median: number;
  std_dev: number;
  highest: number;
  lowest: number;
  count: number;
  grade_counts: Record<string, number>;
};

export type StudentRef = {
  name: string;
  admission_number: string;
  mean: number;
};

export type ClassRow = {
  group_id: string;
  group_name: string;
  students: number;
  overall_mean: number;
  overall_median: number;
  overall_std_dev: number;
  overall_pass_rate: number;
  best_student: StudentRef | null;
  worst_student: StudentRef | null;
  subject_means: Record<string, number>;
  subject_full: SubjectMeanDetail[];
  leading_subject: { code: string; name: string; mean: number } | null;
  trailing_subject: { code: string; name: string; mean: number } | null;
  rank: number;
};

export type LeaderboardEntry = {
  group_id: string;
  group_name: string;
  best: { name: string; admission_number: string; pct: number } | null;
  worst: { name: string; admission_number: string; pct: number } | null;
  most_improved: { name: string; admission_number: string; delta: number } | null;
  most_declined: { name: string; admission_number: string; delta: number } | null;
};

export type OverallEntry = {
  student_id: string;
  name: string;
  admission_number: string;
  mean: number;
  subjects_count: number;
};
export type OverallImproved = {
  student_id: string;
  name: string;
  admission_number: string;
  delta: number;
};
export type OverallLeaderboard = {
  best: OverallEntry;
  worst: OverallEntry;
  most_improved: OverallImproved | null;
  most_declined: OverallImproved | null;
  count: number;
} | null;
export type ClassOverallLeaderboard = {
  group_id: string;
  group_name: string;
  best: OverallEntry | null;
  worst: OverallEntry | null;
  most_improved: OverallImproved | null;
  most_declined: OverallImproved | null;
  count: number;
};
export type Leaderboards = {
  per_subject: Array<{
    subject_code: string;
    subject_name: string;
    by_class: LeaderboardEntry[];
  }>;
};

export type SubjectGap = {
  subject_code: string;
  best_class: string;
  best_mean: number;
  worst_class: string;
  worst_mean: number;
  gap: number;
};

export type ClassComparison = {
  assessment: Assessment;
  classes: ClassRow[];
  subjects: string[];
  subject_gaps: SubjectGap[];
  insights: Insight[];
};

export async function fetchClassComparison(assessmentId?: string): Promise<ClassComparison> {
  const url = assessmentId
    ? `/academics/analysis/classes/?assessment=${assessmentId}`
    : "/academics/analysis/classes/";
  const { data } = await http.get<ClassComparison>(url);
  return data;
}



export type BulkReportForms = {
  class_name: string | null;
  count: number;
  students: Array<Record<string, unknown>>;
};

export async function fetchBulkReportForms(teachingGroupId: string): Promise<BulkReportForms> {
  const { data } = await http.get<BulkReportForms>(
    `/academics/analysis/report-form-bulk/?teaching_group=${teachingGroupId}`,
  );
  return data;
}

export async function listTeachingGroups(): Promise<Array<{ id: string; name: string }>> {
  const { data } = await http.get<Array<{ id: string; name: string }>>("/academics/teaching-groups/");
  return data;
}



// ---------------------------------------------------------------------
// Stream summary (class + per-student + per-subject printable report)
// ---------------------------------------------------------------------
export type StreamStudentSummary = {
  id: string;
  admission_number: string;
  name: string;
  mean: number;
  std: number;
  grade: string;
  rank: number;
  subjects_count: number;
  strengths: string[];
  weaknesses: string[];
  subjects: Array<{
    code: string;
    name: string;
    pct: number;
    grade: string;
    class_mean: number | null;
    vs_class: number | null;
  }>;
  radar: Array<{ subject: string; student: number; class: number }>;
  trend: "improving" | "declining" | "stable";
  delta: number;
};

export type StreamSubjectSummary = {
  code: string;
  name: string;
  candidates: number;
  mean: number;
  median: number;
  std_dev: number;
  highest: number;
  lowest: number;
  pass_count: number;
  pass_rate: number;
  top_student: { id: string; name: string; admission_number: string; pct: number } | null;
  weakest_student: { id: string; name: string; admission_number: string; pct: number } | null;
  most_improved: { id: string; name: string; admission_number: string; delta: number } | null;
  most_declined: { id: string; name: string; admission_number: string; delta: number } | null;
  most_stable: { id: string; name: string; admission_number: string; std: number } | null;
};

export type StreamSummary = {
  assessment: Assessment;
  stream: { id: string; name: string } | null;
  class_stats: {
    mean: number; median: number; std_dev: number;
    highest: number; lowest: number; pass_rate: number;
    count: number; student_count: number;
  } | null;
  students: StreamStudentSummary[];
  subjects: StreamSubjectSummary[];
  leaderboards: {
    best_overall: StreamStudentSummary[];
    most_improved: StreamStudentSummary[];
    most_declined: StreamStudentSummary[];
    most_consistent: StreamStudentSummary[];
    best_per_subject: Array<{
      subject: string;
      subject_name: string;
      student: { id: string; name: string; admission_number: string; pct: number } | null;
    }>;
  };
};

export async function fetchStreamSummary(assessmentId: string, streamId: string): Promise<StreamSummary> {
  const qs = new URLSearchParams({ assessment: assessmentId, stream: streamId });
  const { data } = await http.get<StreamSummary>(`/academics/analysis/stream-summary/?${qs.toString()}`);
  return data;
}



// ---------------------------------------------------------------------
// Stream trend — last N assessments at class / student / subject level
// ---------------------------------------------------------------------
export type StreamTrendPoint = {
  assessment_id: string;
  name: string;
  date: string;
  mean: number;
  pass_rate?: number;
  count?: number;
};

export type StreamTrend = {
  assessments: Array<{ id: string; name: string; date: string }>;
  class_trend: TrendPoint[];
  student_trends: Record<string, { points: StreamTrendPoint[]; delta: number; trend: "improving" | "declining" | "stable" }>;
  subject_trends: Record<string, { points: StreamTrendPoint[]; delta: number; trend: "improving" | "declining" | "stable" }>;
};

export async function fetchStreamTrend(streamId: string, limit = 3): Promise<StreamTrend> {
  const qs = new URLSearchParams({ stream: streamId, limit: String(limit) });
  const { data } = await http.get<StreamTrend>(`/academics/analysis/stream-trend/?${qs.toString()}`);
  return data;
}
