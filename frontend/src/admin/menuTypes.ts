export type PublicationState = "draft" | "published";
export type AvailabilityState = "available" | "temporarily_unavailable" | "scheduled";
export type OptionKind = "choice" | "extra" | "removal";

export type MediaSummary = {
  id: string;
  alt_text: string;
  width: number;
  height: number;
};

export type Category = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  display_order: number;
  media: MediaSummary | null;
  is_published: boolean;
  menu_item_count: number;
};

export type Allergen = {
  id: string;
  name: string;
  slug: string;
  note: string | null;
  description: string | null;
};

export type MenuMedia = MediaSummary & {
  original_filename: string;
  publication_state: PublicationState;
};

export type Location = {
  id: string;
  name: string;
  slug: string;
};

export type MenuOption = {
  id?: string;
  name: string;
  price_delta_minor: number;
  is_available: boolean;
  display_order?: number;
};

export type MenuOptionGroup = {
  id?: string;
  name: string;
  kind: OptionKind;
  minimum_selections: number;
  maximum_selections: number;
  display_order?: number;
  options: MenuOption[];
};

export type MenuAvailability = {
  id?: string | null;
  location_id: string;
  state: AvailabilityState;
  available_from: string | null;
  available_until: string | null;
};

export type MenuItem = {
  id: string;
  name: string;
  slug: string;
  description: string;
  category: Category;
  media: MediaSummary;
  ingredients: string[];
  dietary_tags: string[];
  base_price_minor: number;
  demo_discount_minor: number;
  final_price_minor: number;
  currency_code: string;
  display_order: number;
  publication_state: PublicationState;
  allergens: Allergen[];
  option_groups: MenuOptionGroup[];
  availability: MenuAvailability;
  history: CatalogChange[];
};

export type CatalogChange = {
  id: string;
  action: string;
  actor_name: string;
  created_at: string;
  snapshot: Record<string, unknown>;
};

export type CuratedCollection = {
  id: string;
  name: string;
  slug: string;
  description: string;
  display_order: number;
  publication_state: PublicationState;
  menu_item_ids: string[];
};

export type MenuSetup = {
  categories: Category[];
  allergens: Allergen[];
  media: MenuMedia[];
  locations: Location[];
  collections: CuratedCollection[];
  featured: {
    menu_item_id: string | null;
    menu_item_name: string | null;
  };
};

export type MenuWritePayload = {
  name: string;
  slug: string;
  description: string;
  category_id: string;
  media_id: string;
  ingredients: string[];
  dietary_tags: string[];
  base_price_minor: number;
  demo_discount_minor: number;
  display_order: number;
  publication_state: PublicationState;
  allergen_ids: string[];
  option_groups: Array<{
    name: string;
    kind: OptionKind;
    minimum_selections: number;
    maximum_selections: number;
    options: Array<{
      name: string;
      price_delta_minor: number;
      is_available: boolean;
    }>;
  }>;
  availability: {
    location_id: string;
    state: AvailabilityState;
    available_from?: string | null;
    available_until?: string | null;
  };
};

export function formatPrice(minor: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    currency,
    style: "currency",
  }).format(minor / 100);
}

export function currencyInputToMinor(value: string): number {
  const amount = Number(value);
  return Number.isFinite(amount) ? Math.round(amount * 100) : Number.NaN;
}

export function minorToCurrencyInput(minor: number): number {
  return minor / 100;
}

export function toLocalInputValue(value: string | null): string {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export function fromLocalInputValue(value: string): string | null {
  return value ? new Date(value).toISOString() : null;
}

export function slugFromName(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function splitTerms(value: string): string[] {
  return value
    .split(",")
    .map((term) => term.trim())
    .filter(Boolean);
}
