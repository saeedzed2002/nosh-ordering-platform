import { describe, expect, it } from "vitest";

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
