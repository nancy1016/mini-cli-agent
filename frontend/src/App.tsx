import { Navigate, Route, Routes } from "react-router-dom";

import MainLayout from "./layouts/MainLayout";
import AgentPage from "./pages/AgentPage";
import AnalysisPage from "./pages/AnalysisPage";
import ApplicationsPage from "./pages/ApplicationsPage";
import DashboardPage from "./pages/DashboardPage";
import ExperiencesPage from "./pages/ExperiencesPage";
import InterviewsPage from "./pages/InterviewsPage";
import MissingInfoPage from "./pages/MissingInfoPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="applications" element={<ApplicationsPage />} />
        <Route path="interviews" element={<InterviewsPage />} />
        <Route path="missing-info" element={<MissingInfoPage />} />
        <Route path="agent" element={<AgentPage />} />
        <Route path="experiences" element={<ExperiencesPage />} />
        <Route path="analysis" element={<AnalysisPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
