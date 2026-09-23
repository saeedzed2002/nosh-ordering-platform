import { useCallback, useEffect, useState } from "react";

import type {
  ApiV1Allergen,
  ApiV1Availability,
  ApiV1CartQuote,
  ApiV1CartQuoteLine,
  ApiV1CartSelectedOption,
  ApiV1Category,
  ApiV1Location,
  ApiV1Media,
  ApiV1MenuItem,
  ApiV1Option,
  ApiV1OptionGroup,
  ApiV1PublicReview,
  ApiV1PublicReviewList,
} from "./api/v1";
import { apiBaseUrl } from "./site";

export type CustomerAvailability = ApiV1Availability;
export type CustomerMedia = ApiV1Media;
export type CustomerCategory = ApiV1Category;
export type CustomerAllergen = ApiV1Allergen;
export type CustomerOption = ApiV1Option;
export type CustomerOptionGroup = ApiV1OptionGroup;
export type CustomerMenuItem = ApiV1MenuItem;
export type CustomerLocation = ApiV1Location;

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

export type CustomerCartSelectedOption = ApiV1CartSelectedOption;
export type CustomerCartQuoteLine = ApiV1CartQuoteLine;
export type CustomerCartQuote = ApiV1CartQuote;
export type CustomerPublicReview = ApiV1PublicReview;
export type CustomerPublicReviewList = ApiV1PublicReviewList;

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
  locationSlug: string | null = null,
): Promise<CustomerCartQuote> {
  return postCatalogJson<CustomerCartQuote>(
    "/api/v1/catalog/cart/quote",
    { lines, location_slug: locationSlug },
    signal,
  );
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

export function useCustomerPublicReviews(slug: string | undefined) {
  const readReviews = useCallback(
    (signal: AbortSignal) => slug
      ? readCatalogJson<CustomerPublicReviewList>(`/api/v1/catalog/menu-items/${encodeURIComponent(slug)}/reviews`, signal)
      : Promise.reject(new Error("A dish link is required.")),
    [slug],
  );
  return useResource(`customer-public-reviews:${slug ?? "missing"}`, readReviews);
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
