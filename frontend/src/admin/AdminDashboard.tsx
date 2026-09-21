import { ArrowUpRight, CheckCircle2, Image, PanelsTopLeft } from "lucide-react";
import { Link } from "react-router-dom";

import { useAdminSession } from "./session";

export function AdminDashboard() {
  const { session } = useAdminSession();

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
