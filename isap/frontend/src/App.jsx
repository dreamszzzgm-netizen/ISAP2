import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './legacy-pages/Layout';
import Login from './legacy-pages/Login';
import Dashboard from './legacy-pages/Dashboard';
import Organizations from './legacy-pages/Organizations';
import Facilities from './legacy-pages/Facilities';
import FacilityDetail from './legacy-pages/FacilityDetail';
import FacilityOpoDetails from './legacy-pages/FacilityOpoDetails';
import PmlaWizard from './legacy-pages/PmlaWizard';
import Documents from './legacy-pages/Documents';
import Persons from './legacy-pages/Persons';
import Regulatory from './legacy-pages/Regulatory';
import PmlaSamples from './legacy-pages/PmlaSamples';
import AiSettings from './legacy-pages/AiSettings';

function AppRoutes() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="*" element={<Login />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="organizations" element={<Organizations />} />
        <Route path="persons" element={<Persons />} />
        <Route path="facilities" element={<Facilities />} />
        <Route path="facilities/:id" element={<FacilityDetail />} />
        <Route path="facilities/:id/opo" element={<FacilityOpoDetails />} />
        <Route path="pmla" element={<PmlaWizard />} />
        <Route path="documents" element={<Documents />} />
        <Route path="regulatory" element={<Regulatory />} />
        <Route path="samples" element={<PmlaSamples />} />
        <Route path="ai" element={<AiSettings />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
