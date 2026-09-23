import { useEffect, useState } from "react";

import { ArrowRight, Clock3, MapPin, Sparkles, Truck } from "lucide-react";
import { Link } from "react-router-dom";

import heroImage from "./assets/nosh-hero-food.webp";
import seasonalSpreadImage from "./assets/nosh-seasonal-spread.webp";
import {
  CustomerMenuCard,
  CustomerSiteFooter,
  CustomerSiteHeader,
} from "./CustomerMenuPage";
import { useCustomerReviewEligibility } from "./customerAccount";
import { customerMediaUrl, useCustomerCatalog } from "./customerCatalog";
import { apiBaseUrl } from "./site";

type ApiStatus = "checking" | "ready" | "unavailable";

type HealthPayload = {
  status: "ok" | "degraded";
  database: { status: "ok" | "unavailable" };
};

type PublishedHomeContent = {
  content_key: string;
  heading: string;
  supporting_copy: string;
  featured_menu_item_slug: string | null;
  media: { id: string; alt_text: string } | null;
};

const kitchenMoments = [
  { time: "09:00", label: "Prep starts with the market" },
  { time: "12:00", label: "First pickup leaves the pass" },
  { time: "18:00", label: "Last delivery heads across town" },
];

const customerBenefits = [
  { title: "Cooked for the handoff", copy: "A short menu lets the kitchen make each dish close to the moment it leaves." },
  { title: "A clear way home", copy: "Pickup and delivery are stated early, so the next decision is never hidden." },
  { title: "Seasonal by design", copy: "The menu shifts with what is good now instead of pretending every dish is permanent." },
];

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [publishedHomeContent, setPublishedHomeContent] = useState<PublishedHomeContent[]>([]);
  const catalog = useCustomerCatalog();
  const eligibleReviewMenuItemSlugs = useCustomerReviewEligibility();

  useEffect(() => {
    const controller = new AbortController();
    void fetch(`${apiBaseUrl}/api/v1/health`, { signal: controller.signal })
      .then(async (response) => {
        const payload = (await response.json()) as HealthPayload;
        setApiStatus(response.ok && payload.status === "ok" && payload.database.status === "ok" ? "ready" : "unavailable");
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setApiStatus("unavailable");
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void fetch(`${apiBaseUrl}/api/v1/catalog/home`, {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Published home content is unavailable.");
        }
        return response.json() as Promise<PublishedHomeContent[]>;
      })
      .then((content) => setPublishedHomeContent(content))
      .catch(() => {
        // The home page stays usable while the editable content service recovers.
      });
    return () => controller.abort();
  }, []);

  const homeSection = (contentKey: string) => publishedHomeContent.find((content) => content.content_key === contentKey);
  const heroContent = homeSection("hero");
  const featuredContent = homeSection("featured-dish");
  const kitchenContent = homeSection("kitchen-story");
  const locationContent = homeSection("location-callout");
  const imageSource = (content: PublishedHomeContent | undefined, fallback: string) =>
    content?.media && !content.media.alt_text.startsWith("Development placeholder")
      ? customerMediaUrl(content.media)
      : fallback;
  const imageAlt = (content: PublishedHomeContent | undefined, fallback: string) =>
    content?.media && !content.media.alt_text.startsWith("Development placeholder")
      ? content.media.alt_text
      : fallback;
  const preparationMinutes = catalog.data?.location?.preparation_minutes ?? null;
  const featuredItems = catalog.data?.items.slice(0, 3) ?? [];
  const apiStatusLabel = apiStatus === "checking" ? "Checking local API" : apiStatus === "ready" ? "Local API ready" : "Local API unavailable";
  const featuredDestination = featuredContent?.featured_menu_item_slug ? `/menu/${featuredContent.featured_menu_item_slug}` : "/menu";

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <CustomerSiteHeader />
      <main id="main-content">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow"><Sparkles aria-hidden="true" /> Today at Nosh</p>
            <h1 id="hero-title">{heroContent?.heading ?? "A table worth coming home to."}</h1>
            <p className="hero-intro">{heroContent?.supporting_copy ?? "Thoughtful plates from one local kitchen, cooked close to the moment you pick them up or send them your way."}</p>
            <div className="hero-actions">
              <Link className="nosh-button" data-size="default" data-variant="primary" to="/menu">Explore today’s menu <ArrowRight aria-hidden="true" /></Link>
              <Link className="quiet-link" to="/about">Meet the kitchen <ArrowRight aria-hidden="true" /></Link>
            </div>
            <div className="fulfillment-block"><span>Today’s service</span><div className="home-service-note"><MapPin aria-hidden="true" /> Pickup from one local kitchen</div></div>
          </div>
          <div className="hero-media"><img src={imageSource(heroContent, heroImage) ?? heroImage} alt={imageAlt(heroContent, "Grilled chicken with hummus, chickpeas, cucumber, herbs, and flatbread")} /><div className="hero-media-note"><span>Kitchen note</span><strong>{preparationMinutes ? `About ${preparationMinutes} minutes from the pass.` : "Today’s timing is set with the live menu."}</strong></div></div>
        </section>

        <section className="service-strip" aria-label="Today’s service details"><span><Clock3 aria-hidden="true" /> {preparationMinutes ? `About ${preparationMinutes} min from the kitchen` : "Timing updates with the menu"}</span><span>One kitchen · one local route</span><span>Short menu · cooked to order</span></section>

        <section className="landing-section featured-section" id="menu" aria-labelledby="menu-title">
          <div className="section-heading section-heading--split"><div><p className="eyebrow">Live kitchen board</p><h2 id="menu-title">Today’s menu, as the kitchen has set it.</h2></div><p>These dishes read from the published catalogue. Availability, dietary tags, allergens, and prices no longer come from seeded browser data.</p></div>
          {catalog.status === "loading" ? <div className="home-menu-loading"><Clock3 aria-hidden="true" /> Setting today’s table…</div> : null}
          {catalog.status === "error" ? <div className="home-menu-error">The live menu is temporarily unavailable. <Link to="/menu">Try the full menu</Link> once the local service is ready.</div> : null}
          {featuredItems.length ? <div className="customer-menu-grid home-customer-menu-grid">{featuredItems.map((item) => <CustomerMenuCard canReview={eligibleReviewMenuItemSlugs.has(item.slug)} key={item.id} item={item} preparationMinutes={preparationMinutes} />)}</div> : null}
          <Link className="home-menu-link" to="/menu">Browse the full menu <ArrowRight aria-hidden="true" /></Link>
        </section>

        <section className="promotion-panel" aria-labelledby="promotion-title"><img src={imageSource(featuredContent, seasonalSpreadImage) ?? seasonalSpreadImage} alt={imageAlt(featuredContent, "Vegetable flatbread, citrus salad, and whipped feta on a warm cream table")} /><div><p className="eyebrow">From the kitchen</p><h2 id="promotion-title">{featuredContent?.heading ?? "A good meal starts with one clear choice."}</h2><p>{featuredContent?.supporting_copy ?? "Open the live menu to compare ingredients, allergen notes, availability, and the dishes that belong alongside each other."}</p><Link className="nosh-button" data-size="default" data-variant="secondary" to={featuredDestination}>See the dish <ArrowRight aria-hidden="true" /></Link></div></section>

        <section className="landing-section kitchen-section" id="kitchen" aria-labelledby="kitchen-title"><div className="kitchen-story"><p className="eyebrow">A kitchen with a point of view</p><h2 id="kitchen-title">{kitchenContent?.heading ?? "The less a dish travels, the more it feels like dinner."}</h2><p>{kitchenContent?.supporting_copy ?? "Nosh is designed around a small, legible handoff: food starts in one kitchen, moves through one ordering flow, and reaches one local table."}</p><Link className="quiet-link" to="/locations">Find the kitchen <MapPin aria-hidden="true" /></Link></div><img className="kitchen-section-image" src={imageSource(kitchenContent, seasonalSpreadImage) ?? seasonalSpreadImage} alt={imageAlt(kitchenContent, "Citrus and fennel salad with herbs and pistachios in a ceramic bowl")} /><ol className="kitchen-moments">{kitchenMoments.map((moment) => <li key={moment.time}><time>{moment.time}</time><span>{moment.label}</span></li>)}</ol></section>

        <section className="benefits-section" aria-label="Nosh principles">{customerBenefits.map((benefit, index) => <article key={benefit.title}><span>0{index + 1}</span><h2>{benefit.title}</h2><p>{benefit.copy}</p></article>)}</section>

        <section className="location-section" id="location" aria-labelledby="location-title"><div><p className="eyebrow">One place to find us</p><h2 id="location-title">{locationContent?.heading ?? "Nosh on Market Street."}</h2><p>{locationContent?.supporting_copy ?? "12 Market Street · Tuesday to Sunday · 12:00–21:30"}</p></div><img className="location-section-image" src={imageSource(locationContent, seasonalSpreadImage) ?? seasonalSpreadImage} alt={imageAlt(locationContent, "A warm cream table set with grilled citrus and an olive branch")} /><div className="location-actions"><span><Truck aria-hidden="true" /> Service details stay visible before ordering</span><Link className="nosh-button" data-size="default" data-variant="primary" to="/menu">Browse menu <ArrowRight aria-hidden="true" /></Link></div></section>
      </main>
      <CustomerSiteFooter />
      <span className={`api-status api-status-${apiStatus} home-api-status`} aria-live="polite"><span aria-hidden="true" />{apiStatusLabel}</span>
    </div>
  );
}

export default App;
