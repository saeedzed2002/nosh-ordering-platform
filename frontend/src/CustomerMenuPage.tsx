import {
  ArrowLeft,
  ArrowRight,
  ChevronRight,
  CircleAlert,
  Clock3,
  Leaf,
  Heart,
  LoaderCircle,
  Search,
  ShieldCheck,
  ShoppingBag,
  SlidersHorizontal,
  UtensilsCrossed,
  X,
} from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useState, useTransition } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { Button } from "./components/ui/Button";
import { QuantityStepper } from "./components/ui/QuantityStepper";
import { CustomerCartDrawer, useCustomerCart } from "./customerCart";
import { useCustomerAccount } from "./customerAccount";
import {
  availabilityLabel,
  customerMediaUrl,
  formatCustomerPrice,
  type CustomerAllergen,
  type CustomerMenuItem,
  type CustomerMedia,
  useCustomerCatalog,
  useCustomerMenuItem,
} from "./customerCatalog";
import { customerCartLineId, previewCustomerPrice, selectedOptionIds, selectionIssues, type CustomerSelections } from "./customerOrder";

type MenuSort = "curated" | "price-low" | "price-high" | "name";

const menuSortLabels: Record<MenuSort, string> = {
  curated: "Kitchen order",
  "price-low": "Price: low to high",
  "price-high": "Price: high to low",
  name: "Name: A to Z",
};

const emptyMenuItems: CustomerMenuItem[] = [];

function joinClasses(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

function readListParameter(value: string | null): string[] {
  return value ? value.split(",").filter(Boolean) : [];
}

function uniqueValues(values: string[]): string[] {
  return [...new Set(values)].sort((left, right) => left.localeCompare(right));
}

function customerMenuPath(slug: string): string {
  return `/menu/${slug}`;
}

export function CustomerSiteHeader() {
  const { cartCount, openCart } = useCustomerCart();
  const { ready, session } = useCustomerAccount();
  return (
    <header className="site-header customer-site-header">
      <Link className="wordmark" to="/" aria-label="Nosh home">Nosh<span>.</span></Link>
      <nav aria-label="Primary navigation">
        <ul className="navigation-list">
          <li><Link to="/menu">Menu</Link></li>
          <li><Link to="/about">About</Link></li>
          <li><Link to="/locations">Locations</Link></li>
        </ul>
      </nav>
      <div className="customer-header-actions">
        {ready ? <Link className="header-account-link" to={session ? "/account" : "/account/sign-in"}>{session ? session.user.display_name.split(" ")[0] : "Account"}</Link> : null}
        <Button className="header-cart-button" size="compact" variant="secondary" onClick={openCart}>
          <ShoppingBag aria-hidden="true" /> Cart <span aria-label={`${cartCount} items in cart`}>{cartCount}</span>
        </Button>
        <Link className="nosh-button header-order-button" data-size="default" data-variant="primary" to="/menu">
          View menu <ArrowRight aria-hidden="true" />
        </Link>
      </div>
      <CustomerCartDrawer />
    </header>
  );
}

export function CustomerSiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-wordmark">Nosh<span>.</span></div>
      <div><p>Local food, set at a human pace.</p></div>
      <div className="footer-links">
        <Link to="/menu">Menu</Link>
        <Link to="/about">About</Link>
        <Link to="/locations">Locations</Link>
      </div>
    </footer>
  );
}

function AvailabilityBadge({ item }: { item: CustomerMenuItem }) {
  const available = item.availability === "available";
  return (
    <span className={joinClasses("customer-availability", available ? "available" : "unavailable")}>
      <i aria-hidden="true" />
      {availabilityLabel(item.availability)}
    </span>
  );
}

function CustomerImage({
  alt,
  className,
  media,
}: {
  alt: string;
  className?: string;
  media: CustomerMedia | null;
}) {
  const source = customerMediaUrl(media);
  if (!source) {
    return <div aria-label="Dish image not available" className={joinClasses("customer-media-fallback", className)}>Image coming soon</div>;
  }
  return <img alt={alt} className={className} loading="lazy" src={source} />;
}

