import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { CustomerMenuCard } from "./CustomerMenuPage";
import type { CustomerMenuItem } from "./customerCatalog";

const reviewableItem = {
  availability: "available",
  category: { name: "Fire & grill" },
  currency_code: "USD",
  description: "Charred chicken with herbs and rice.",
  dietary_tags: ["halal-style"],
  final_price_minor: 1450,
  media: null,
  name: "Harissa chicken bowl",
  slug: "harissa-chicken-bowl",
} as CustomerMenuItem;

function renderMenuCard(canReview: boolean): string {
  return renderToStaticMarkup(
    <MemoryRouter>
      <CustomerMenuCard canReview={canReview} item={reviewableItem} preparationMinutes={25} />
    </MemoryRouter>,
  );
}

describe("CustomerMenuCard review action", () => {
  it("does not expose a review action when the server reports no eligible purchase", () => {
    expect(renderMenuCard(false)).not.toContain("Add a review");
  });

  it("exposes the account review action below an eligible purchased dish", () => {
    const markup = renderMenuCard(true);

    expect(markup).toContain("Add a review");
    expect(markup).toContain('href="/account#reviews"');
  });
});
