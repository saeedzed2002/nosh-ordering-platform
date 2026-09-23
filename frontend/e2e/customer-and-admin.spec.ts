import { expect, test } from "@playwright/test";

const adminEmail = process.env.NOSH_E2E_ADMIN_EMAIL ?? "manager@nosh.example";
const adminPassword = process.env.NOSH_E2E_ADMIN_PASSWORD;

test.describe.configure({ mode: "serial" });

for (const viewport of [
  { name: "mobile", width: 375, height: 812 },
  { name: "tablet", width: 768, height: 1024 },
]) {
  test(`customer menu remains usable at ${viewport.name} width`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/menu");

    await expect(page.getByRole("heading", { name: "Find what fits the table." })).toBeVisible();
    await expect(page.getByRole("button", { name: /Cart/ })).toBeVisible();
    await expect(page.locator(".skip-link")).toHaveAttribute("href", "#menu-results");
    const documentWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(documentWidth).toBeLessThanOrEqual(viewport.width + 1);
  });
}

test("customer can customize, check out, and track an order", async ({ page }) => {
  const pageErrors: string[] = [];
  const failedResponses: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") {
      const location = message.location();
      pageErrors.push(`${message.text()} @ ${location.url}:${location.lineNumber}`);
    }
  });
  page.on("response", (response) => {
    if (response.status() >= 400) failedResponses.push(`${response.status()} ${response.url()}`);
  });

  await page.goto("/menu/harissa-chicken-bowl");
  await expect(page.getByRole("heading", { name: "Harissa chicken bowl" })).toBeVisible();
  await page.getByLabel(/Greens/).check();
  await page.getByLabel(/Extra harissa/).check();
  await page.getByLabel("Increase quantity").click();
  await expect(page.locator(".customer-order-summary output")).toHaveText("2");
  await expect(page.locator(".customer-order-summary strong")).toHaveText("$30.50");

  await page.getByRole("button", { name: /Add to cart/ }).click();
  await expect(page.locator(".header-cart-button")).toContainText("2");
  await page.locator(".header-cart-button").click();
  await expect(page.getByRole("dialog", { name: /Your cart/ })).toBeVisible();
  await page.getByRole("link", { name: "Checkout" }).click();

  await expect(page).toHaveURL(/\/checkout$/);
  await page.getByLabel("Name").fill("E2E customer");
  await page.getByLabel("Phone").fill("+1 555 010 0195");
  await page.getByLabel("Email").fill("e2e.customer@nosh.example");
  await page.getByRole("button", { name: "Place local-demo order" }).click();

  await expect(page).toHaveURL(/\/orders\/[A-Z0-9-]+$/);
  await expect(page.getByText("Local-demo order tracker")).toBeVisible();
  await expect(page.getByLabel("Order progress")).toBeVisible();
  const reference = await page.locator(".customer-receipt-reference strong").textContent();
  expect(reference).toMatch(/^N-[0-9A-F]{16}$/);
  expect({ failedResponses, pageErrors }).toEqual({ failedResponses: [], pageErrors: [] });
});

test("staff protected workflows retain keyboard-safe dialogs", async ({ page }) => {
  test.skip(!adminPassword, "Set NOSH_E2E_ADMIN_PASSWORD to run the authenticated local E2E flow.");

  await page.goto("/admin/sign-in");
  await page.getByLabel("Email address").fill(adminEmail);
  await page.getByLabel("Password").fill(adminPassword ?? "");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin\/home$/);

  await expect(page.getByRole("heading", { name: "Write it as the customer should read it." })).toBeVisible();
  await page.getByLabel("Headline").fill("Temporary E2E content edit");
  await expect(page.getByText("Unsaved changes")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Headline")).not.toHaveValue("Temporary E2E content edit");

  await page.getByRole("link", { name: "Menu", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Keep every plate true to the pass." })).toBeVisible();
  await expect(page.locator(".admin-state-chip.published").first()).toHaveText("Live");

  await page.getByRole("link", { name: "Orders", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Keep every handoff visible." })).toBeVisible();
  const queuedOrder = page.locator(".admin-order-list button").first();
  await expect(queuedOrder).toBeVisible();
  await queuedOrder.click();
  const requestDetail = page.getByRole("button", { name: "Request a detail" });
  await expect(requestDetail).toBeVisible();
  await requestDetail.click();
  await expect(page.getByRole("dialog", { name: "Request a detail" })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Reason" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(requestDetail).toBeFocused();
});
