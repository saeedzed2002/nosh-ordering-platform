import { describe, expect, it } from "vitest";

import { currencyInputToMinor, minorToCurrencyInput } from "./admin/menuTypes";
import { resolveApiBaseUrl } from "./site";

describe("resolveApiBaseUrl", () => {
  it("uses the local backend when no value is provided", () => {
    expect(resolveApiBaseUrl()).toBe("http://localhost:8000");
  });

  it("removes trailing slashes from a configured URL", () => {
    expect(resolveApiBaseUrl("https://api.example.test///")).toBe(
      "https://api.example.test",
    );
  });
});

describe("currency input helpers", () => {
  it("converts customer-facing USD amounts without exposing minor units", () => {
    expect(currencyInputToMinor("14.50")).toBe(1450);
    expect(currencyInputToMinor("0.015")).toBe(2);
    expect(minorToCurrencyInput(1450)).toBe(14.5);
  });

  it("preserves invalid input for form validation", () => {
    expect(Number.isNaN(currencyInputToMinor("not-a-price"))).toBe(true);
  });
});