export function CustomerMenuCard({
  item,
  preparationMinutes,
}: {
  item: CustomerMenuItem;
  preparationMinutes: number | null;
}) {
  const tags = item.dietary_tags.slice(0, 3);
  return (
    <article className="customer-menu-card" data-availability={item.availability}>
      <Link className="customer-menu-card-image" to={customerMenuPath(item.slug)} aria-label={`Read details for ${item.name}`}>
        <CustomerImage alt={item.media?.alt_text ?? item.name} media={item.media} />
        <AvailabilityBadge item={item} />
      </Link>
      <div className="customer-menu-card-content">
        <p className="customer-menu-card-category">{item.category.name}</p>
        <div className="customer-menu-card-heading">
          <h2><Link to={customerMenuPath(item.slug)}>{item.name}</Link></h2>
          <strong>{formatCustomerPrice(item.final_price_minor, item.currency_code)}</strong>
        </div>
        <p className="customer-menu-card-description">{item.description}</p>
        <div className="customer-menu-card-meta">
          {tags.map((tag) => <span key={tag}>{tag}</span>)}
          {preparationMinutes ? <small><Clock3 aria-hidden="true" /> About {preparationMinutes} min</small> : null}
        </div>
        <Link className="customer-menu-card-link" to={customerMenuPath(item.slug)}>
          {item.availability === "available" ? "View dish" : "View availability"} <ChevronRight aria-hidden="true" />
        </Link>
      </div>
    </article>
  );
}

function MenuSkeleton() {
  return (
    <div className="customer-menu-grid customer-menu-grid-skeleton" aria-label="Loading menu" aria-live="polite">
      {Array.from({ length: 8 }, (_, index) => <div key={index} className="customer-menu-skeleton"><i /><span /><strong /><small /></div>)}
    </div>
  );
}

function MenuLoadFailure({ onRetry }: { onRetry: () => void }) {
  return (
    <section className="customer-menu-feedback" role="alert">
      <CircleAlert aria-hidden="true" />
      <div><h2>Today’s menu could not load.</h2><p>The kitchen catalogue is not responding. Check the local service, then try again.</p></div>
      <Button variant="secondary" onClick={onRetry}>Try again</Button>
    </section>
  );
}

function dietaryOptions(items: CustomerMenuItem[]): string[] {
  return uniqueValues(items.flatMap((item) => item.dietary_tags));
}

function allergenOptions(items: CustomerMenuItem[]): CustomerAllergen[] {
  const known = new Map<string, CustomerAllergen>();
  for (const item of items) {
    for (const allergen of item.allergens) {
      known.set(allergen.slug, allergen);
    }
  }
  return [...known.values()].sort((left, right) => left.name.localeCompare(right.name));
}

function filterItems(
  items: CustomerMenuItem[],
  filters: {
    allergenSlugs: Set<string>;
    availability: string;
    category: string;
    dietaryTags: Set<string>;
    query: string;
    sort: MenuSort;
  },
): CustomerMenuItem[] {
  const query = filters.query.trim().toLocaleLowerCase();
  const visible = items.filter((item) => {
    const text = [item.name, item.description, ...item.ingredients, ...item.dietary_tags]
      .join(" ")
      .toLocaleLowerCase();
    return (
      (!query || text.includes(query)) &&
      (!filters.category || item.category.slug === filters.category) &&
      (!filters.availability || item.availability === "available") &&
      [...filters.dietaryTags].every((tag) => item.dietary_tags.includes(tag)) &&
      !item.allergens.some((allergen) => filters.allergenSlugs.has(allergen.slug))
    );
  });

  if (filters.sort === "price-low") {
    return [...visible].sort((left, right) => left.final_price_minor - right.final_price_minor);
  }
  if (filters.sort === "price-high") {
    return [...visible].sort((left, right) => right.final_price_minor - left.final_price_minor);
  }
  if (filters.sort === "name") {
    return [...visible].sort((left, right) => left.name.localeCompare(right.name));
  }
  return visible;
}

