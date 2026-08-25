import { apiGet } from "./client";

export interface MissingInfoRecord {
  company: string;
  position: string;
  missing_fields: string[];
  suggestion: string;
}

export function getMissingInfo() {
  return apiGet<MissingInfoRecord[]>("/missing-info");
}
