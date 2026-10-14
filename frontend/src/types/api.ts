export type ExtractionStatus = "queued" | "processing" | "completed" | "failed";
export type AnalysisStatus = "not_started" | "queued" | "processing" | "completed" | "failed";

export type ResumeSummary = {
  id: string;
  original_filename: string;
  candidate_name: string | null;
  email: string | null;
  mobile: string | null;
  location: string | null;
  skills: string[];
  uploaded_at: string;
  extraction_status: ExtractionStatus;
  analysis_status: AnalysisStatus;
  error_message: string | null;
};

export type ResumeListResponse = {
  items: ResumeSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type ResumeStatus = {
  id: string;
  extraction_status: ExtractionStatus;
  analysis_status: AnalysisStatus;
  error_message: string | null;
  extracted_at: string | null;
};

export type UploadItemResult = {
  filename: string;
  status: "accepted" | "rejected" | "duplicate";
  resume_id: string | null;
  detail: string | null;
};

export type BulkUploadResponse = {
  accepted: number;
  rejected: number;
  results: UploadItemResult[];
};

export type MeResponse = {
  id: string;
  keycloak_sub: string;
  username: string | null;
  email: string | null;
  display_name: string | null;
  roles: string[];
};

export type ResumeDetail = ResumeSummary & {
  mime_type: string;
  file_size: number;
  extraction_method: string | null;
  extracted_at: string | null;
  extracted_text: string | null;
};

export type RubricCriterion = {
  key: string;
  label: string;
  points: number;
  max_points: number;
  explanation: string;
};

export type Narrative = {
  professional_summary: string;
  experience_summary: string;
  education_summary: string;
  technical_skills: string[];
  non_technical_skills: string[];
  strengths: string[];
  improvements: string[];
};

export type AnalysisDetail = {
  advisory_notice: string;
  rubric: { version: string; total: number; max: number; criteria: RubricCriterion[] };
  missing_or_unclear: string[];
  narrative_available: boolean;
  narrative: Narrative | null;
};

export type AnalysisResponse = {
  id: string;
  resume_id: string;
  analysis_status: AnalysisStatus;
  score: number | null;
  summary: string;
  detailed_result: AnalysisDetail;
  rubric_version: string;
  prompt_version: string;
  model_name: string;
  model_version: string | null;
  created_at: string;
};