export function CustomerMenuPage() {
  const { data: snapshot, retry, status } = useCustomerCatalog();
  const [searchParams, setSearchParams] = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const query = searchParams.get("q") ?? "";
  const deferredQuery = useDeferredValue(query);
  const category = searchParams.get("category") ?? "";
  const availability = searchParams.get("available") ?? "";
  const sort = (searchParams.get("sort") as MenuSort | null) ?? "curated";
  const dietaryTags = useMemo(() => new Set(readListParameter(searchParams.get("dietary"))), [searchParams]);
  const allergenSlugs = useMemo(() => new Set(readListParameter(searchParams.get("avoid"))), [searchParams]);

  const updateParameters = (updates: Record<string, string | null>) => {
    startTransition(() => {
      const next = new URLSearchParams(searchParams);
      for (const [key, value] of Object.entries(updates)) {
        if (value) {
          next.set(key, value);
        } else {
          next.delete(key);
        }
      }
      setSearchParams(next, { replace: true });
    });
  };

  const toggleListParameter = (key: "dietary" | "avoid", value: string) => {
    const current = readListParameter(searchParams.get(key));
    const next = current.includes(value)
      ? current.filter((entry) => entry !== value)
      : [...current, value];
    updateParameters({ [key]: uniqueValues(next).join(",") || null });
  };

  const items = snapshot?.items ?? emptyMenuItems;
  const categories = useMemo(
    () => [...new Map(items.map((item) => [item.category.slug, item.category])).values()],
    [items],
  );
  const visibleItems = useMemo(
    () => filterItems(items, { allergenSlugs, availability, category, dietaryTags, query: deferredQuery, sort }),
    [allergenSlugs, availability, category, deferredQuery, dietaryTags, items, sort],
  );
  const hasFilters = Boolean(query || category || availability || dietaryTags.size || allergenSlugs.size || sort !== "curated");
  const preparationMinutes = snapshot?.location?.preparation_minutes ?? null;

  return (
    <div className="app-shell customer-menu-page">
      <a className="skip-link" href="#menu-results">Skip to menu results</a>
      <CustomerSiteHeader />
      <main>
        <header className="customer-menu-hero">
          <div>
            <p className="eyebrow"><UtensilsCrossed aria-hidden="true" /> Today’s menu</p>
            <h1>Find what fits the table.</h1>
            <p>Search the live kitchen board by appetite, dietary preference, and what you need to avoid. Availability is shown before the next decision.</p>
          </div>
          <div className="customer-menu-hero-note"><Clock3 aria-hidden="true" /><span>{preparationMinutes ? `About ${preparationMinutes} minutes from the kitchen` : "Service timing appears with the live menu"}</span></div>
        </header>

        {status === "error" ? <MenuLoadFailure onRetry={retry} /> : null}
        {status === "loading" && !snapshot ? <MenuSkeleton /> : null}

        {snapshot ? (
          <section className="customer-menu-workspace" aria-label="Browse today’s menu">
            <aside className="customer-menu-filters">
              <div className="customer-filter-heading"><SlidersHorizontal aria-hidden="true" /><div><p>Refine the menu</p><span>Filters stay in this page link.</span></div></div>
              <label className="customer-menu-search"><Search aria-hidden="true" /><span className="sr-only">Search menu</span><input value={query} onChange={(event) => updateParameters({ q: event.target.value || null })} placeholder="Search dishes or ingredients" type="search" /></label>
              <fieldset><legend>Category</legend><div className="customer-filter-chips"><button className={!category ? "selected" : undefined} type="button" aria-pressed={!category} onClick={() => updateParameters({ category: null })}>Everything</button>{categories.map((entry) => <button key={entry.id} className={category === entry.slug ? "selected" : undefined} type="button" aria-pressed={category === entry.slug} onClick={() => updateParameters({ category: entry.slug })}>{entry.name}</button>)}</div></fieldset>
              <fieldset><legend>Dietary preferences</legend><div className="customer-filter-chips">{dietaryOptions(items).map((tag) => <button key={tag} className={dietaryTags.has(tag) ? "selected" : undefined} type="button" aria-pressed={dietaryTags.has(tag)} onClick={() => toggleListParameter("dietary", tag)}><Leaf aria-hidden="true" />{tag}</button>)}</div></fieldset>
              <fieldset><legend>Avoid allergens</legend><div className="customer-filter-chips">{allergenOptions(items).map((allergen) => <button key={allergen.slug} className={allergenSlugs.has(allergen.slug) ? "selected" : undefined} type="button" aria-pressed={allergenSlugs.has(allergen.slug)} onClick={() => toggleListParameter("avoid", allergen.slug)}><ShieldCheck aria-hidden="true" />{allergen.name}</button>)}</div></fieldset>
              <label className="customer-availability-filter"><input checked={availability === "available"} type="checkbox" onChange={(event) => updateParameters({ available: event.target.checked ? "available" : null })} /> Show available dishes only</label>
              {hasFilters ? <Button size="compact" variant="quiet" onClick={() => setSearchParams({}, { replace: true })}><X aria-hidden="true" /> Clear filters</Button> : null}
            </aside>

            <section className={joinClasses("customer-menu-results", isPending && "pending")} id="menu-results" aria-live="polite">
              <header className="customer-menu-results-heading">
                <div><p className="eyebrow">Kitchen board</p><h2>{visibleItems.length} {visibleItems.length === 1 ? "dish" : "dishes"}</h2></div>
                <label>Sort menu<select value={sort} onChange={(event) => updateParameters({ sort: event.target.value === "curated" ? null : event.target.value })}>{(Object.keys(menuSortLabels) as MenuSort[]).map((option) => <option key={option} value={option}>{menuSortLabels[option]}</option>)}</select></label>
              </header>
              {visibleItems.length ? <div className="customer-menu-grid">{visibleItems.map((item) => <CustomerMenuCard key={item.id} item={item} preparationMinutes={preparationMinutes} />)}</div> : <section className="customer-menu-empty"><Search aria-hidden="true" /><h2>Nothing matches those choices.</h2><p>Try clearing a dietary, allergen, or availability filter to see more of today’s menu.</p><Button variant="secondary" onClick={() => setSearchParams({}, { replace: true })}>Clear filters</Button></section>}
            </section>
          </section>
        ) : null}
      </main>
      <CustomerSiteFooter />
    </div>
  );
}

