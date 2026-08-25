import { apiGet } from "./client";

export interface ApplicationRecord {
  id: number | null;
  company: string;
  position: string;
  location: string | null;
  recruit_type: string | null;
  apply_source: string | null;
  apply_link: string | null;
  apply_date: string;
  status: string;
  notes: string | null;
}

export interface ApplicationQuery {
  status?: string;
  keyword?: string;
}

export function getApplications(query: ApplicationQuery = {}) {
  const params = new URLSearchParams();
  if (query.status) params.set("status", query.status);
  if (query.keyword) params.set("keyword", query.keyword);
  const queryString = params.toString();
  const suffix = queryString ? `?${queryString}` : "";
  return apiGet<ApplicationRecord[]>(`/applications${suffix}`);
}
