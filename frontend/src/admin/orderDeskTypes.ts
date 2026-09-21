export type AdminOrderStatus =
  | "scheduled"
  | "submitted"
  | "accepted"
  | "preparing"
  | "ready_for_pickup"
  | "ready_for_courier"
  | "handed_to_customer"
  | "handed_to_courier"
  | "out_for_delivery"
  | "delivered"
  | "declined"
  | "cancelled"
  | "needs_contact";

export type AdminOrderQueue = "needs_approval" | "scheduled" | "active" | "ready" | "completed" | "archive";
export type AdminFulfillmentMethod = "pickup" | "delivery";
export type OnlineOrderingState = "on" | "timed_pause" | "off";
export type OrderIssueReason = "customer_request" | "fulfillment_details" | "kitchen_unavailable" | "schedule_unavailable";

export type AdminOrderListItem = {
  public_reference: string;
  status: AdminOrderStatus;
  fulfillment_method: AdminFulfillmentMethod;
  created_at: string;
  scheduled_for: string | null;
  location_name: string;
  recipient_name: string;
  total_minor: number;
  currency_code: string;
  item_count: number;
  queue: AdminOrderQueue;
};

export type AdminOrderDetail = AdminOrderListItem & {
  recipient_email: string;
  recipient_phone: string;
  delivery_address: string | null;
  fulfillment_instructions: string | null;
  pickup_instructions: string | null;
  delivery_area: string | null;
  lines: Array<{
    menu_item_name: string;
    quantity: number;
    note: string | null;
    selected_options: string[];
    ingredients: string[];
    dietary_tags: string[];
    allergens: Array<{ name: string; slug: string }>;
  }>;
  status_events: Array<{
    status: AdminOrderStatus;
    note: string;
    created_at: string;
    actor_name: string | null;
  }>;
  valid_next_statuses: AdminOrderStatus[];
};

export type AdminOrderDesk = {
  orders: AdminOrderListItem[];
  queue_counts: Array<{ queue: AdminOrderQueue; label: string; count: number }>;
  locations: Array<{ id: string; name: string }>;
  total: number;
};

export type LocationOrderControls = {
  id: string;
  name: string;
  online_ordering_state: OnlineOrderingState;
  online_ordering_paused_until: string | null;
  ordering_available: boolean;
  ordering_message: string;
  preparation_minutes: number;
  demo_capacity: number;
};

export const issueReasons: Array<{ value: OrderIssueReason; label: string }> = [
  { value: "fulfillment_details", label: "A fulfilment detail needs confirmation" },
  { value: "customer_request", label: "Customer request" },
  { value: "kitchen_unavailable", label: "Kitchen unavailable" },
  { value: "schedule_unavailable", label: "Requested time unavailable" },
];

const statusLabels: Record<AdminOrderStatus, string> = {
  scheduled: "Scheduled",
  submitted: "Submitted",
  accepted: "Accepted",
  preparing: "Preparing",
  ready_for_pickup: "Ready for pickup",
  ready_for_courier: "Ready for courier",
  handed_to_customer: "Handed to customer",
  handed_to_courier: "Handed to courier",
  out_for_delivery: "Out for delivery",
  delivered: "Delivered",
  declined: "Declined",
  cancelled: "Cancelled",
  needs_contact: "Needs contact",
};

export function orderStatusLabel(status: AdminOrderStatus): string {
  return statusLabels[status];
}

export function orderActionLabel(status: AdminOrderStatus): string {
  const labels: Partial<Record<AdminOrderStatus, string>> = {
    accepted: "Accept order",
    preparing: "Start preparation",
    ready_for_pickup: "Mark ready for pickup",
    ready_for_courier: "Mark ready for courier",
    handed_to_customer: "Hand to customer",
    handed_to_courier: "Hand to courier",
    out_for_delivery: "Mark out for delivery",
    delivered: "Mark delivered",
    needs_contact: "Request a detail",
    declined: "Decline order",
    cancelled: "Cancel order",
  };
  return labels[status] ?? orderStatusLabel(status);
}

export function formatOrderDeskMoment(value: string | null): string {
  if (!value) {
    return "Not scheduled";
  }
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatOrderDeskPrice(minor: number, currency: string): string {
  return new Intl.NumberFormat("en-US", { currency, style: "currency" }).format(minor / 100);
}
