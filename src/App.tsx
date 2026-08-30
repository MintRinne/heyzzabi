import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom";
import { ThemeProvider } from "@/components/ThemeProvider";
import { AuthProvider } from "@/lib/auth";

import AuthLayout from "@/pages/auth/AuthLayout";
import LoginPage from "@/pages/auth/LoginPage";
import OnboardingPage from "@/pages/auth/OnboardingPage";
import DashboardLayout from "@/pages/dashboard/DashboardLayout";
import DashboardPage from "@/pages/DashboardPage";
import DocumentsPage from "@/pages/DocumentsPage";
import TasksPage from "@/pages/TasksPage";
import ApprovalsPage from "@/pages/ApprovalsPage";
import HistoryPage from "@/pages/HistoryPage";
import MembersPage from "@/pages/MembersPage";
import ProfilePage from "@/pages/ProfilePage";
import SettingsPage from "@/pages/SettingsPage";
import SettingsTermsPage from "@/pages/SettingsTermsPage";
import SettingsPrivacyPage from "@/pages/SettingsPrivacyPage";
import AiHubPage from "@/pages/AiHubPage";
import AiAgentsPage from "@/pages/AiAgentsPage";
import ProjectNewPage from "@/pages/ProjectNewPage";
import ProjectDetailPage from "@/pages/ProjectDetailPage";

function LegacyProjectRedirect() {
  const { id } = useParams();
  return <Navigate to={`/projects/${id}`} replace />;
}

export default function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AuthLayout />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/onboarding" element={<OnboardingPage />} />
            </Route>

            <Route element={<DashboardLayout />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/documents" element={<DocumentsPage />} />
              <Route path="/tasks" element={<TasksPage />} />
              <Route path="/approvals" element={<ApprovalsPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/members" element={<MembersPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/settings/terms" element={<SettingsTermsPage />} />
              <Route path="/settings/privacy" element={<SettingsPrivacyPage />} />
              <Route path="/ai-hub" element={<AiHubPage />} />
              <Route path="/ai-agents" element={<AiAgentsPage />} />
              <Route path="/project/new" element={<ProjectNewPage />} />
              <Route path="/project/:id" element={<LegacyProjectRedirect />} />
              <Route path="/projects/:id" element={<ProjectDetailPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