function RelatedDishes({ items, preparationMinutes }: { items: CustomerMenuItem[]; preparationMinutes: number | null }) {
  if (!items.length) {
    return null;
  }
  return <section className="customer-related-dishes" aria-labelledby="related-dishes-title"><div className="customer-section-heading"><p className="eyebrow">Keep the table moving</p><h2 id="related-dishes-title">You might also like</h2></div><div className="customer-menu-grid">{items.map((item) => <CustomerMenuCard key={item.id} item={item} preparationMinutes={preparationMinutes} />)}</div></section>;
}

function CustomerDishOrderPanel({ item }: { item: CustomerMenuItem }) {
  const { addLine, isUpdating } = useCustomerCart();
  const { ready, request, session } = useCustomerAccount();
  const location = useLocation();
  const navigate = useNavigate();
  const [selections, setSelections] = useState<CustomerSelections>({});
  const [quantity, setQuantity] = useState(1);
  const [note, setNote] = useState("");
  const [formIssues, setFormIssues] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isFavorite, setIsFavorite] = useState(false);
  const [favoriteError, setFavoriteError] = useState<string | null>(null);
  const [favoriteUpdating, setFavoriteUpdating] = useState(false);
  const available = item.availability === "available";
  const previewPrice = previewCustomerPrice(item, selections);

  useEffect(() => {
    if (!session) {
      setIsFavorite(false);
      return;
    }
    const controller = new AbortController();
    void request<Array<{ slug: string }>>("/api/v1/account/favorites", { signal: controller.signal })
      .then((favorites) => { if (!controller.signal.aborted) setIsFavorite(favorites.some((favorite) => favorite.slug === item.slug)); })
      .catch(() => { if (!controller.signal.aborted) setFavoriteError("Your saved dishes could not be checked."); });
    return () => controller.abort();
  }, [item.slug, request, session]);

  const toggleFavorite = async () => {
    if (!session) {
      navigate("/account/sign-in", { state: { from: location } });
      return;
    }
    setFavoriteError(null);
    setFavoriteUpdating(true);
    try {
      if (isFavorite) {
        await request<void>(`/api/v1/account/favorites/${item.slug}`, { method: "DELETE" });
      } else {
        await request(`/api/v1/account/favorites/${item.slug}`, { method: "PUT" });
      }
      setIsFavorite((current) => !current);
    } catch (requestError) {
      setFavoriteError(requestError instanceof Error ? requestError.message : "This dish could not be saved.");
    } finally {
      setFavoriteUpdating(false);
    }
  };

  const toggleOption = (groupId: string, optionId: string, maximumSelections: number, forceSelection: boolean) => {
    setFormIssues((current) => ({ ...current, [groupId]: "" }));
    setSelections((current) => {
      const selected = current[groupId] ?? [];
      if (forceSelection) {
        return { ...current, [groupId]: [optionId] };
      }
      if (selected.includes(optionId)) {
        return { ...current, [groupId]: selected.filter((selectedId) => selectedId !== optionId) };
      }
      if (selected.length >= maximumSelections) {
        setFormIssues((issues) => ({ ...issues, [groupId]: `Choose no more than ${maximumSelections} options.` }));
        return current;
      }
      return { ...current, [groupId]: [...selected, optionId] };
    });
  };

  const addToCart = async () => {
    const nextIssues = selectionIssues(item, selections);
    if (Object.keys(nextIssues).length) {
      setFormIssues(nextIssues);
      return;
    }
    setFormIssues({});
    setSubmitError(null);
    try {
      await addLine({
        client_line_id: customerCartLineId(),
        menu_item_slug: item.slug,
        note: note.trim() || null,
        option_ids: selectedOptionIds(selections),
        quantity,
      });
      setSelections({});
      setQuantity(1);
      setNote("");
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "This dish could not be added to the cart.");
    }
  };

  return (
    <section className="customer-dish-options" aria-labelledby="dish-options-title">
      <div className="customer-section-heading"><p className="eyebrow">Made your way</p><h2 id="dish-options-title">Choices available with this dish</h2><p>{available ? "Choose what works for you. The kitchen checks every choice and the final total before the dish reaches your cart." : "The kitchen has this dish paused. Its choices are shown here, but it cannot be added to an order."}</p></div>
      <div className="customer-order-workspace">
        <form className="customer-order-form" onSubmit={(event) => { event.preventDefault(); void addToCart(); }}>
          {item.option_groups.map((group) => {
            const selected = selections[group.id] ?? [];
            const isSingleRequiredChoice = group.kind === "choice" && group.minimum_selections === 1 && group.maximum_selections === 1;
            const issue = formIssues[group.id];
            return <fieldset key={group.id} aria-invalid={issue ? true : undefined} disabled={!available || isUpdating}>
              <legend>{group.name} {group.minimum_selections ? <em>Required</em> : <em>Optional</em>}</legend>
              <p>{group.minimum_selections ? `Choose at least ${group.minimum_selections}` : "Choose any if you like"}{group.maximum_selections > 1 ? ` · up to ${group.maximum_selections}` : ""}</p>
              <div className="customer-order-options">
                {group.options.map((option) => {
                  const isSelected = selected.includes(option.id);
                  return <label key={option.id} className={isSelected ? "selected" : undefined}>
                    <input checked={isSelected} name={group.id} type={isSingleRequiredChoice ? "radio" : "checkbox"} value={option.id} onChange={() => toggleOption(group.id, option.id, group.maximum_selections, isSingleRequiredChoice)} />
                    <span><strong>{option.name}</strong><small>{option.price_delta_minor ? `+${formatCustomerPrice(option.price_delta_minor, item.currency_code)}` : "Included"}</small></span>
                  </label>;
                })}
              </div>
              {issue ? <small className="customer-order-issue" role="alert">{issue}</small> : null}
            </fieldset>;
          })}
          <label className="customer-order-note">A note for the kitchen<textarea disabled={!available || isUpdating} maxLength={500} placeholder="Optional: anything the kitchen should know?" value={note} onChange={(event) => setNote(event.target.value)} /></label>
          {submitError ? <p className="customer-order-issue" role="alert">{submitError}</p> : null}
        </form>
        <aside className="customer-order-summary" aria-live="polite">
          <span>Current selection</span>
          <strong>{formatCustomerPrice(previewPrice * quantity, item.currency_code)}</strong>
          <small>{quantity > 1 ? `${formatCustomerPrice(previewPrice, item.currency_code)} each` : "Price updates as you make choices"}</small>
          <div><span>Quantity</span><QuantityStepper disabled={!available || isUpdating} max={20} value={quantity} onValueChange={setQuantity} /></div>
          <Button disabled={!available || isUpdating} loading={isUpdating} onClick={() => void addToCart()}>{available ? "Add to cart" : "Unavailable today"} <ShoppingBag aria-hidden="true" /></Button>
          <Button disabled={!ready || favoriteUpdating} loading={favoriteUpdating} variant="secondary" onClick={() => void toggleFavorite()}><Heart aria-hidden="true" fill={isFavorite ? "currentColor" : "none"} /> {isFavorite ? "Saved to favorites" : "Save to favorites"}</Button>
          {favoriteError ? <p className="customer-order-issue" role="alert">{favoriteError}</p> : null}
          <p>{available ? "The total is confirmed by the kitchen before this is saved in your cart." : "Check back when the kitchen makes this dish available again."}</p>
        </aside>
      </div>
    </section>
  );
}

