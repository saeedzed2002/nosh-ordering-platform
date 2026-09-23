import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AdminDashboard } from "./admin/AdminDashboard";
import { AdminLayout } from "./admin/AdminLayout";
import { AdminSignInPage } from "./admin/AdminSignInPage";
import { HomeEditorPage } from "./admin/HomeEditorPage";
import { MenuEditorPage } from "./admin/MenuEditorPage";
import { MenuWorkspacePage } from "./admin/MenuWorkspacePage";
import { MediaLibraryPage } from "./admin/MediaLibraryPage";
import { OrderDeskPage } from "./admin/OrderDeskPage";
import { ReviewDeskPage } from "./admin/ReviewDeskPage";
import { AdminSessionProvider, useAdminSession } from "./admin/session";
import App from "./App";
import { CustomerCartProvider } from "./customerCart";
import { CustomerAccountProvider } from "./customerAccount";
import {
  CustomerAccountGuard,
  CustomerAccountPage,
  CustomerAccountSignInPage,
  CustomerAccountSignUpPage,
} from "./CustomerAccountPages";
import { CustomerCheckoutPage, CustomerOrderConfirmationPage } from "./CustomerCheckoutPage";
import { CustomerMenuItemPage, CustomerMenuPage } from "./CustomerMenuPage";
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
      <CustomerAccountProvider>
        <CustomerCartProvider>
          <AdminSessionProvider>
            <Routes>
          <Route path="/" element={<App />} />
          <Route path="/menu" element={<CustomerMenuPage />} />
          <Route path="/menu/:slug" element={<CustomerMenuItemPage />} />
          <Route path="/checkout" element={<CustomerCheckoutPage />} />
          <Route path="/orders/:publicReference" element={<CustomerOrderConfirmationPage />} />
          <Route path="/account/sign-in" element={<CustomerAccountSignInPage />} />
          <Route path="/account/sign-up" element={<CustomerAccountSignUpPage />} />
          <Route element={<CustomerAccountGuard />}>
            <Route path="/account" element={<CustomerAccountPage />} />
          </Route>
          <Route path="/locations" element={<LocationsPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/admin/sign-in" element={<AdminSignInPage />} />
          <Route element={<AdminGuard />}>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/home" element={<HomeEditorPage />} />
            <Route path="/admin/media" element={<MediaLibraryPage />} />
            <Route path="/admin/menu" element={<MenuWorkspacePage />} />
            <Route path="/admin/menu/new" element={<MenuEditorPage />} />
            <Route path="/admin/menu/:slug" element={<MenuEditorPage />} />
            <Route path="/admin/orders" element={<OrderDeskPage />} />
            <Route path="/admin/reviews" element={<ReviewDeskPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </AdminSessionProvider>
        </CustomerCartProvider>
      </CustomerAccountProvider>
    </BrowserRouter>
  );
}
