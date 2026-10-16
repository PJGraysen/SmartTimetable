import http from "./http";

export type Term = {
  id: string;
  name: string;
  academic_year_name?: string;
};

export type Subject = {
  id: string;
  code: string;
  name: string;
};

export type InstructionalGroup = {
  id: string;
  code: string;
  name: string;
  teaching_group_name?: string;
};

export type RequirementType = "STANDALONE" | "BLOCK" | "PRACTICAL";

export type LessonRequirement = {
  id: string;
  term: string;
  term_name?: string;
  instructional_group: string | null;
  instructional_group_name?: string;
  subject: string;
  subject_name?: string;
  requirement_type: RequirementType;
  teacher?: number | null;
  teacher_name?: string | null;
  lessons_per_week: number;
  is_active: boolean;
};

export type ValidationIssue = {
  subject: string;
  type: string;
  have: number;
  want: number;
};

export type ValidationGroup = {
  group: string;
  short: ValidationIssue[];
  over: ValidationIssue[];
  extra: Array<{ subject: string; type: string; have: number }>;
  ok: boolean;
};

export type ValidationReport = {
  term: string;
  term_id: string;
  report: ValidationGroup[];
  groups_ok: boolean;
};

// -------------------------------------------------------------------
// Terms — reuse the scheduling dashboard which already returns them
// -------------------------------------------------------------------
export async function fetchTerms(): Promise<Term[]> {
  const { data } = await http.get<{ terms: Term[] }>("/scheduling/dashboard/");
  return Array.isArray(data?.terms) ? data.terms : [];
}

// -------------------------------------------------------------------
// Subjects + Instructional groups
// -------------------------------------------------------------------
export async function fetchSubjects(): Promise<Subject[]> {
  const { data } = await http.get<Subject[] | { results: Subject[] }>(
    "/academics/subjects/",
  );
  if (Array.isArray(data)) return data;
  return data?.results ?? [];
}

export async function fetchInstructionalGroups(): Promise<InstructionalGroup[]> {
  const { data } = await http.get<
    InstructionalGroup[] | { results: InstructionalGroup[] }
  >("/academics/instructional-groups/");
  if (Array.isArray(data)) return data;
  return data?.results ?? [];
}

// -------------------------------------------------------------------
// Lesson requirements
// -------------------------------------------------------------------
export async function fetchLessonRequirements(
  termId: string,
): Promise<LessonRequirement[]> {
  const { data } = await http.get<
    LessonRequirement[] | { results: LessonRequirement[] }
  >("/academics/lesson-requirements/", {
    params: { term: termId, _t: Date.now() },
  });
  if (Array.isArray(data)) return data;
  return data?.results ?? [];
}

export async function patchLessonRequirement(
  id: string,
  patch: Partial<LessonRequirement>,
): Promise<LessonRequirement> {
  const { data } = await http.patch<LessonRequirement>(
    `/academics/lesson-requirements/${id}/`,
    patch,
  );
  return data;
}

export async function createLessonRequirement(
  payload: {
    term: string;
    instructional_group: string;
    subject: string;
    requirement_type: RequirementType;
    lessons_per_week: number;
    is_active?: boolean;
  },
): Promise<LessonRequirement> {
  const { data } = await http.post<LessonRequirement>(
    "/academics/lesson-requirements/",
    payload,
  );
  return data;
}

export async function copyLessonRequirements(
  fromTermId: string,
  toTermId: string,
  apply = false,
): Promise<{
  source: string;
  target: string;
  source_active_lrs?: number;
  created?: number;
  updated?: number;
  unchanged?: number;
  target_active?: number;
  applied?: boolean;
}> {
  const { data } = await http.post("/academics/lesson-requirements/copy/", {
    from_term: fromTermId,
    to_term: toTermId,
    apply,
  });
  return data;
}

export async function validateTerm(termId: string): Promise<ValidationReport> {
  const { data } = await http.get<ValidationReport>(
    "/academics/lesson-requirements/validate/",
    { params: { term: termId, _t: Date.now() } },
  );
  return data;
}

// -------------------------------------------------------------------
// Rule configuration (per term)
// -------------------------------------------------------------------
export type RuleConfig = {
  id: string;
  term: string;
  term_name?: string;
  cross_stream_practicals_enabled: boolean;
  block_sync_enabled: boolean;
  teacher_max_consecutive_enabled: boolean;
  complex_adjacency_enabled: boolean;
  eng_grade10_sync_enabled: boolean;
  single_lesson_per_day_enabled: boolean;
  teacher_free_afternoon_enabled: boolean;
  practical_double_lesson_enabled: boolean;
};

export async function fetchRuleConfig(termId: string): Promise<RuleConfig> {
  const { data } = await http.get<RuleConfig>(
    "/scheduling/rule-config/",
    { params: { term: termId, _t: Date.now() } },
  );
  return data;
}

export async function patchRuleConfig(
  termId: string,
  patch: Partial<RuleConfig>,
): Promise<RuleConfig> {
  const { data } = await http.patch<RuleConfig>(
    "/scheduling/rule-config/",
    patch,
    { params: { term: termId } },
  );
  return data;
}

// -------------------------------------------------------------------
// Pre-flight
// -------------------------------------------------------------------
export type ProposalSeverity = "critical" | "warning" | "info";

export type Proposal = {
  id: string;
  action: string;
  description: string;
  rationale: string;
  target_kind: string;
  target_id: string;
  current_value: Record<string, unknown>;
  proposed_value: Record<string, unknown>;
  severity?: ProposalSeverity;
};

export type PreflightDiagnostic = {
  code: string;
  rule: string;
  message: string;
  required_input: string;
  details?: Record<string, unknown>;
  proposals?: Proposal[];
};

export type PreflightResult = {
  clean: boolean;
  error?: string;
  diagnostics: PreflightDiagnostic[];
  proposals?: Proposal[];
};

export async function runPreflight(termId: string): Promise<PreflightResult> {
  const { data } = await http.get<PreflightResult>(
    "/scheduling/preflight/",
    { params: { term: termId, _t: Date.now() } },
  );
  return data;
}

export async function applyProposal(
  termId: string,
  proposalId: string,
): Promise<PreflightResult & { applied?: Record<string, unknown> }> {
  const { data } = await http.post(
    "/scheduling/proposals/apply/",
    { term: termId, proposal_id: proposalId },
  );
  return data;
}

