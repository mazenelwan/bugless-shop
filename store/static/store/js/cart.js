(function (window, document) {
  "use strict";

  var STORAGE_KEY = "bfCart";
  var SCHEMA_VERSION = 1;
  var catalogElement = document.getElementById("bf-catalog-data");
  var catalog = [];

  try {
    catalog = catalogElement ? JSON.parse(catalogElement.textContent) : [];
  } catch (error) {
    catalog = [];
  }

  var productsById = Object.create(null);
  var productsByLegacyId = Object.create(null);
  var productsByName = Object.create(null);
  catalog.forEach(function (product) {
    productsById[product.productId] = product;
    if (product.legacyId) productsByLegacyId[product.legacyId] = product;
    var normalizedName = String(product.name || "").trim().toLowerCase();
    if (!productsByName[normalizedName]) productsByName[normalizedName] = [];
    productsByName[normalizedName].push(product);
  });

  function quantity(value) {
    var parsed = Number(value);
    if (!Number.isInteger(parsed) || parsed < 1) return null;
    return Math.min(parsed, 99);
  }

  function lineKey(line) {
    return line.productId + "::" + (line.variantId || "");
  }

  function coalesce(lines) {
    var merged = Object.create(null);
    var order = [];
    lines.forEach(function (line) {
      var normalizedQuantity = quantity(line.quantity);
      if (!line.productId || normalizedQuantity === null) return;
      var normalized = {
        productId: String(line.productId),
        variantId: line.variantId ? String(line.variantId) : null,
        quantity: normalizedQuantity
      };
      var key = lineKey(normalized);
      if (!merged[key]) {
        merged[key] = normalized;
        order.push(key);
      } else {
        merged[key].quantity = Math.min(99, merged[key].quantity + normalizedQuantity);
      }
    });
    return order.map(function (key) { return merged[key]; });
  }

  function resolveLegacyProduct(line) {
    var rawId = line.productId || line.id;
    if (rawId && productsById[String(rawId)]) return productsById[String(rawId)];
    if (rawId && productsByLegacyId[String(rawId)]) return productsByLegacyId[String(rawId)];

    var normalizedName = String(line.name || "").trim().toLowerCase();
    var matches = productsByName[normalizedName] || [];
    return matches.length === 1 ? matches[0] : null;
  }

  function migrate(value) {
    if (value && value.version === SCHEMA_VERSION && Array.isArray(value.lines)) {
      return { version: SCHEMA_VERSION, lines: coalesce(value.lines) };
    }

    if (!Array.isArray(value)) return { version: SCHEMA_VERSION, lines: [] };
    var migrated = [];
    value.forEach(function (legacyLine) {
      if (!legacyLine || typeof legacyLine !== "object") return;
      var product = resolveLegacyProduct(legacyLine);
      var migratedQuantity = quantity(legacyLine.quantity || legacyLine.qty);
      if (!product || migratedQuantity === null) return;

      var variantId = legacyLine.variantId || null;
      if (!variantId && (legacyLine.color || legacyLine.size)) {
        var matchingVariants = (product.variants || []).filter(function (variant) {
          return (
            (!legacyLine.color || variant.color === legacyLine.color) &&
            (!legacyLine.size || variant.size === legacyLine.size)
          );
        });
        if (matchingVariants.length === 1) variantId = matchingVariants[0].variantId;
      }
      migrated.push({
        productId: product.productId,
        variantId: variantId,
        quantity: migratedQuantity
      });
    });
    return { version: SCHEMA_VERSION, lines: coalesce(migrated) };
  }

  function load() {
    try {
      return migrate(JSON.parse(window.localStorage.getItem(STORAGE_KEY)));
    } catch (error) {
      return { version: SCHEMA_VERSION, lines: [] };
    }
  }

  var state = load();

  function persist() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
      // The in-memory cart remains usable when storage is unavailable.
    }
    document.dispatchEvent(new CustomEvent("bf-cart-change", { detail: api.read() }));
  }

  function productFor(line) {
    return productsById[line.productId] || null;
  }

  function variantFor(product, line) {
    if (!product || !line.variantId) return null;
    return (product.variants || []).filter(function (variant) {
      return variant.variantId === line.variantId;
    })[0] || null;
  }

  function details() {
    return state.lines.map(function (line) {
      var product = productFor(line);
      var variant = variantFor(product, line);
      return {
        productId: line.productId,
        variantId: line.variantId,
        quantity: line.quantity,
        product: product,
        variant: variant,
        available: Boolean(
          product &&
          product.available &&
          (!(product.variants || []).length || (variant && variant.available))
        )
      };
    });
  }

  function update(productId, variantId, nextQuantity) {
    var key = lineKey({ productId: String(productId), variantId: variantId || null });
    var normalizedQuantity = quantity(nextQuantity);
    state.lines = state.lines.filter(function (line) { return lineKey(line) !== key; });
    if (normalizedQuantity !== null) {
      state.lines.push({
        productId: String(productId),
        variantId: variantId ? String(variantId) : null,
        quantity: normalizedQuantity
      });
    }
    state.lines = coalesce(state.lines);
    persist();
  }

  function add(productId, variantId, amount) {
    var product = productsById[String(productId)];
    if (!product || !product.available) return false;
    var variants = product.variants || [];
    if (variants.length) {
      var variant = variants.filter(function (item) {
        return item.variantId === String(variantId || "");
      })[0];
      if (!variant || !variant.available) return false;
    }

    var key = lineKey({ productId: String(productId), variantId: variantId || null });
    var current = state.lines.filter(function (line) { return lineKey(line) === key; })[0];
    update(productId, variantId, (current ? current.quantity : 0) + (quantity(amount) || 1));
    return true;
  }

  function remove(productId, variantId) {
    update(productId, variantId, 0);
  }

  function clear() {
    state = { version: SCHEMA_VERSION, lines: [] };
    persist();
  }

  function estimatedTotal() {
    return details().reduce(function (total, line) {
      var price = line.product ? Number(line.product.price) : 0;
      return total + price * line.quantity;
    }, 0);
  }

  function lineLabel(detail) {
    var label = detail.product ? detail.product.name : "Unavailable product";
    if (detail.variant) {
      var options = [detail.variant.color, detail.variant.size].filter(Boolean);
      if (options.length) label += " · " + options.join(" / ");
    }
    return label;
  }

  function bindSidebar(options) {
    options = options || {};
    var list = document.getElementById("cart-items");
    var total = document.getElementById("cart-total");
    var badge = document.getElementById("cart-count-badge");
    var clearButton = document.getElementById("clear-cart-btn");
    var checkoutButton = document.getElementById("checkout-btn");
    var toggleButton = document.getElementById("cart-toggle-btn");
    var panel = document.getElementById("cart");
    if (!list) return function () {};

    function render() {
      list.replaceChildren();
      var count = 0;
      details().forEach(function (detail) {
        count += detail.quantity;
        var row = document.createElement("div");
        row.className = "cart-item";

        var name = document.createElement("span");
        name.className = "cart-item-name";
        name.textContent = lineLabel(detail);
        row.appendChild(name);

        if (options.quantityControls) {
          var controls = document.createElement("div");
          controls.className = "cart-item-controls";
          var decrease = document.createElement("button");
          decrease.type = "button";
          decrease.className = "qty-btn qty-decrease";
          decrease.dataset.cartAction = "decrease";
          decrease.textContent = "−";
          decrease.setAttribute("aria-label", "Decrease quantity");
          var amount = document.createElement("span");
          amount.className = "cart-item-qty";
          amount.textContent = detail.quantity;
          var increase = document.createElement("button");
          increase.type = "button";
          increase.className = "qty-btn qty-increase";
          increase.dataset.cartAction = "increase";
          increase.textContent = "+";
          increase.setAttribute("aria-label", "Increase quantity");
          controls.append(decrease, amount, increase);
          row.appendChild(controls);
        }

        var price = document.createElement("span");
        price.className = "cart-item-price";
        var unitPrice = detail.product ? Number(detail.product.price) : 0;
        price.textContent = options.quantityControls
          ? "EGP " + (unitPrice * detail.quantity).toFixed(2)
          : detail.quantity + " × EGP " + unitPrice.toFixed(2);
        row.appendChild(price);

        var removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "remove-btn";
        removeButton.dataset.cartAction = "remove";
        removeButton.textContent = "×";
        removeButton.setAttribute("aria-label", "Remove item");
        row.appendChild(removeButton);

        row.dataset.productId = detail.productId;
        row.dataset.variantId = detail.variantId || "";
        list.appendChild(row);
      });
      if (total) total.textContent = estimatedTotal().toFixed(2);
      if (badge) badge.textContent = count;
    }

    list.addEventListener("click", function (event) {
      var button = event.target.closest("[data-cart-action]");
      var row = button && button.closest(".cart-item");
      if (!button || !row) return;
      var productId = row.dataset.productId;
      var variantId = row.dataset.variantId || null;
      var current = state.lines.filter(function (line) {
        return lineKey(line) === lineKey({ productId: productId, variantId: variantId });
      })[0];
      if (!current) return;
      if (button.dataset.cartAction === "increase") update(productId, variantId, current.quantity + 1);
      if (button.dataset.cartAction === "decrease") update(productId, variantId, current.quantity - 1);
      if (button.dataset.cartAction === "remove") remove(productId, variantId);
    });

    if (clearButton) clearButton.addEventListener("click", clear);
    if (checkoutButton) {
      checkoutButton.addEventListener("click", function () {
        var destination = checkoutButton.dataset.checkoutUrl;
        if (destination) window.location.assign(destination);
      });
    }
    if (toggleButton && panel) {
      toggleButton.addEventListener("click", function (event) {
        event.stopPropagation();
        var open = panel.classList.toggle("cart-open");
        toggleButton.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }

    document.addEventListener("bf-cart-change", render);
    render();
    return render;
  }

  var api = {
    version: SCHEMA_VERSION,
    read: function () {
      return {
        version: SCHEMA_VERSION,
        lines: state.lines.map(function (line) { return Object.assign({}, line); })
      };
    },
    details: details,
    add: add,
    update: update,
    remove: remove,
    clear: clear,
    estimatedTotal: estimatedTotal,
    bindSidebar: bindSidebar,
    catalog: catalog
  };

  window.BuglessCart = api;
  persist();
})(window, document);
