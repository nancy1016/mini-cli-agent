import type { ApplicationRecord } from "./applications";
import { apiGet } from "./client";
import type { InterviewRecord } from "./interviews";

export interface DashboardSummary {
  total_applications: number;
  active_applications: number;
  offer_count: number;
  next_three_days_interviews: number;
  next_thirty_days_interviews: number;
  missing_info_count: number;
  recent_applications: ApplicationRecord[];
  upcoming_interviews: InterviewRecord[];
}

export function getDashboardSummary() {
  return apiGet<DashboardSummary>("/dashboard/summary");
}
