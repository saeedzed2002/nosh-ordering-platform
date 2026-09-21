import { useCallback, useEffect, useState } from "react";

import { apiBaseUrl } from "./site";

export type CustomerAvailability = "available" | "temporarily_unavailable" | "scheduled";

export type CustomerMedia = {
  id: string;
  alt_text: string;
  width: number;
  height: number;
};

export type CustomerCategory = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  display_order: number;
  media: CustomerMedia | null;
};

export type CustomerAllergen = {
  name: string;
  slug: string;
  note: string | null;
};

export type CustomerOption = {
  id: string;
  name: string;
  price_delta_minor: number;
  display_order: number;
};

export type CustomerOptionGroup = {
  id: string;
  name: string;
  kind: "choice" | "extra" | "removal";
  minimum_selections: number;
  maximum_selections: number;
  display_order: number;
  options: CustomerOption[];
};

export type CustomerMenuItem = {
  id: string;
  name: string;
  slug: string;
  description: string;
  ingredients: string[];
  dietary_tags: string[];
  base_price_minor: number;
  demo_discount_minor: number;
  final_price_minor: number;
  currency_code: string;
  display_order: number;
  category: CustomerCategory;
  availability: CustomerAvailability;
  media: CustomerMedia | null;
  allergens: CustomerAllergen[];
  option_groups: CustomerOptionGroup[];
};

export type CustomerLocation = {
  id: string;
  name: string;
  slug: string;
  address_text: string;
  pickup_instructions: string | null;
  delivery_area_text: string | null;
  pickup_available: boolean;
  delivery_available: boolean;
  preparation_minutes: number;
  online_ordering_available: boolean;
  online_ordering_message: string;
};

export type CustomerCatalogSnapshot = {
  items: CustomerMenuItem[];
  location: CustomerLocation | null;
  locations: CustomerLocation[];
};

export type CustomerCartLineInput = {
  client_line_id: string;
  menu_item_slug: string;
  quantity: number;
  option_ids: string[];
  note: string | null;
};

export type CustomerCartSelectedOption = {
  id: string;
  name: string;
  option_group_name: string;
  price_delta_minor: number;
};

export type CustomerCartQuoteLine = {
  client_line_id: string;
  menu_item_slug: string;
  name: string;
  media: CustomerMedia | null;
  quantity: number;
  note: string | null;
  selected_options: CustomerCartSelectedOption[];
  unit_price_minor: number;
  line_total_minor: number;
  currency_code: string;
};

export type CustomerCartQuote = {
  lines: CustomerCartQuoteLine[];
  subtotal_minor: number;
  currency_code: string;
};

type ResourceState<T> = {
  data: T | null;
  error: string | null;
  status: "loading" | "ready" | "error";
};

async function readCatalogJson<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new Error(`The local catalog returned ${response.status}.`);
  }
  return response.json() as Promise<T>;
}

async function postCatalogJson<T>(
  path: string,
  body: unknown,
  signal: AbortSignal,
): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    body: JSON.stringify(body),
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    method: "POST",
    signal,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: unknown } | null;
    const detail = typeof payload?.detail === "string" ? payload.detail : "The kitchen could not validate this cart.";
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export async function readCustomerCatalog(
  signal: AbortSignal,
): Promise<CustomerCatalogSnapshot> {
  const [items, locations] = await Promise.all([
    readCatalogJson<CustomerMenuItem[]>("/api/v1/catalog/menu-items", signal),
    readCatalogJson<CustomerLocation[]>("/api/v1/catalog/locations", signal),
  ]);
  return { items, location: locations[0] ?? null, locations };
}

export async function readCustomerMenuItem(
  slug: string,
  signal: AbortSignal,
): Promise<{ item: CustomerMenuItem; location: CustomerLocation | null }> {
  const [item, locations] = await Promise.all([
    readCatalogJson<CustomerMenuItem>(
      `/api/v1/catalog/menu-items/${encodeURIComponent(slug)}`,
      signal,
    ),
    readCatalogJson<CustomerLocation[]>("/api/v1/catalog/locations", signal),
  ]);
  return { item, location: locations[0] ?? null };
}

export function quoteCustomerCart(
  lines: CustomerCartLineInput[],
  signal: AbortSignal,
): Promise<CustomerCartQuote> {
  return postCatalogJson<CustomerCartQuote>("/api/v1/catalog/cart/quote", { lines }, signal);
}

function useResource<T>(
  cacheKey: string,
  reader: (signal: AbortSignal) => Promise<T>,
): ResourceState<T> & { retry: () => void } {
  const [retryKey, setRetryKey] = useState(0);
  const [state, setState] = useState<ResourceState<T>>({
    data: null,
    error: null,
    status: "loading",
  });

  useEffect(() => {
    const controller = new AbortController();
    setState((current) => ({ ...current, error: null, status: "loading" }));

    void reader(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setState({ data, error: null, status: "ready" });
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setState({
            data: null,
            error: "The menu is not available right now. Check the local service and try again.",
            status: "error",
          });
        }
      });

    return () => controller.abort();
  }, [cacheKey, reader, retryKey]);

  return {
    ...state,
    retry: useCallback(() => setRetryKey((current) => current + 1), []),
  };
}

const readCatalog = (signal: AbortSignal) => readCustomerCatalog(signal);

export function useCustomerCatalog() {
  return useResource("customer-catalog", readCatalog);
}

export function useCustomerMenuItem(slug: string | undefined) {
  const readItem = useCallback(
    (signal: AbortSignal) => {
      if (!slug) {
        return Promise.reject(new Error("A dish link is required."));
      }
      return readCustomerMenuItem(slug, signal);
    },
    [slug],
  );
  return useResource(`customer-menu-item:${slug ?? "missing"}`, readItem);
}

export function formatCustomerPrice(minor: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    currency,
    style: "currency",
  }).format(minor / 100);
}

export function customerMediaUrl(media: Pick<CustomerMedia, "id"> | null): string | null {
  return media ? `${apiBaseUrl}/api/v1/media/${media.id}/thumbnail` : null;
}

export function availabilityLabel(availability: CustomerAvailability): string {
  return availability === "available" ? "Available today" : "Unavailable today";
}
