import { useEffect, useState } from "react";

import heroImage from "./assets/nosh-hero-food.png";
import { apiBaseUrl } from "./site";

type FulfillmentMethod = "pickup" | "delivery";
type ApiStatus = "checking" | "ready" | "unavailable";

type HealthPayload = {
  status: "ok" | "degraded";
  database: {
    status: "ok" | "unavailable";
  };
};

const navigationItems = [
  { label: "Menu", href: "#menu" },
  { label: "Locations", href: "#locations" },
  { label: "About", href: "#about" },
];

function CartIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M3 4h2l2.1 10.2a2 2 0 0 0 2 1.6h8.7a2 2 0 0 0 2-1.6L21 8H7" />
      <circle cx="10" cy="20" r="1" />
      <circle cx="18" cy="20" r="1" />
    </svg>
  );
}

function PickupIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="m4 11 8-7 8 7" />
      <path d="M6 10v9h12v-9" />
      <path d="M10 19v-5h4v5" />
    </svg>
  );
}

function DeliveryIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M5 19 19 5" />
      <path d="M11 5h8v8" />
    </svg>
  );
}

function App() {
  const [fulfillment, setFulfillment] =
    useState<FulfillmentMethod>("pickup");
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    let isCancelled = false;

    async function checkApiHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/health`);
        const payload = (await response.json()) as HealthPayload;

        if (!isCancelled) {
          setApiStatus(
            response.ok && payload.status === "ok" && payload.database.status === "ok"
              ? "ready"
              : "unavailable",
          );
        }
      } catch {
        if (!isCancelled) {
          setApiStatus("unavailable");
        }
      }
    }

    void checkApiHealth();

    return () => {
      isCancelled = true;
    };
  }, []);

  const fulfillmentLabel =
    fulfillment === "pickup" ? "Pickup" : "Delivery";
  const apiStatusLabel =
    apiStatus === "checking"
      ? "Checking local API"
      : apiStatus === "ready"
        ? "Local API ready"
        : "Local API unavailable";

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>

      <header className="site-header">
        <a className="wordmark" href="#" aria-label="Nosh home">
          Nosh
        </a>
        <nav aria-label="Primary navigation">
          <ul className="navigation-list">
            {navigationItems.map((item) => (
              <li key={item.href}>
                <a href={item.href}>{item.label}</a>
              </li>
            ))}
          </ul>
        </nav>
        <div className="header-actions">
          <button
            className="cart-trigger"
            type="button"
            aria-expanded={isCartOpen}
            aria-controls="phase-zero-cart"
            onClick={() => setIsCartOpen(true)}
          >
            <span aria-hidden="true" className="cart-icon">
              <CartIcon />
            </span>
            <span className="cart-label">Your cart</span>
            <span className="cart-count" aria-label="0 items">
              0
            </span>
          </button>
          <button
            className="button button-primary header-order-button"
            type="button"
            onClick={() => setIsCartOpen(true)}
          >
            Order now
          </button>
        </div>
      </header>

      <main id="main-content">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <h1 id="hero-title">
              From our kitchen,
              <br />
              straight to your table.
            </h1>

            <div
              className="fulfillment-selector"
              role="radiogroup"
              aria-label="Preferred fulfillment method"
            >
              {(["pickup", "delivery"] as const).map((method) => {
                const isSelected = fulfillment === method;
                const label = method === "pickup" ? "Pickup" : "Delivery";

                return (
                  <button
                    key={method}
                    className={isSelected ? "selected" : undefined}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    onClick={() => setFulfillment(method)}
                  >
                    <span aria-hidden="true">
                      {method === "pickup" ? <PickupIcon /> : <DeliveryIcon />}
                    </span>
                    {label}
                  </button>
                );
              })}
            </div>

            <button
              className="button button-primary hero-order-button"
              type="button"
              onClick={() => setIsCartOpen(true)}
            >
              Order now <span aria-hidden="true">→</span>
            </button>
          </div>

          <div className="hero-media">
            <img
              src={heroImage}
              alt="Grilled chicken with hummus, chickpeas, cucumber, herbs, and flatbread"
            />
          </div>
        </section>

        <section className="foundation-section" id="menu">
          <div>
            <p className="section-label">Local development baseline</p>
            <h2>The kitchen opens in deliberate stages.</h2>
          </div>
          <div className="foundation-detail">
            <p>
              The first milestone connects the customer shell, documented API,
              and PostgreSQL readiness check. The menu and checkout become
              real only after their ordering rules exist in the backend.
            </p>
            <a className="text-link" href={`${apiBaseUrl}/docs`}>
              Open API documentation <span aria-hidden="true">↗</span>
            </a>
          </div>
        </section>

        <section className="information-grid" aria-label="Local demo status">
          <article id="locations">
            <h2>One location, one ordering flow.</h2>
            <p>
              Nosh starts as a single-brand local demo. Marketplace and
              multi-tenant behavior are outside this product boundary.
            </p>
          </article>
          <article id="about">
            <h2>Built for trustworthy handoff.</h2>
            <p>
              Payments, delivery, notifications, and maps will remain clearly
              simulated unless an explicitly authorized integration is added.
            </p>
          </article>
        </section>
      </main>

      <footer className="site-footer">
        <span>Nosh Kitchen & Delivery</span>
        <span className={`api-status api-status-${apiStatus}`} aria-live="polite">
          <span aria-hidden="true" />
          {apiStatusLabel}
        </span>
      </footer>

      {isCartOpen ? (
        <aside
          className="cart-drawer"
          id="phase-zero-cart"
          role="dialog"
          aria-modal="true"
          aria-labelledby="cart-drawer-title"
        >
          <div className="cart-drawer-header">
            <h2 id="cart-drawer-title">Your cart</h2>
            <button
              className="icon-button"
              type="button"
              onClick={() => setIsCartOpen(false)}
              aria-label="Close cart"
            >
              ×
            </button>
          </div>
          <p>
            {fulfillmentLabel} is selected for the next ordering flow.
          </p>
          <p>
            Cart persistence and menu customization are implemented in Phase
            8, after server-side pricing and option validation exist.
          </p>
          <button
            className="button button-secondary"
            type="button"
            onClick={() => setIsCartOpen(false)}
          >
            Continue exploring
          </button>
        </aside>
      ) : null}
    </div>
  );
}

export default App;
