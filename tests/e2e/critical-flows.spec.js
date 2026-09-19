const { test, expect } = require("@playwright/test");

const externalResource = /^https?:\/\/(?!127\.0\.0\.1:8010(?:\/|$))/;
const browserSecurityErrors = new WeakMap();

test.beforeEach(async ({ page }) => {
  const errors = [];
  browserSecurityErrors.set(page, errors);
  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error" && /content security policy|refused/i.test(message.text())) {
      errors.push(`console: ${message.text()}`);
    }
  });
  await page.route(externalResource, async (route) => {
    await route.fulfill({ status: 204, contentType: "text/plain", body: "" });
  });
});

test.afterEach(async ({ page }) => {
  expect(browserSecurityErrors.get(page)).toEqual([]);
});

async function addFirstProductAndOpenCheckout(page) {
  await page.goto("/search/?q=BF-SHIRTS-01");
  await expect(page.locator(".product-card")).toHaveCount(1);
  await page.locator(".product-card h3").first().click();
  await expect(page).toHaveURL(/\/product\/[a-z0-9-]+\/$/);
  await page.locator("#add-to-cart").click();
  await expect(page.locator("#validation")).toHaveText("Added to your cart.");
  await page.locator("#cart-toggle-btn").click();
  await expect(page.locator("#cart-items .cart-item")).toHaveCount(1);
  await page.locator("#checkout-btn").click();
  await expect(page).toHaveURL(/\/checkout\/$/);
  await expect(page.locator("#checkout-form")).toBeVisible();
}

async function finishCheckout(page, customer = {}) {
  if (customer.name) await page.getByPlaceholder("Full Name").fill(customer.name);
  if (customer.email) await page.getByPlaceholder("E-mail").fill(customer.email);
  await page.getByPlaceholder("Phone Number").fill("+20 100 000 0000");
  await page.getByPlaceholder("Address").fill("1 Browser Test Street");
  await page.locator("#confirm-order-btn").click();
  await expect(page).toHaveURL(/\/order\/BF-[A-Z0-9-]+\/[0-9a-f-]+\/$/);
  await expect(page.locator(".order-confirmation h1")).toHaveText("Thank you!");
  const orderNumber = (await page.locator(".order-confirmation strong").first().textContent()).trim();
  expect(orderNumber).toMatch(/^BF-[A-Z0-9-]+$/);
  return orderNumber;
}

test("guest catalog, product, cart, checkout, and private confirmation", async ({ page }) => {
  await addFirstProductAndOpenCheckout(page);
  const orderNumber = await finishCheckout(page, {
    name: "Guest Browser Learner",
    email: "guest-browser@example.com"
  });

  const cart = await page.evaluate(() => JSON.parse(localStorage.getItem("bfCart")));
  expect(cart).toEqual({ version: 1, lines: [] });
  expect(await page.locator("body").textContent()).toContain(orderNumber);

  const confirmationUrl = new URL(page.url());
  const parts = confirmationUrl.pathname.split("/").filter(Boolean);
  parts[2] = "00000000-0000-4000-8000-000000000000";
  const response = await page.goto(`/${parts.join("/")}/`);
  expect(response.status()).toBe(404);
});

