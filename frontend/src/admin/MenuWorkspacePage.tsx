import {
  ArrowRight,
  CheckCircle2,
  ChefHat,
  CirclePause,
  Eye,
  LoaderCircle,
  PackagePlus,
  Search,
  Sparkles,
  Undo2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { ApiError } from "./api";
import {
  type AvailabilityState,
  type Category,
  type CuratedCollection,
  type MenuItem,
  type MenuSetup,
  type PublicationState,
  formatPrice,
  slugFromName,
} from "./menuTypes";
import { ProtectedMediaImage } from "./ProtectedMediaImage";
import { useAdminSession } from "./session";

type CollectionDraft = {
  id: string | null;
  name: string;
  slug: string;
  description: string;
  display_order: number;
  publication_state: PublicationState;
  menu_item_ids: string[];
};

function newCollectionDraft(): CollectionDraft {
  return {
    id: null,
    name: "",
    slug: "",
    description: "",
    display_order: 0,
    publication_state: "draft",
    menu_item_ids: [],
  };
}

function collectionDraftFrom(collection: CuratedCollection): CollectionDraft {
  return {
    id: collection.id,
    name: collection.name,
    slug: collection.slug,
    description: collection.description,
    display_order: collection.display_order,
    publication_state: collection.publication_state,
    menu_item_ids: collection.menu_item_ids,
  };
}

function availabilityLabel(state: AvailabilityState): string {
  if (state === "temporarily_unavailable") {
    return "Paused";
  }
  if (state === "scheduled") {
    return "Scheduled";
  }
  return "Available";
}

function availabilityClass(state: AvailabilityState): string {
  return state === "available" ? "available" : "paused";
}

export function MenuWorkspacePage() {
  const { request } = useAdminSession();
  const [setup, setSetup] = useState<MenuSetup | null>(null);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [visibilityFilter, setVisibilityFilter] = useState<"all" | PublicationState>("all");
  const [availabilityFilter, setAvailabilityFilter] = useState<"all" | AvailabilityState>("all");
  const [busySlug, setBusySlug] = useState<string | null>(null);
  const [featuredId, setFeaturedId] = useState<string>("");
  const [savingFeatured, setSavingFeatured] = useState(false);
  const [savingCategoryId, setSavingCategoryId] = useState<string | null>(null);
  const [collectionDraft, setCollectionDraft] = useState<CollectionDraft>(newCollectionDraft);
  const [savingCollection, setSavingCollection] = useState(false);

  useEffect(() => {
    let active = true;

    void Promise.all([
      request<MenuSetup>("/api/v1/admin/menu/setup"),
      request<MenuItem[]>("/api/v1/admin/menu"),
    ])
      .then(([nextSetup, nextItems]) => {
        if (!active) {
          return;
        }
        setSetup(nextSetup);
        setItems(nextItems);
        setFeaturedId(nextSetup.featured.menu_item_id ?? "");
      })
      .catch((reason) => {
        if (active) {
          setError(
            reason instanceof ApiError
              ? reason.message
              : "The local menu desk is unavailable.",
          );
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [request]);

  const visibleItems = useMemo(() => {
    const phrase = search.trim().toLocaleLowerCase();
    return items.filter((item) => {
      const matchesSearch = !phrase || `${item.name} ${item.description}`.toLocaleLowerCase().includes(phrase);
      const matchesCategory = categoryFilter === "all" || item.category.id === categoryFilter;
      const matchesVisibility = visibilityFilter === "all" || item.publication_state === visibilityFilter;
      const matchesAvailability =
        availabilityFilter === "all" || item.availability.state === availabilityFilter;
      return matchesSearch && matchesCategory && matchesVisibility && matchesAvailability;
    });
  }, [availabilityFilter, categoryFilter, items, search, visibilityFilter]);

  const publishedItems = useMemo(
    () => items.filter((item) => item.publication_state === "published"),
    [items],
  );

  async function updateAvailability(item: MenuItem) {
    const nextState: AvailabilityState =
      item.availability.state === "temporarily_unavailable"
        ? "available"
        : "temporarily_unavailable";
    setBusySlug(item.slug);
    setError(null);
    setNotice(null);
    try {
      const updated = await request<MenuItem>(`/api/v1/admin/menu/${item.slug}/availability`, {
        method: "PATCH",
        body: JSON.stringify({
          location_id: item.availability.location_id,
          state: nextState,
        }),
      });
      setItems((allItems) => allItems.map((entry) => (entry.id === updated.id ? updated : entry)));
      setNotice(nextState === "available" ? `${item.name} is available again.` : `${item.name} is paused.`);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Availability could not be changed.");
    } finally {
      setBusySlug(null);
    }
  }

  async function saveFeatured() {
    setSavingFeatured(true);
    setError(null);
    setNotice(null);
    try {
      const featured = await request<MenuSetup["featured"]>("/api/v1/admin/menu/featured", {
        method: "PUT",
        body: JSON.stringify({ menu_item_id: featuredId || null }),
      });
      setSetup((current) => (current ? { ...current, featured } : current));
      setNotice(featured.menu_item_name ? `${featured.menu_item_name} is now featured.` : "Featured placement cleared.");
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Featured placement could not be saved.");
    } finally {
      setSavingFeatured(false);
    }
  }

  async function toggleCategory(category: Category) {
    setSavingCategoryId(category.id);
    setError(null);
    setNotice(null);
    try {
      const updated = await request<Category>(`/api/v1/admin/menu/categories/${category.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: category.name,
          slug: category.slug,
          description: category.description,
          media_id: category.media?.id ?? null,
          display_order: category.display_order,
          is_published: !category.is_published,
        }),
      });
      setSetup((current) =>
        current
          ? {
              ...current,
              categories: current.categories.map((entry) =>
                entry.id === updated.id ? updated : entry,
              ),
            }
          : current,
      );
      setNotice(
        updated.is_published
          ? `${updated.name} is visible to customers again.`
          : `${updated.name} is safely hidden from customers.`,
      );
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Category visibility could not be changed.");
    } finally {
      setSavingCategoryId(null);
    }
  }

  function selectCollection(value: string) {
    const selected = setup?.collections.find((collection) => collection.id === value);
    setCollectionDraft(selected ? collectionDraftFrom(selected) : newCollectionDraft());
  }

  function toggleCollectionItem(itemId: string) {
    setCollectionDraft((current) => ({
      ...current,
      menu_item_ids: current.menu_item_ids.includes(itemId)
        ? current.menu_item_ids.filter((id) => id !== itemId)
        : [...current.menu_item_ids, itemId],
    }));
  }

  async function saveCollection() {
    if (!collectionDraft.name.trim() || !collectionDraft.description.trim()) {
      setError("Give the collection a name and a short customer-facing description.");
      return;
    }
    const slug = collectionDraft.slug || slugFromName(collectionDraft.name);
    if (!slug) {
      setError("Give the collection a URL name using letters, numbers, and dashes.");
      return;
    }
    setSavingCollection(true);
    setError(null);
    setNotice(null);
    const payload = { ...collectionDraft, slug };
    try {
      const saved = await request<CuratedCollection>(
        collectionDraft.id
          ? `/api/v1/admin/menu/collections/${collectionDraft.id}`
          : "/api/v1/admin/menu/collections",
        {
          method: collectionDraft.id ? "PUT" : "POST",
          body: JSON.stringify(payload),
        },
      );
      setSetup((current) => {
        if (!current) {
          return current;
        }
        const exists = current.collections.some((collection) => collection.id === saved.id);
        return {
          ...current,
          collections: exists
            ? current.collections.map((collection) => (collection.id === saved.id ? saved : collection))
            : [...current.collections, saved],
        };
      });
      setCollectionDraft(collectionDraftFrom(saved));
      setNotice(`${saved.name} has been saved.`);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Collection could not be saved.");
    } finally {
      setSavingCollection(false);
    }
  }

  if (loading) {
    return <div className="admin-inline-loading"><LoaderCircle aria-hidden="true" /> Opening the menu desk…</div>;
  }

  if (!setup) {
    return <div className="admin-empty-state">Menu references are unavailable.</div>;
  }

  return (
    <div className="admin-menu-workspace">
      <header className="admin-page-heading admin-menu-heading">
        <div>
          <p className="admin-kicker">Menu service</p>
          <h1>Keep every plate true to the pass.</h1>
          <p>Search the live board, pause a dish safely, and build the next one in a guided flow.</p>
        </div>
        <Link className="nosh-button admin-menu-create" data-variant="primary" data-size="default" to="/admin/menu/new">
          <PackagePlus aria-hidden="true" /> Add a food item
        </Link>
      </header>

      {error ? <p className="admin-form-error" role="alert">{error}</p> : null}
      {notice ? <p className="admin-form-notice" role="status">{notice}</p> : null}

      <section className="admin-menu-filter-bar" aria-label="Filter the menu board">
        <label className="admin-menu-search">
          <Search aria-hidden="true" />
          <span className="sr-only">Search food items</span>
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search dishes" type="search" />
        </label>
        <label>
          <span>Category</span>
          <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
            <option value="all">All categories</option>
            {setup.categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
        </label>
        <label>
          <span>Visibility</span>
          <select value={visibilityFilter} onChange={(event) => setVisibilityFilter(event.target.value as "all" | PublicationState)}>
            <option value="all">All visibility</option>
            <option value="published">Customer live</option>
            <option value="draft">Private draft</option>
          </select>
        </label>
        <label>
          <span>Service</span>
          <select value={availabilityFilter} onChange={(event) => setAvailabilityFilter(event.target.value as "all" | AvailabilityState)}>
            <option value="all">All service states</option>
            <option value="available">Available</option>
            <option value="temporarily_unavailable">Paused</option>
            <option value="scheduled">Scheduled</option>
          </select>
        </label>
      </section>

      <div className="admin-menu-layout">
        <section className="admin-menu-board" aria-labelledby="menu-board-title">
          <div className="admin-menu-board-heading">
            <div>
              <p className="admin-kicker">Today’s board</p>
              <h2 id="menu-board-title">{visibleItems.length} {visibleItems.length === 1 ? "dish" : "dishes"}</h2>
            </div>
            <span><ChefHat aria-hidden="true" /> Quick changes are recorded.</span>
          </div>
          <div className="admin-menu-card-grid">
            {visibleItems.map((item) => (
              <article key={item.id} className="admin-menu-card">
                <ProtectedMediaImage alt={item.media.alt_text} className="admin-menu-card-image" mediaId={item.media.id} />
                <div className="admin-menu-card-body">
                  <div className="admin-menu-card-meta">
                    <span className={`admin-menu-service-state ${availabilityClass(item.availability.state)}`}>
                      <i aria-hidden="true" /> {availabilityLabel(item.availability.state)}
                    </span>
                    <span className={`admin-state-chip ${item.publication_state}`}>{item.publication_state === "published" ? "Live" : "Draft"}</span>
                  </div>
                  <div className="admin-menu-card-title">
                    <div>
                      <p>{item.category.name}</p>
                      <h3>{item.name}</h3>
                    </div>
                    <strong>{formatPrice(item.final_price_minor, item.currency_code)}</strong>
                  </div>
                  <p className="admin-menu-card-description">{item.description}</p>
                  <div className="admin-menu-card-details">
                    <span>{item.option_groups.length ? `${item.option_groups.length} option groups` : "No options"}</span>
                    <span>{item.allergens.length ? `${item.allergens.length} allergen notes` : "No allergen notes"}</span>
                  </div>
                  <div className="admin-menu-card-actions">
                    <Link to={`/admin/menu/${item.slug}`}>Edit plate <ArrowRight aria-hidden="true" /></Link>
                    <Button loading={busySlug === item.slug} size="compact" variant="quiet" onClick={() => void updateAvailability(item)}>
                      {item.availability.state === "temporarily_unavailable" ? <Undo2 aria-hidden="true" /> : <CirclePause aria-hidden="true" />}
                      {item.availability.state === "temporarily_unavailable" ? "Resume" : "Pause"}
                    </Button>
                  </div>
                </div>
              </article>
            ))}
          </div>
          {visibleItems.length === 0 ? <p className="admin-menu-no-results">No dishes match these filters.</p> : null}
        </section>

        <aside className="admin-menu-sidecar">
          <section className="admin-menu-featured-card" aria-labelledby="featured-menu-title">
            <div className="admin-panel-heading">
              <div>
                <p className="admin-kicker">Home placement</p>
                <h2 id="featured-menu-title">Feature one dish</h2>
              </div>
              <Sparkles aria-hidden="true" />
            </div>
            <p>Only customer-live dishes can take this position. The home copy remains managed in its own desk.</p>
            <select value={featuredId} onChange={(event) => setFeaturedId(event.target.value)}>
              <option value="">No featured dish</option>
              {publishedItems.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <Button loading={savingFeatured} size="compact" onClick={() => void saveFeatured()}><CheckCircle2 aria-hidden="true" /> Save placement</Button>
          </section>

          <section className="admin-menu-category-card" aria-labelledby="category-visibility-title">
            <div className="admin-panel-heading">
              <div>
                <p className="admin-kicker">Categories</p>
                <h2 id="category-visibility-title">Hide, don’t erase</h2>
              </div>
              <Eye aria-hidden="true" />
            </div>
            <p>Hiding a category safely removes its live dishes from the public catalog without deleting their work.</p>
            <ul>
              {setup.categories.map((category) => (
                <li key={category.id}>
                  <div>
                    <strong>{category.name}</strong>
                    <small>{category.menu_item_count} dishes · {category.is_published ? "Customer live" : "Hidden"}</small>
                  </div>
                  <Button loading={savingCategoryId === category.id} size="compact" variant="quiet" onClick={() => void toggleCategory(category)}>
                    {category.is_published ? "Hide" : "Show"}
                  </Button>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>

      <details className="admin-collection-desk">
        <summary>
          <span><Sparkles aria-hidden="true" /> Curated collections</span>
          <small>Group customer-live dishes into a purposeful set.</small>
        </summary>
        <div className="admin-collection-desk-body">
          <div className="admin-collection-picker">
            <label htmlFor="collection-picker">Choose a collection</label>
            <select id="collection-picker" value={collectionDraft.id ?? "new"} onChange={(event) => selectCollection(event.target.value)}>
              <option value="new">New collection</option>
              {setup.collections.map((collection) => <option key={collection.id} value={collection.id}>{collection.name}</option>)}
            </select>
          </div>
          <div className="admin-collection-fields">
            <label>Name<input value={collectionDraft.name} onChange={(event) => setCollectionDraft((current) => ({ ...current, name: event.target.value, slug: current.slug || slugFromName(event.target.value) }))} /></label>
            <label>URL name<input value={collectionDraft.slug} onChange={(event) => setCollectionDraft((current) => ({ ...current, slug: slugFromName(event.target.value) }))} /></label>
            <label>Display order<input min="0" type="number" value={collectionDraft.display_order} onChange={(event) => setCollectionDraft((current) => ({ ...current, display_order: Number(event.target.value) || 0 }))} /></label>
            <label>Visibility<select value={collectionDraft.publication_state} onChange={(event) => setCollectionDraft((current) => ({ ...current, publication_state: event.target.value as PublicationState }))}><option value="draft">Private draft</option><option value="published">Customer live</option></select></label>
          </div>
          <label className="admin-collection-description">Customer-facing introduction<textarea rows={3} value={collectionDraft.description} onChange={(event) => setCollectionDraft((current) => ({ ...current, description: event.target.value }))} /></label>
          <fieldset className="admin-collection-items">
            <legend>Choose dishes</legend>
            {publishedItems.map((item) => (
              <label key={item.id}>
                <input checked={collectionDraft.menu_item_ids.includes(item.id)} type="checkbox" onChange={() => toggleCollectionItem(item.id)} />
                <span>{item.name}</span>
              </label>
            ))}
          </fieldset>
          <Button loading={savingCollection} onClick={() => void saveCollection()}><CheckCircle2 aria-hidden="true" /> Save collection</Button>
        </div>
      </details>
    </div>
  );
}
