import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AdminDashboard } from "./admin/AdminDashboard";
import { AdminLayout } from "./admin/AdminLayout";
import { AdminSignInPage } from "./admin/AdminSignInPage";
import { HomeEditorPage } from "./admin/HomeEditorPage";
import { MediaLibraryPage } from "./admin/MediaLibraryPage";
import { AdminSessionProvider, useAdminSession } from "./admin/session";
import App from "./App";
import { AboutPage, LocationsPage, NotFoundPage } from "./SitePages";

function AdminGuard() {
  const location = useLocation();
  const { ready, session } = useAdminSession();

  if (!ready) {
    return <main className="admin-loading-page">Checking your local session…</main>;
  }

  return session ? <AdminLayout /> : <Navigate to="/admin/sign-in" replace state={{ from: location }} />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <AdminSessionProvider>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/locations" element={<LocationsPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/admin/sign-in" element={<AdminSignInPage />} />
          <Route element={<AdminGuard />}>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/home" element={<HomeEditorPage />} />
            <Route path="/admin/media" element={<MediaLibraryPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AdminSessionProvider>
    </BrowserRouter>
  );
}