export function CustomerMenuItemPage() {
  const { slug } = useParams();
  const itemResource = useCustomerMenuItem(slug);
  const catalogResource = useCustomerCatalog();
  const item = itemResource.data?.item;
  const location = itemResource.data?.location ?? catalogResource.data?.location ?? null;
  const relatedItems = useMemo(() => {
    if (!item || !catalogResource.data) {
      return [];
    }
    const categoryMatches = catalogResource.data.items.filter(
      (candidate) => candidate.id !== item.id && candidate.category.id === item.category.id,
    );
    const sharedTagMatches = catalogResource.data.items.filter(
      (candidate) => candidate.id !== item.id && candidate.category.id !== item.category.id && candidate.dietary_tags.some((tag) => item.dietary_tags.includes(tag)),
    );
    return [...categoryMatches, ...sharedTagMatches].slice(0, 3);
  }, [catalogResource.data, item]);
  const categoryImage = item?.category.media && item.category.media.id !== item.media?.id ? item.category.media : null;

  return (
    <div className="app-shell customer-dish-page">
      <a className="skip-link" href="#dish-content">Skip to dish details</a>
      <CustomerSiteHeader />
      <main id="dish-content">
        {itemResource.status === "loading" ? <section className="customer-detail-loading"><LoaderCircle aria-hidden="true" /><p>Opening dish details…</p></section> : null}
        {itemResource.status === "error" ? <section className="customer-menu-feedback" role="alert"><CircleAlert aria-hidden="true" /><div><h1>This dish is not on the current menu.</h1><p>It may be private, unavailable from this kitchen, or no longer published.</p></div><Link className="nosh-button" data-size="default" data-variant="secondary" to="/menu"><ArrowLeft aria-hidden="true" /> Back to menu</Link></section> : null}
        {item ? <>
          <section className="customer-dish-hero">
            <div className="customer-dish-hero-copy">
              <Link className="customer-back-link" to="/menu"><ArrowLeft aria-hidden="true" /> Back to menu</Link>
              <p className="eyebrow">{item.category.name}</p>
              <h1>{item.name}</h1>
              <p>{item.description}</p>
              <div className="customer-dish-hero-meta"><AvailabilityBadge item={item} /><strong>{formatCustomerPrice(item.final_price_minor, item.currency_code)}</strong>{location ? <span><Clock3 aria-hidden="true" /> About {location.preparation_minutes} min</span> : null}</div>
              {item.availability !== "available" ? <p className="customer-unavailable-note">This dish can be viewed, but it cannot be added to an order while the kitchen has it paused.</p> : <p className="customer-detail-boundary">Choose options, quantity, and a kitchen note below. The live menu confirms the final total before the dish reaches your cart.</p>}
            </div>
            <section className="customer-dish-gallery" aria-label="Dish image gallery">
              <figure><CustomerImage alt={item.media?.alt_text ?? item.name} media={item.media} /><figcaption>Dish image</figcaption></figure>
              {categoryImage ? <figure className="customer-dish-gallery-category"><CustomerImage alt={categoryImage.alt_text} media={categoryImage} /><figcaption>From {item.category.name}</figcaption></figure> : null}
            </section>
          </section>

          <section className="customer-dish-details">
            <div className="customer-dish-copy"><p className="eyebrow">What to know</p><h2>Clear before you choose.</h2><section><h3>Ingredients</h3><p>{item.ingredients.length ? item.ingredients.join(", ") : "Ingredients are being prepared for this dish."}</p></section><section><h3>Dietary notes</h3>{item.dietary_tags.length ? <ul className="customer-detail-tags">{item.dietary_tags.map((tag) => <li key={tag}>{tag}</li>)}</ul> : <p>No dietary tags have been published for this dish.</p>}</section><section><h3>Allergen information</h3>{item.allergens.length ? <ul className="customer-allergen-list">{item.allergens.map((allergen) => <li key={allergen.slug}><ShieldCheck aria-hidden="true" /><span><strong>{allergen.name}</strong>{allergen.note ? <small>{allergen.note}</small> : null}</span></li>)}</ul> : <p>No allergen notes have been published for this dish.</p>}</section></div>
            <aside className="customer-dish-facts"><div><span>Kitchen time</span><strong>{location ? `About ${location.preparation_minutes} min` : "Shown at checkout"}</strong></div><div><span>Nutrition</span><strong>Not published yet</strong><p>Nutrition facts appear here when the kitchen supplies them.</p></div><div><span>Availability</span><strong>{availabilityLabel(item.availability)}</strong></div></aside>
          </section>

          <CustomerDishOrderPanel key={item.id} item={item} />
          <RelatedDishes items={relatedItems} preparationMinutes={location?.preparation_minutes ?? null} />
        </> : null}
      </main>
      <CustomerSiteFooter />
    </div>
  );
}
