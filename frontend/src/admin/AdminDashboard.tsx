import { ArrowUpRight, CheckCircle2, ClipboardList, Image, PanelsTopLeft, SlidersHorizontal, UtensilsCrossed } from "lucide-react";
import { Link, Navigate } from "react-router-dom";

import { useAdminSession } from "./session";

export function AdminDashboard() {
  const { session } = useAdminSession();

  if (session?.user.role === "kitchen") {
    return <Navigate replace to="/admin/orders" />;
  }

  return (
    <div className="admin-dashboard">
      <header className="admin-page-heading">
        <div>
          <p className="admin-kicker">Service pass</p>
          <h1>Keep the first impression true to today.</h1>
          <p>
            {session?.user.display_name}, this desk keeps unpublished work separate from the
            live customer page.
          </p>
        </div>
        <div className="admin-publish-promise">
          <CheckCircle2 aria-hidden="true" />
          <span>Draft first. Preview second. Publish last.</span>
        </div>
      </header>
      <section className="admin-action-grid" aria-label="Publishing actions">
        <Link className="admin-action-card" to="/admin/orders">
          <ClipboardList aria-hidden="true" />
          <div>
            <span>Order desk</span>
            <strong>Keep every handoff clear</strong>
            <p>Review the next safe step, customer details, allergens, timing, and the kitchen queue.</p>
          </div>
          <ArrowUpRight aria-hidden="true" />
        </Link>
        <Link className="admin-action-card" to="/admin/operations">
          <SlidersHorizontal aria-hidden="true" />
          <div>
            <span>Restaurant operations</span>
            <strong>Keep the business rules visible</strong>
            <p>Manage promotions, service settings, accounts, reports, and the owner audit history.</p>
          </div>
          <ArrowUpRight aria-hidden="true" />
        </Link>
        <Link className="admin-action-card" to="/admin/menu">
          <UtensilsCrossed aria-hidden="true" />
          <div>
            <span>Menu service</span>
            <strong>Keep every plate accurate</strong>
            <p>Create food items, set price and options, record allergens, and pause service safely.</p>
          </div>
          <ArrowUpRight aria-hidden="true" />
        </Link>
        <Link className="admin-action-card" to="/admin/home">
          <PanelsTopLeft aria-hidden="true" />
          <div>
            <span>Home page</span>
            <strong>Shape the welcome</strong>
            <p>Update the hero, featured dish, kitchen story, and location callout.</p>
          </div>
          <ArrowUpRight aria-hidden="true" />
        </Link>
        <Link className="admin-action-card" to="/admin/media">
          <Image aria-hidden="true" />
          <div>
            <span>Media library</span>
            <strong>Keep every image useful</strong>
            <p>Upload, replace, crop around the focal point, and see where an image appears.</p>
          </div>
          <ArrowUpRight aria-hidden="true" />
        </Link>
      </section>
      <section className="admin-workflow-card" aria-labelledby="admin-workflow-title">
        <div>
          <p className="admin-kicker">How this desk works</p>
          <h2 id="admin-workflow-title">There is no accidental publish.</h2>
        </div>
        <ol>
          <li><span>01</span> Save an editable private draft.</li>
          <li><span>02</span> Read the live preview beside the form.</li>
          <li><span>03</span> Publish the saved version deliberately.</li>
        </ol>
      </section>
    </div>
  );
}
