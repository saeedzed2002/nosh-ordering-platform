import { useEffect, useState } from "react";

import { ArrowUpRight, House, ShoppingBag, Truck } from "lucide-react";
import { Toast } from "radix-ui";

import heroImage from "./assets/nosh-hero-food.png";
import { Button } from "./components/ui/Button";
import { Drawer } from "./components/ui/Drawer";
import {
  ToastNotice,
  ToastViewport,
  type ToastMessage,
} from "./components/ui/ToastNotice";
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

function App() {
  const [fulfillment, setFulfillment] = useState<FulfillmentMethod>("pickup");
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [notice, setNotice] = useState<ToastMessage | null>(null);

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

  const fulfillmentLabel = fulfillment === "pickup" ? "Pickup" : "Delivery";
  const apiStatusLabel =
    apiStatus === "checking"
      ? "Checking local API"
      : apiStatus === "ready"
        ? "Local API ready"
        : "Local API unavailable";

  function selectFulfillment(method: FulfillmentMethod) {
    setFulfillment(method);
    setNotice({
      title: `${method === "pickup" ? "Pickup" : "Delivery"} selected`,
      description: "Your preference will carry into the ordering flow when it is available.",
    });
  }

  return (
    <Toast.Provider duration={5000} swipeDirection="right">
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
              onClick={() => setIsCartOpen(true)}
            >
              <ShoppingBag aria-hidden="true" className="cart-icon" />
              <span className="cart-label">Your cart</span>
              <span className="cart-count" aria-label="0 items">
                0
              </span>
            </button>
            <Button className="header-order-button" onClick={() => setIsCartOpen(true)}>
              Order now
            </Button>
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
                role="group"
                aria-label="Preferred fulfillment method"
              >
                {(["pickup", "delivery"] as const).map((method) => {
                  const isSelected = fulfillment === method;
                  const label = method === "pickup" ? "Pickup" : "Delivery";
                  const Icon = method === "pickup" ? House : Truck;

                  return (
                    <button
                      key={method}
                      className={isSelected ? "selected" : undefined}
                      type="button"
                      aria-pressed={isSelected}
                      onClick={() => selectFulfillment(method)}
                    >
                      <Icon aria-hidden="true" />
                      {label}
                    </button>
                  );
                })}
              </div>

              <Button className="hero-order-button" onClick={() => setIsCartOpen(true)}>
                Order now <ArrowUpRight aria-hidden="true" />
              </Button>
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
                Open API documentation <ArrowUpRight aria-hidden="true" />
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

        <Drawer
          description="Ordering components are ready for the server rules introduced in later phases."
          open={isCartOpen}
          title="Your cart"
          onOpenChange={setIsCartOpen}
          footer={
            <Button className="drawer-action" variant="secondary" onClick={() => setIsCartOpen(false)}>
              Continue exploring
            </Button>
          }
        >
          <p>
            {fulfillmentLabel} is selected for the next ordering flow.
          </p>
          <p>
            Cart persistence and menu customisation are implemented in Phase 8,
            after server-side pricing and option validation exist.
          </p>
        </Drawer>
      </div>
      <ToastNotice notice={notice} onOpenChange={(open) => !open && setNotice(null)} />
      <ToastViewport />
    </Toast.Provider>
  );
}

export default App;
