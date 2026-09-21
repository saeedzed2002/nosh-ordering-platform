import { describe, expect, it } from "vitest";

import {
  isTrackingIssue,
  trackingStatusDescription,
  trackingStepState,
  trackingSteps,
} from "./customerTracking";

describe("customer order tracking", () => {
  it("keeps pickup and delivery progress distinct", () => {
    expect(trackingSteps("pickup").map((step) => step.status)).toEqual([
      "submitted",
      "accepted",
      "preparing",
      "ready_for_pickup",
      "handed_to_customer",
    ]);
    expect(trackingSteps("delivery").map((step) => step.status)).toContain("handed_to_courier");
    expect(trackingStepState("ready_for_courier", "delivery", "handed_to_courier")).toBe("upcoming");
    expect(trackingStepState("handed_to_courier", "delivery", "ready_for_courier")).toBe("complete");
  });

  it("makes contact and courier limitations explicit", () => {
    expect(isTrackingIssue("needs_contact")).toBe(true);
    expect(isTrackingIssue("preparing")).toBe(false);
    expect(trackingStatusDescription("out_for_delivery")).toContain("does not show a live courier map");
  });
});
