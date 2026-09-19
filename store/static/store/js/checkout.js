(function (window, document) {
  "use strict";

  if (!window.BuglessCart) return;

  var itemsElement = document.getElementById("checkout-items");
  var subtotalElement = document.getElementById("checkout-subtotal");
  var discountElement = document.getElementById("checkout-discount");
  var discountLine = document.getElementById("discount-line");
  var totalElement = document.getElementById("checkout-total");
  var emptyMessage = document.getElementById("empty-cart-msg");
  var form = document.getElementById("checkout-form");
  var submitButton = document.getElementById("confirm-order-btn");
  var statusElement = document.getElementById("checkout-status");
  var promotionInput = document.getElementById("promo-code-input");
  var promotionButton = document.getElementById("apply-promo-btn");
  var promotionMessage = document.getElementById("promo-message");
  var retryStorageKey = "bfCheckoutIdempotencyKey";
  var memoryRetryKey = null;
  var quotedPromotionCode = "";

  if (!itemsElement || !subtotalElement || !totalElement || !form) return;

  function money(value) {
    var parsed = Number(value);
    return Number.isFinite(parsed) ? parsed.toFixed(2) : "0.00";
  }

  function setMoney(data) {
    subtotalElement.textContent = money(data.subtotal);
    totalElement.textContent = money(data.total);
    var discount = Number(data.discount || 0);
    if (discountElement) discountElement.textContent = money(discount);
    if (discountLine) discountLine.style.display = discount > 0 ? "block" : "none";
  }

  function estimateMoney() {
    var estimate = window.BuglessCart.estimatedTotal();
    setMoney({ subtotal: estimate, discount: 0, total: estimate });
  }

  function detailLabel(detail) {
    var label = detail.product ? detail.product.name : "Unavailable product";
    if (detail.variant) {
      var options = [detail.variant.color, detail.variant.size].filter(Boolean);
      if (options.length) label += " · " + options.join(" / ");
    }
    return label;
  }

  function render() {
    var details = window.BuglessCart.details();
    itemsElement.replaceChildren();
    details.forEach(function (detail) {
      var row = document.createElement("div");
      row.className = "checkout-item";
      var name = document.createElement("span");
      name.className = "checkout-item-name";
      name.textContent = detailLabel(detail) + " × " + detail.quantity;
      var price = document.createElement("span");
      price.className = "checkout-item-price";
      var unitPrice = detail.product ? Number(detail.product.price) : 0;
      price.textContent = "EGP " + money(unitPrice * detail.quantity);
      row.append(name, price);
      itemsElement.appendChild(row);
    });

    estimateMoney();
    quotedPromotionCode = "";
    if (promotionMessage) promotionMessage.textContent = "";
    var empty = details.length === 0;
    if (emptyMessage) emptyMessage.style.display = empty ? "block" : "none";
    form.style.display = empty ? "none" : "block";
  }

  function cartRequest(promotionCode) {
    var cart = window.BuglessCart.read();
    return {
      version: cart.version,
      promotionCode: promotionCode,
      lines: cart.lines
    };
  }

  function csrfToken() {
    var input = form.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  async function postJson(url, payload) {
    var response;
    try {
      response = await window.fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken()
        },
        body: JSON.stringify(payload)
      });
    } catch (error) {
      throw {
        status: 0,
        body: null,
        message: "The network request failed. Your cart is still saved."
      };
    }

    var body = null;
    try {
      body = await response.json();
    } catch (error) {
      body = null;
    }
    if (!response.ok || !body || body.ok !== true) {
      throw {
        status: response.status,
        body: body,
        message: body && body.error
          ? body.error.message
          : "Checkout could not be completed. Please try again."
      };
    }
    return body.data;
  }

  function firstError(error) {
    var fields = error && error.body && error.body.error
      ? error.body.error.fields || {}
      : {};
    var keys = Object.keys(fields);
    return keys.length && fields[keys[0]].length ? fields[keys[0]][0] : error.message;
  }

  function clearFieldErrors() {
    form.querySelectorAll("[aria-invalid=true]").forEach(function (field) {
      field.removeAttribute("aria-invalid");
    });
    form.querySelectorAll("[data-checkout-field-error]").forEach(function (node) {
      node.remove();
    });
    if (promotionInput) promotionInput.removeAttribute("aria-invalid");
  }

  function bindFieldErrors(error) {
    clearFieldErrors();
    var fields = error && error.body && error.body.error
      ? error.body.error.fields || {}
      : {};
    Object.keys(fields).forEach(function (path) {
      if (!path.startsWith("customer.")) return;
      var name = path.slice("customer.".length);
      var input = form.elements.namedItem(name);
      if (!input) return;
      input.setAttribute("aria-invalid", "true");
      var message = document.createElement("small");
      message.dataset.checkoutFieldError = name;
      message.className = "promo-message promo-error";
      message.textContent = fields[path][0];
      input.parentElement.appendChild(message);
    });
    if (fields.promotionCode && promotionInput) {
      promotionInput.setAttribute("aria-invalid", "true");
      if (promotionMessage) {
        promotionMessage.textContent = fields.promotionCode[0];
        promotionMessage.className = "promo-message promo-error";
      }
    }
  }

  function generateRetryKey() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    if (!window.crypto || typeof window.crypto.getRandomValues !== "function") {
      throw new Error("Secure random identifiers are unavailable in this browser.");
    }
    var bytes = new Uint8Array(16);
    window.crypto.getRandomValues(bytes);
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    var hex = Array.from(bytes, function (value) {
      return value.toString(16).padStart(2, "0");
    }).join("");
    return [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16), hex.slice(16, 20), hex.slice(20)].join("-");
  }

  function retryKey() {
    if (memoryRetryKey) return memoryRetryKey;
    try {
      memoryRetryKey = window.sessionStorage.getItem(retryStorageKey);
    } catch (error) {
      memoryRetryKey = null;
    }
    if (!memoryRetryKey) {
      memoryRetryKey = generateRetryKey();
      try {
        window.sessionStorage.setItem(retryStorageKey, memoryRetryKey);
      } catch (error) {
        // The in-memory key still protects retries for the current page load.
      }
    }
    return memoryRetryKey;
  }

  function clearRetryKey() {
    memoryRetryKey = null;
    try {
      window.sessionStorage.removeItem(retryStorageKey);
    } catch (error) {
      // A successful response is still authoritative when storage is unavailable.
    }
  }

  document.addEventListener("bf-cart-change", render);
  render();

  if (promotionInput) {
    promotionInput.addEventListener("input", function () {
      if (promotionInput.value.trim().toUpperCase() !== quotedPromotionCode) {
        quotedPromotionCode = "";
        estimateMoney();
        if (promotionMessage) promotionMessage.textContent = "";
      }
    });
  }

  if (promotionButton && promotionInput && promotionMessage) {
    promotionButton.addEventListener("click", async function () {
      var code = promotionInput.value.trim().toUpperCase();
      if (!code) {
        promotionMessage.textContent = "Enter a promotion code first.";
        promotionMessage.className = "promo-message promo-error";
        return;
      }
      promotionButton.disabled = true;
      promotionMessage.textContent = "Checking promotion…";
      promotionMessage.className = "promo-message";
      try {
        var data = await postJson(form.dataset.quoteUrl, cartRequest(code));
        quotedPromotionCode = data.promotion ? data.promotion.code : "";
        promotionInput.value = quotedPromotionCode;
        setMoney(data);
        promotionMessage.textContent = "Promotion applied to this estimate. Final availability is checked when you place the order.";
        promotionMessage.className = "promo-message promo-success";
        promotionInput.removeAttribute("aria-invalid");
      } catch (error) {
        quotedPromotionCode = "";
        estimateMoney();
        promotionInput.setAttribute("aria-invalid", "true");
        promotionMessage.textContent = firstError(error);
        promotionMessage.className = "promo-message promo-error";
      } finally {
        promotionButton.disabled = false;
      }
    });
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    clearFieldErrors();
    if (!form.reportValidity()) return;

    var cart = window.BuglessCart.read();
    if (!cart.lines.length) {
      render();
      return;
    }
    var fields = new window.FormData(form);
    var key;
    try {
      key = retryKey();
    } catch (error) {
      if (statusElement) {
        statusElement.textContent = error.message;
        statusElement.className = "promo-message promo-error";
      }
      return;
    }

    var payload = {
      version: cart.version,
      idempotencyKey: key,
      customer: {
        name: String(fields.get("name") || ""),
        email: String(fields.get("email") || ""),
        phone: String(fields.get("phone") || ""),
        address: String(fields.get("address") || ""),
        city: "",
        notes: String(fields.get("notes") || "")
      },
      promotionCode: promotionInput ? promotionInput.value.trim().toUpperCase() : "",
      lines: cart.lines
    };

    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "PLACING ORDER…";
    }
    if (statusElement) {
      statusElement.textContent = "Validating current price and stock…";
      statusElement.className = "promo-message";
    }

    try {
      var data = await postJson(form.dataset.createUrl, payload);
      setMoney(data);
      if (statusElement) {
        statusElement.textContent = data.replayed
          ? "Your existing order was recovered. Opening confirmation…"
          : "Order confirmed. Opening confirmation…";
        statusElement.className = "promo-message promo-success";
      }
      window.BuglessCart.clear();
      clearRetryKey();
      window.location.assign(data.confirmationUrl);
    } catch (error) {
      bindFieldErrors(error);
      if (statusElement) {
        statusElement.textContent = error.message;
        statusElement.className = "promo-message promo-error";
      }
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = "Confirm Order";
      }
    }
  });
})(window, document);
