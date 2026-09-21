import { Image, LayoutDashboard, LogOut, PanelsTopLeft } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { useAdminSession } from "./session";

const navigationItems = [
  { label: "Home", to: "/admin/home", icon: PanelsTopLeft },
  { label: "Media", to: "/admin/media", icon: Image },
];

function navigationClassName({ isActive }: { isActive: boolean }): string {
  return isActive ? "admin-navigation-link active" : "admin-navigation-link";
}

export function AdminLayout() {
  const { session, signOut } = useAdminSession();

  return (
    <div className="admin-shell">
      <a className="skip-link" href="#admin-main-content">
        Skip to administration content
      </a>
      <aside className="admin-sidebar">
        <NavLink className="admin-wordmark" to="/admin/home" aria-label="Nosh administration home">
          Nosh<span>.</span>
          <small>Kitchen desk</small>
        </NavLink>
        <nav aria-label="Administration navigation">
          <p className="admin-nav-label">Publishing</p>
          {navigationItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink key={item.to} className={navigationClassName} to={item.to}>
                <Icon aria-hidden="true" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
        <div className="admin-sidebar-footer">
          <div className="admin-user-summary">
            <span aria-hidden="true">{session?.user.display_name.slice(0, 1)}</span>
            <div>
              <strong>{session?.user.display_name}</strong>
              <small>{session?.user.role}</small>
            </div>
          </div>
          <Button className="admin-sign-out" variant="quiet" onClick={signOut}>
            <LogOut aria-hidden="true" />
            Sign out
          </Button>
        </div>
      </aside>
      <div className="admin-workspace">
        <header className="admin-topbar">
          <span className="admin-topbar-kicker"><LayoutDashboard aria-hidden="true" /> Local publishing desk</span>
          <span>Changes stay private until you publish.</span>
        </header>
        <main id="admin-main-content" className="admin-main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
