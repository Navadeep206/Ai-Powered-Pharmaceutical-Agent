import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import DashboardPage from './pages/Dashboard';
import InvestigationsPage from './pages/Investigations';
import NewInvestigationPage from './pages/Investigations/NewInvestigation';
import InvestigationDetailPage from './pages/Investigations/InvestigationDetail';
import CAPAManagementPage from './pages/CAPAManagement';
import SettingsPage from './pages/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="investigations" element={<InvestigationsPage />} />
          <Route path="investigations/new" element={<NewInvestigationPage />} />
          <Route path="investigations/:id" element={<InvestigationDetailPage />} />
          <Route path="capa" element={<CAPAManagementPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
