import { apiBaseUrl } from "./site";
import type { CustomerCartLineInput } from "./customerCatalog";

export type CustomerCheckoutTiming = "immediate" | "scheduled";
export type CustomerFulfillmentMethod = "pickup" | "delivery";
export type CustomerPaymentScenario = "succeeds" | "fails";

export type CustomerCheckoutRequest = {
  idempotency_key: string;
  location_slug: string;
  fulfillment_method: CustomerFulfillmentMethod;
  timing: CustomerCheckoutTiming;
  scheduled_for: string | null;
  recipient_name: string;
  recipient_email: string;
  recipient_phone: string;
  delivery_address: string | null;
  fulfillment_instructions: string | null;
  promotion_code: string | null;
  payment_scenario: CustomerPaymentScenario;
  lines: CustomerCartLineInput[];
};

export type CustomerOrderReceiptOption = {
  id: string;
  name: string;
  option_group_name: string;
  price_delta_minor: number;
};

export type CustomerOrderReceiptLine = {
  menu_item_slug: string;
  menu_item_name: string;
  quantity: number;
  note: string | null;
  unit_price_minor: number;
  line_total_minor: number;
  currency_code: string;
  selected_options: CustomerOrderReceiptOption[];
};

export type CustomerOrderReceipt = {
  public_reference: string;
  status: string;
  created_at: string;
  scheduled_for: string | null;
  location_name: string;
  location_address: string;
  contact_phone: string;
  fulfillment_method: CustomerFulfillmentMethod;
  pickup_instructions: string | null;
  delivery_area: string | null;
  preparation_minutes: number;
  estimated_fulfillment_at: string | null;
  currency_code: string;
  subtotal_minor: number;
  promotion_code: string | null;
  promotion_discount_minor: number;
  total_minor: number;
  payment_message: string;
  lines: CustomerOrderReceiptLine[];
  status_events: Array<{ status: string; note: string; created_at: string }>;
};

async function readError(response: Response): Promise<string> {
  const payload = await response.json().catch(() => null) as { detail?: unknown } | null;
  if (typeof payload?.detail === "string") {
    return payload.detail;
  }
  return response.status === 422
    ? "Check the highlighted checkout details and try again."
    : "The local kitchen could not place this order. Try again.";
}

export async function submitCustomerOrder(
  request: CustomerCheckoutRequest,
  signal: AbortSignal,
  accessToken: string | null = null,
): Promise<CustomerOrderReceipt> {
  const headers = new Headers({ "Content-Type": "application/json" });
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  const response = await fetch(`${apiBaseUrl}/api/v1/orders/checkout`, {
    body: JSON.stringify(request),
    cache: "no-store",
    headers,
    method: "POST",
    signal,
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<CustomerOrderReceipt>;
}

export async function readCustomerOrder(
  publicReference: string,
  signal: AbortSignal,
): Promise<CustomerOrderReceipt> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/orders/${encodeURIComponent(publicReference)}`,
    { cache: "no-store", signal },
  );
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<CustomerOrderReceipt>;
}
