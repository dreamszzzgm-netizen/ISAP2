import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './pages/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Organizations from './pages/Organizations';
import Facilities from './pages/Facilities';
import FacilityDetail from './pages/FacilityDetail';
import FacilityOpoDetails from './pages/FacilityOpoDetails';
import PmlaWizard from './pages/PmlaWizard';
import Documents from './pages/Documents';
import Persons from './pages/Persons';
import Regulatory from './pages/Regulatory';
import PmlaSamples from './pages/PmlaSamples';
import AiSettings from './pages/AiSettings';

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
