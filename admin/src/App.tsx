import type React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AdminLayout } from './layouts/AdminLayout';
import { AuthProvider } from './lib/auth';
import DatasetPage from './pages/DatasetPage';
import LoginPage from './pages/LoginPage';
import ModerationPage from './pages/ModerationPage';
import OverviewPage from './pages/OverviewPage';
import TagsPage from './pages/TagsPage';
import TrustScoresPage from './pages/TrustScoresPage';

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <AdminLayout>{children}</AdminLayout>
    </ProtectedRoute>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route path="/" element={<Shell><OverviewPage /></Shell>} />
          <Route path="/moderation" element={<Shell><ModerationPage /></Shell>} />
          <Route path="/tags" element={<Shell><TagsPage /></Shell>} />
          <Route path="/trust-scores" element={<Shell><TrustScoresPage /></Shell>} />
          <Route path="/dataset" element={<Shell><DatasetPage /></Shell>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