test("registered checkout is owned, listed, and logout stays POST-backed", async ({ page }, testInfo) => {
  const suffix = testInfo.project.name.replace(/[^a-z0-9]/gi, "-").toLowerCase();
  const email = `account-${suffix}@e2e.local`;
  const password = "Browser-account-password-829!";

  await page.goto("/accounts/register/");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("First name").fill("Account");
  await page.getByLabel("Last name").fill("Learner");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password").fill(password);
  await page.getByRole("button", { name: "CREATE ACCOUNT" }).click();
  await expect(page).toHaveURL(/\/accounts\/profile\/$/);

  await addFirstProductAndOpenCheckout(page);
  await expect(page.getByPlaceholder("Full Name")).toHaveValue("Account Learner");
  await expect(page.getByPlaceholder("E-mail")).toHaveValue(email);
  const orderNumber = await finishCheckout(page);

  await page.getByRole("link", { name: "View in My Orders" }).click();
  await expect(page).toHaveURL(new RegExp(`/accounts/orders/${orderNumber}/$`));
  await expect(page.getByRole("heading", { name: orderNumber })).toBeVisible();
  await page.goto("/accounts/orders/");
  await expect(page.getByText(orderNumber, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "LOG OUT" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/accounts/profile/");
  await expect(page).toHaveURL(/\/accounts\/login\/\?next=/);
});

test("contact validation and idempotent replay remain server-backed", async ({ page }) => {
  await page.goto("/contact/");
  await page.locator("#contact-message").fill("Browser validation probe");
  await page.locator("form[action='/contact/']").evaluate((form) => form.submit());
  await expect(page.locator("#contact-name-errors")).toBeVisible();
  await expect(page.locator("#contact-email-errors")).toBeVisible();

  const csrf = await page.locator("input[name=csrfmiddlewaretoken]").inputValue();
  const submissionId = await page.locator("input[name=submission_id]").inputValue();
  const form = {
    csrfmiddlewaretoken: csrf,
    submission_id: submissionId,
    website: "",
    name: "Browser Contact Learner",
    email: "contact-browser@example.com",
    phone: "+20 100 000 0000",
    subject: "Phase 6",
    message: "A deterministic browser submission."
  };
  const first = await page.request.post("/contact/", { form, maxRedirects: 0 });
  expect(first.status()).toBe(302);
  const replay = await page.request.post("/contact/", { form, maxRedirects: 0 });
  expect(replay.status()).toBe(302);
  const conflict = await page.request.post("/contact/", {
    form: { ...form, message: "Changed reuse must conflict." },
    maxRedirects: 0
  });
  expect(conflict.status()).toBe(409);
  expect(await conflict.text()).toContain("already used for a different message");
});

test("Store Manager can change order status while order details stay immutable", async ({ page }, testInfo) => {
  const suffix = testInfo.project.name.replace(/[^a-z0-9]/gi, "-").toLowerCase();
  await addFirstProductAndOpenCheckout(page);
  const orderNumber = await finishCheckout(page, {
    name: "Admin Order Learner",
    email: `order-admin-${suffix}@e2e.local`
  });

  await page.goto("/admin/login/");
  await page.locator("#id_username").fill("manager@e2e.local");
  await page.locator("#id_password").fill("Phase6-manager-password-829!");
  await page.locator("input[type=submit]").click();
  await page.goto("/admin/store/order/");
  await page.locator("#searchbar").fill(orderNumber);
  await page.locator("#changelist-search input[type=submit]").click();
  await expect(page.locator("#result_list tbody tr")).toHaveCount(1);
  await expect(page.locator("select[name=action] option", { hasText: /paid|refund/i })).toHaveCount(0);
  await page.locator(".action-select").check();
  await page.locator("select[name=action]").selectOption({
    label: "Move selected orders to confirmed"
  });
  await page.locator("button[name=index]").click();
  await expect(page.locator(".messagelist")).toContainText("1 order(s) moved to confirmed");
  await expect(page.locator("#result_list tbody tr")).toContainText("Confirmed");

  await page.getByRole("link", { name: orderNumber }).click();
  await expect(page.locator(".field-status .readonly")).toHaveText("Confirmed");
  await expect(page.locator(".field-payment_status .readonly")).toHaveText("Unpaid");
  await expect(page.locator("input[name=_save]")).toHaveCount(0);
});

test("Store Manager can read a contact message in the simplified admin", async ({ page }, testInfo) => {
  const suffix = testInfo.project.name.replace(/[^a-z0-9]/gi, "-").toLowerCase();
  const email = `admin-flow-${suffix}@e2e.local`;

  await page.goto("/contact/");
  await page.locator("#contact-name").fill("Admin Browser Learner");
  await page.locator("#contact-email").fill(email);
  await page.locator("#contact-message").fill("Please review this contact message.");
  await page.getByRole("button", { name: "Send Now" }).click();
  await expect(page.getByRole("status")).toContainText("sent successfully");

  await page.goto("/admin/login/");
  await page.locator("#id_username").fill("manager@e2e.local");
  await page.locator("#id_password").fill("Phase6-manager-password-829!");
  await page.locator("input[type=submit]").click();
  await expect(page).toHaveURL(/\/admin\/$/);
  await page.goto("/admin/store/contactmessage/");
  await page.locator("#searchbar").fill(email);
  await page.locator("#changelist-search input[type=submit]").click();
  await expect(page.locator("#result_list tbody tr")).toHaveCount(1);
  await expect(page.locator("select[name=action]")).toHaveCount(0);
  await page.locator("#result_list .field-name a").click();
  await expect(page.locator(".field-name .readonly")).toHaveText("Admin Browser Learner");
  await expect(page.locator(".field-email .readonly")).toHaveText(email);
  await expect(page.locator(".field-message .readonly")).toContainText(
    "Please review this contact message."
  );
  await expect(page.locator("input[name=_save]")).toHaveCount(0);
});
