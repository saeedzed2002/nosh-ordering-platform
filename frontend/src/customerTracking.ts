import type { CustomerFulfillmentMethod } from "./customerCheckout";

export type CustomerTrackingStatus =
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

export type CustomerTrackingStep = {
  label: string;
  status: CustomerTrackingStatus;
};

const pickupSteps: CustomerTrackingStep[] = [
  { status: "submitted", label: "Submitted" },
  { status: "accepted", label: "Accepted" },
  { status: "preparing", label: "Preparing" },
  { status: "ready_for_pickup", label: "Ready for pickup" },
  { status: "handed_to_customer", label: "Collected" },
];

const deliverySteps: CustomerTrackingStep[] = [
  { status: "submitted", label: "Submitted" },
  { status: "accepted", label: "Accepted" },
  { status: "preparing", label: "Preparing" },
  { status: "ready_for_courier", label: "Ready for courier" },
  { status: "handed_to_courier", label: "Handed to courier" },
  { status: "out_for_delivery", label: "Out for delivery" },
  { status: "delivered", label: "Delivered" },
];

const labels: Record<CustomerTrackingStatus, string> = {
  scheduled: "Scheduled",
  submitted: "Submitted",
  accepted: "Accepted",
  preparing: "Preparing",
  ready_for_pickup: "Ready for pickup",
  ready_for_courier: "Ready for courier",
  handed_to_customer: "Collected",
  handed_to_courier: "Handed to courier",
  out_for_delivery: "Out for delivery",
  delivered: "Delivered",
  declined: "Unable to accept",
  cancelled: "Cancelled",
  needs_contact: "Kitchen needs a detail",
};

const descriptions: Record<CustomerTrackingStatus, string> = {
  scheduled: "The kitchen has saved the requested time and will release this order in its preparation window.",
  submitted: "The kitchen has received this order and will review it shortly.",
  accepted: "The kitchen has accepted this order and will start preparing it next.",
  preparing: "The kitchen is preparing this order now.",
  ready_for_pickup: "This order is ready to collect from the kitchen counter.",
  ready_for_courier: "This order is ready and waiting for its courier handoff.",
  handed_to_customer: "This order has been collected from the kitchen.",
  handed_to_courier: "The kitchen has handed this order to the courier.",
  out_for_delivery: "This order is on its way. This local demo does not show a live courier map or GPS location.",
  delivered: "This order has been marked as delivered.",
  declined: "The kitchen could not accept this order. Read the timeline and contact the kitchen if you need help.",
  cancelled: "This order has been cancelled. Read the timeline and contact the kitchen if you need help.",
  needs_contact: "The kitchen needs to confirm a detail before this order can continue.",
};

export function trackingSteps(method: CustomerFulfillmentMethod): CustomerTrackingStep[] {
  return method === "delivery" ? deliverySteps : pickupSteps;
}

export function trackingStatusLabel(status: string): string {
  return labels[status as CustomerTrackingStatus] ?? "Order update";
}

export function trackingStatusDescription(status: string): string {
  return descriptions[status as CustomerTrackingStatus] ?? "The kitchen has recorded a new order update.";
}

export function trackingStepState(
  status: string,
  method: CustomerFulfillmentMethod,
  stepStatus: CustomerTrackingStatus,
): "complete" | "current" | "upcoming" {
  const steps = trackingSteps(method);
  const currentIndex = steps.findIndex((step) => step.status === status);
  const stepIndex = steps.findIndex((step) => step.status === stepStatus);
  if (currentIndex === -1 || stepIndex > currentIndex) {
    return "upcoming";
  }
  return stepIndex === currentIndex ? "current" : "complete";
}

export function isTrackingIssue(status: string): boolean {
  return status === "declined" || status === "cancelled" || status === "needs_contact";
}
