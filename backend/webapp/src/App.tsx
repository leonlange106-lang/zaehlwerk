import { Center, Loader } from '@mantine/core';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import { AppLayout } from './layout/AppLayout';
import { LoginView } from './features/auth/LoginView';
import { OnboardingView } from './features/auth/OnboardingView';
import { DashboardView } from './features/dashboard/DashboardView';
import { ReadingsView } from './features/systems/ReadingsView';
import { SystemDetailView } from './features/systems/SystemDetailView';
import { TariffsView, ReportsView, AuditView, SettingsView, AdminView } from './features/stubs';

export default function App() {
  const { checked, status, onboardingNeeded } = useAuth();

  if (!checked) {
    return <Center mih="100vh"><Loader /></Center>;
  }
  if (!status?.authenticated) {
    return <LoginView />;
  }
  if (onboardingNeeded) {
    return <OnboardingView />;
  }

  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardView />} />
        <Route path="/readings" element={<ReadingsView />} />
        <Route path="/readings/:id" element={<SystemDetailView />} />
        <Route path="/tariffs" element={<TariffsView />} />
        <Route path="/reports" element={<ReportsView />} />
        <Route path="/audit" element={<AuditView />} />
        <Route path="/settings" element={<SettingsView />} />
        <Route path="/admin" element={<AdminView />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
