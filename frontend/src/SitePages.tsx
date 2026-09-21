import { ArrowLeft, Clock3, MapPin, Truck } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { apiBaseUrl } from "./site";

type OperatingHour = {
  weekday: number;
  opens_at: string | null;
  closes_at: string | null;
  is_closed: boolean;
};

type Location = {
  id: string;
  name: string;
  address_text: string;
  pickup_instructions: string | null;
  delivery_area_text: string | null;
  pickup_available: boolean;
  delivery_available: boolean;
  preparation_minutes: number;
  hours: OperatingHour[];
};

const weekdayNames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function SitePageShell({ children }: { children: ReactNode }) {
  return (
    <div className="site-page-shell">
      <header className="site-page-header">
        <Link className="wordmark" to="/" aria-label="Nosh home">Nosh<span>.</span></Link>
        <Link className="site-page-back-link" to="/"><ArrowLeft aria-hidden="true" /> Back to home</Link>
      </header>
      {children}
    </div>
  );
}

function formatHours(hour: OperatingHour): string {
  if (hour.is_closed || !hour.opens_at || !hour.closes_at) {
    return "Closed";
  }
  return `${hour.opens_at.slice(0, 5)}–${hour.closes_at.slice(0, 5)}`;
}

export function LocationsPage() {
  const [locations, setLocations] = useState<Location[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "unavailable">("loading");

  useEffect(() => {
    let active = true;
    void fetch(`${apiBaseUrl}/api/v1/catalog/locations`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Locations unavailable");
        }
        return response.json() as Promise<Location[]>;
      })
      .then((nextLocations) => {
        if (active) {
          setLocations(nextLocations);
          setStatus("ready");
        }
      })
      .catch(() => {
        if (active) {
          setStatus("unavailable");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <SitePageShell>
      <main className="site-information-page">
        <header className="site-information-heading">
          <p className="eyebrow"><MapPin aria-hidden="true" /> Find the kitchen</p>
          <h1>One local counter. One clear handoff.</h1>
          <p>Pickup and delivery details come from the running local catalog, not a static claim.</p>
        </header>
        {status === "loading" ? <p className="site-page-status">Loading local location details…</p> : null}
        {status === "unavailable" ? <p className="site-page-status error">The local location service is unavailable. Return home and check the API status.</p> : null}
        {locations.map((location) => (
          <article key={location.id} className="site-location-card">
            <div>
              <p className="eyebrow">Kitchen counter</p>
              <h2>{location.name}</h2>
              <p>{location.address_text}</p>
              {location.pickup_instructions ? <p>{location.pickup_instructions}</p> : null}
              <div className="site-location-options">
                {location.pickup_available ? <span><MapPin aria-hidden="true" /> Pickup in about {location.preparation_minutes} minutes</span> : null}
                {location.delivery_available ? <span><Truck aria-hidden="true" /> {location.delivery_area_text}</span> : null}
              </div>
            </div>
            <div className="site-location-hours">
              <p><Clock3 aria-hidden="true" /> Hours</p>
              <dl>
                {location.hours.map((hour) => (
                  <div key={hour.weekday}>
                    <dt>{weekdayNames[hour.weekday]}</dt>
                    <dd>{formatHours(hour)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </article>
        ))}
      </main>
    </SitePageShell>
  );
}

export function AboutPage() {
  return (
    <SitePageShell>
      <main className="site-information-page about-page">
        <header className="site-information-heading">
          <p className="eyebrow">The Nosh approach</p>
          <h1>Food with less distance between the kitchen and the table.</h1>
          <p>One local restaurant, a short useful menu, and a handoff that stays legible from first choice to pickup.</p>
        </header>
        <section className="about-principles" aria-label="Nosh principles">
          <article><span>01</span><h2>Cook close to the moment.</h2><p>Each dish begins in one kitchen and is made to travel a short, local route.</p></article>
          <article><span>02</span><h2>Say what is true.</h2><p>Availability, timing, and the day’s welcome should be clear instead of decorative promises.</p></article>
          <article><span>03</span><h2>Make service feel human.</h2><p>The customer order and the kitchen desk are designed to reduce the number of unclear handoffs.</p></article>
        </section>
      </main>
    </SitePageShell>
  );
}

export function NotFoundPage() {
  return (
    <SitePageShell>
      <main className="site-not-found">
        <p className="eyebrow">Route not found</p>
        <h1>This page has not been set for service.</h1>
        <p>Return to the current Nosh home page and choose a published route.</p>
        <Link className="site-page-back-link" to="/"><ArrowLeft aria-hidden="true" /> Return home</Link>
      </main>
    </SitePageShell>
  );
}
