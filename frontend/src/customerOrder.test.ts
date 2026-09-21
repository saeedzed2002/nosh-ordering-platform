import { describe, expect, it } from "vitest";

import type { CustomerMenuItem } from "./customerCatalog";
import { previewCustomerPrice, selectionIssues } from "./customerOrder";

const dish = {
  final_price_minor: 1450,
  option_groups: [
    {
      id: "base",
      maximum_selections: 1,
      minimum_selections: 1,
      name: "Choose a base",
      options: [
        { id: "grains", name: "Warm grains", price_delta_minor: 0 },
        { id: "greens", name: "Greens", price_delta_minor: 0 },
      ],
    },
    {
      id: "heat",
      maximum_selections: 1,
      minimum_selections: 0,
      name: "Add heat",
      options: [{ id: "harissa", name: "Extra harissa", price_delta_minor: 75 }],
    },
  ],
} as unknown as CustomerMenuItem;

describe("customer order choices", () => {
  it("rejects a missing required choice and a selection over the configured maximum", () => {
    expect(selectionIssues(dish, {})).toEqual({ base: "Choose one option for Choose a base." });
    expect(selectionIssues(dish, { base: ["grains", "greens"] })).toEqual({
      base: "Choose no more than 1 options for Choose a base.",
    });
  });

  it("adds selected extras to the immediate customer price preview", () => {
    expect(previewCustomerPrice(dish, { base: ["grains"], heat: ["harissa"] })).toBe(1525);
  });
});
