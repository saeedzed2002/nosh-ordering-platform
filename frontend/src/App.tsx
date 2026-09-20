import { useEffect, useState } from "react";

import {
  ArrowDown,
  ArrowUpRight,
  Clock3,
  MapPin,
  ShoppingBag,
  Sparkles,
  Truck,
} from "lucide-react";
import { Toast } from "radix-ui";

import { Button } from "./components/ui/Button";
import { Drawer } from "./components/ui/Drawer";
import { FoodCard } from "./components/ui/FoodCard";
import { QuantityStepper } from "./components/ui/QuantityStepper";
import {
  ToastNotice,
  ToastViewport,
  type ToastMessage,
} from "./components/ui/ToastNotice";
import {
  customerBenefits,
  kitchenMoments,
  menuPreviewCategories,
  menuPreviewDishes,
  type MenuPreviewCategory,
  type MenuPreviewDish,
} from "./data/customerPreview";
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
  { label: "Kitchen", href: "#kitchen" },
  { label: "Location", href: "#location" },
];

const moneyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

function formatPrice(priceCents: number) {
  return moneyFormatter.format(priceCents / 100);
}

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({
    behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? "auto"
      : "smooth",
  });
}

function App() {
  const [activeCategory, setActiveCategory] = useState<MenuPreviewCategory["id"]>("all");
  const [cart, setCart] = useState<Record<string, number>>({});
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

  const featuredDishes =
    activeCategory === "all"
      ? menuPreviewDishes
      : menuPreviewDishes.filter((dish) => dish.category === activeCategory);
  const cartItems = menuPreviewDishes
    .filter((dish) => cart[dish.id] !== undefined)
    .map((dish) => ({ dish, quantity: cart[dish.id] }));
  const cartCount = cartItems.reduce((total, item) => total + item.quantity, 0);
  const cartTotal = cartItems.reduce(
    (total, item) => total + item.dish.priceCents * item.quantity,
    0,
  );
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
      description: "The local cart keeps this choice for the current page session.",
    });
  }

  function addDish(dish: MenuPreviewDish) {
    setCart((currentCart) => {
      const quantity = currentCart[dish.id] ?? 0;

      return {
        ...currentCart,
        [dish.id]: Math.min(quantity + 1, 9),
      };
    });
    setNotice({
      title: "Added to your cart",
      description: `${dish.name} is ready to review in the local demo cart.`,
    });
  }

  function updateQuantity(dishId: string, quantity: number) {
    setCart((currentCart) => {
      if (quantity <= 0) {
        const remainingCart = { ...currentCart };
        delete remainingCart[dishId];
        return remainingCart;
      }

      return { ...currentCart, [dishId]: Math.min(quantity, 9) };
    });
  }

  return (
    <Toast.Provider duration={5000} swipeDirection="right">
      <div className="app-shell">
        <a className="skip-link" href="#main-content">
          Skip to main content
        </a>

        <header className="site-header">
          <a className="wordmark" href="#top" aria-label="Nosh home">
            Nosh<span>.</span>
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
              aria-haspopup="dialog"
              aria-label={`Open cart, ${cartCount} ${cartCount === 1 ? "item" : "items"}`}
              onClick={() => setIsCartOpen(true)}
            >
              <ShoppingBag aria-hidden="true" className="cart-icon" />
              <span className="cart-label">Cart</span>
              <span className="cart-count" aria-hidden="true">
                {cartCount}
              </span>
            </button>
            <Button className="header-order-button" onClick={() => scrollToSection("menu")}>
              Order now
            </Button>
          </div>
        </header>

        <main id="main-content">
          <section className="hero" id="top" aria-labelledby="hero-title">
            <div className="hero-copy">
              <p className="eyebrow"><Sparkles aria-hidden="true" /> Today at Nosh</p>
              <h1 id="hero-title">A table worth coming home to.</h1>
              <p className="hero-intro">
                Thoughtful plates from one local kitchen, cooked close to the moment
                you pick them up or send them your way.
              </p>

              <div className="hero-actions">
                <Button onClick={() => scrollToSection("menu")}>
                  Explore today’s menu <ArrowDown aria-hidden="true" />
                </Button>
                <a className="quiet-link" href="#kitchen">
                  Meet the kitchen <ArrowUpRight aria-hidden="true" />
                </a>
              </div>

              <div className="fulfillment-block">
                <span>How should it arrive?</span>
                <div
                  className="fulfillment-selector"
                  role="group"
                  aria-label="Preferred fulfillment method"
                >
                  {(["pickup", "delivery"] as const).map((method) => {
                    const isSelected = fulfillment === method;
                    const label = method === "pickup" ? "Pickup" : "Delivery";
                    const Icon = method === "pickup" ? MapPin : Truck;

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
              </div>
            </div>

            <div className="hero-media">
              <img
                src={menuPreviewDishes[0].image}
                alt={menuPreviewDishes[0].alt}
              />
              <div className="hero-media-note">
                <span>Kitchen note</span>
                <strong>Harissa chicken is on the fire.</strong>
              </div>
            </div>
          </section>

          <section className="service-strip" aria-label="Today’s service details">
            <span><Clock3 aria-hidden="true" /> Lunch pickup starts at 12:00</span>
            <span>One kitchen · one local route</span>
            <span>Short menu · cooked to order</span>
          </section>

          <section className="landing-section category-section" id="menu" aria-labelledby="menu-title">
            <div className="section-heading section-heading--split">
              <div>
                <p className="eyebrow">Start with appetite</p>
                <h2 id="menu-title">A short menu with room to linger.</h2>
              </div>
              <p>
                Pick a direction. Every preview dish below is seeded local data for
                this interactive customer demo.
              </p>
            </div>

            <div className="category-rail" aria-label="Menu categories">
              {menuPreviewCategories.map((category) => (
                <button
                  key={category.id}
                  className={activeCategory === category.id ? "selected" : undefined}
                  type="button"
                  aria-pressed={activeCategory === category.id}
                  onClick={() => setActiveCategory(category.id)}
                >
                  <strong>{category.label}</strong>
                  <span>{category.note}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="landing-section featured-section" id="featured-dishes" aria-labelledby="featured-title">
            <div className="section-heading section-heading--split">
              <div>
                <p className="eyebrow">Featured dishes</p>
                <h2 id="featured-title">
                  {activeCategory === "all" ? "Choose your first plate." : "One good place to begin."}
                </h2>
              </div>
              <p className="featured-cart-note">{cartCount} {cartCount === 1 ? "item" : "items"} in cart</p>
            </div>

            <div className="featured-grid">
              {featuredDishes.map((dish) => (
                <FoodCard
                  key={dish.id}
                  actionLabel="Add to cart"
                  alt={dish.alt}
                  description={dish.description}
                  image={dish.image}
                  name={dish.name}
                  price={formatPrice(dish.priceCents)}
                  status={dish.status}
                  tags={dish.tags}
                  onAction={() => addDish(dish)}
                />
              ))}
            </div>
          </section>

          <section className="promotion-panel" aria-labelledby="promotion-title">
            <img
              src={menuPreviewDishes[1].image}
              alt="Vegetable flatbread, citrus salad, and whipped feta on a warm cream table"
            />
            <div>
              <p className="eyebrow">Limited table</p>
              <h2 id="promotion-title">Weeknight food, with a little more daylight.</h2>
              <p>
                Our flatbread and seasonal sides are made for sharing. The local demo
                menu changes without claiming real-time availability.
              </p>
              <Button variant="secondary" onClick={() => scrollToSection("featured-dishes")}>
                See featured plates <ArrowUpRight aria-hidden="true" />
              </Button>
            </div>
          </section>

          <section className="landing-section kitchen-section" id="kitchen" aria-labelledby="kitchen-title">
            <div className="kitchen-story">
              <p className="eyebrow">A kitchen with a point of view</p>
              <h2 id="kitchen-title">The less a dish travels, the more it feels like dinner.</h2>
              <p>
                Nosh is designed around a small, legible handoff: food starts in one
                kitchen, moves through one ordering flow, and reaches one local table.
              </p>
              <a className="quiet-link" href="#location">
                Find the kitchen <MapPin aria-hidden="true" />
              </a>
            </div>
            <ol className="kitchen-moments">
              {kitchenMoments.map((moment) => (
                <li key={moment.time}>
                  <time>{moment.time}</time>
                  <span>{moment.label}</span>
                </li>
              ))}
            </ol>
          </section>

          <section className="benefits-section" aria-label="Nosh principles">
            {customerBenefits.map((benefit, index) => (
              <article key={benefit.title}>
                <span>0{index + 1}</span>
                <h2>{benefit.title}</h2>
                <p>{benefit.copy}</p>
              </article>
            ))}
          </section>

          <section className="location-section" id="location" aria-labelledby="location-title">
            <div>
              <p className="eyebrow">One place to find us</p>
              <h2 id="location-title">Nosh on Market Street.</h2>
              <p>12 Market Street · Tuesday to Sunday · 12:00–21:30</p>
            </div>
            <div className="location-actions">
              <span><MapPin aria-hidden="true" /> Pickup from the kitchen</span>
              <Button onClick={() => setIsCartOpen(true)}>
                Review cart <ShoppingBag aria-hidden="true" />
              </Button>
            </div>
          </section>
        </main>

        <footer className="site-footer">
          <div className="footer-wordmark">Nosh<span>.</span></div>
          <div>
            <p>Local food, set at a human pace.</p>
            <span className={`api-status api-status-${apiStatus}`} aria-live="polite">
              <span aria-hidden="true" />
              {apiStatusLabel}
            </span>
          </div>
          <div className="footer-links">
            <a href="#menu">Menu</a>
            <a href="#kitchen">Kitchen</a>
            <a href="#location">Location</a>
          </div>
        </footer>

        <Drawer
          description={
            cartCount === 0
              ? "Add a preview dish to see the seeded local cart in action."
              : `${fulfillmentLabel} is selected for this browser-only cart session.`
          }
          open={isCartOpen}
          title={`Your cart${cartCount > 0 ? ` · ${cartCount}` : ""}`}
          onOpenChange={setIsCartOpen}
          footer={
            <div className="cart-drawer-footer">
              {cartCount > 0 ? <strong>Subtotal {formatPrice(cartTotal)}</strong> : null}
              <Button className="drawer-action" variant="secondary" onClick={() => setIsCartOpen(false)}>
                Continue exploring
              </Button>
            </div>
          }
        >
          {cartItems.length === 0 ? (
            <div className="empty-cart">
              <ShoppingBag aria-hidden="true" />
              <p>Your cart is waiting for its first plate.</p>
              <Button
                variant="secondary"
                onClick={() => {
                  setIsCartOpen(false);
                  scrollToSection("menu");
                }}
              >
                Browse dishes
              </Button>
            </div>
          ) : (
            <div className="cart-item-list">
              {cartItems.map(({ dish, quantity }) => (
                <article key={dish.id} className="cart-item">
                  <img src={dish.image} alt="" />
                  <div>
                    <div className="cart-item-heading">
                      <h3>{dish.name}</h3>
                      <strong>{formatPrice(dish.priceCents * quantity)}</strong>
                    </div>
                    <p>{formatPrice(dish.priceCents)} each</p>
                    <QuantityStepper
                      max={9}
                      min={0}
                      value={quantity}
                      onValueChange={(nextQuantity) => updateQuantity(dish.id, nextQuantity)}
                    />
                  </div>
                </article>
              ))}
              <p className="cart-boundary-note">
                This cart is page-session state only. Menu validation, persistence, and
                checkout arrive in later phases.
              </p>
            </div>
          )}
        </Drawer>
      </div>
      <ToastNotice notice={notice} onOpenChange={(open) => !open && setNotice(null)} />
      <ToastViewport />
    </Toast.Provider>
  );
}

export default App;
