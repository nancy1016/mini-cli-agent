import { apiGet } from "./client";

export type InterviewRange =
  | "today"
  | "tomorrow"
  | "next_three_days"
  | "this_week"
  | "next_thirty_days";

export interface InterviewRecord {
  id: number | null;
  application_id: number;
  company: string;
  position: string;
  stage: string;
  interview_time: string;
  interview_method: string | null;
  meeting_link: string | null;
  notes: string | null;
}

export function getInterviews(range: InterviewRange = "next_three_days") {
  return apiGet<InterviewRecord[]>(`/interviews?range=${range}`);
}
