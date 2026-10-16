import { ApiError, apiFetch } from "@/lib/api";
import type {
  AnalysisResponse,
  BulkUploadResponse,
  ResumeDetail,
  ResumeListResponse,
  ResumeStatus,
  UploadItemResult,
  JobMatchesResponse,
} from "@/types/api";

export function listResumes(query: string): Promise<ResumeListResponse> {
  return apiFetch<ResumeListResponse>(`/resumes?${query}`);
}

export function getResume(id: string): Promise<ResumeDetail> {
  return apiFetch<ResumeDetail>(`/resumes/${id}`);
}

export function getAnalysis(id: string): Promise<AnalysisResponse> {
  return apiFetch<AnalysisResponse>(`/resumes/${id}/analysis`);
}

export function analyzeResume(id: string): Promise<ResumeStatus> {
  return apiFetch<ResumeStatus>(`/resumes/${id}/analyze`, { method: "POST" });
}

export function retryResume(id: string): Promise<ResumeStatus> {
  return apiFetch<ResumeStatus>(`/resumes/${id}/retry`, { method: "POST" });
}

export function deleteResume(id: string): Promise<void> {
  return apiFetch<void>(`/resumes/${id}`, { method: "DELETE" });
}

async function uploadOne(file: File): Promise<UploadItemResult> {
  const body = new FormData();
  body.append("file", file);
  try {
    return await apiFetch<UploadItemResult>("/resumes", { method: "POST", body });
  } catch (error) {
    if (error instanceof ApiError) {
      return {
        filename: file.name,
        status: error.status === 409 ? "duplicate" : "rejected",
        resume_id: null,
        detail: error.message,
      };
    }
    throw error;
  }
}

export async function uploadResumes(files: File[]): Promise<UploadItemResult[]> {
  if (files.length === 1) return [await uploadOne(files[0])];
  const body = new FormData();
  files.forEach((file) => body.append("files", file));
  const response = await apiFetch<BulkUploadResponse>("/resumes/bulk", { method: "POST", body });
  return response.results;
}

export function getJobMatches(id: string): Promise<JobMatchesResponse> {
  return apiFetch<JobMatchesResponse>(`/resumes/${id}/job-matches`);
}

export function refreshJobMatches(id: string): Promise<JobMatchesResponse> {
  return apiFetch<JobMatchesResponse>(`/resumes/${id}/job-matches`, { method: "POST" });
}