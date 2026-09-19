(function () {
  "use strict";

  var root = document.getElementById("product-root");
  if (!root || !window.BuglessCart) return;

  window.BuglessCart.bindSidebar({ quantityControls: false });

  var variantsElement = document.getElementById("bf-variant-data");
  var variants = [];
  try {
    variants = variantsElement ? JSON.parse(variantsElement.textContent) : [];
  } catch (error) {
    variants = [];
  }

  Array.prototype.forEach.call(document.querySelectorAll(".thumb"), function (button) {
    button.addEventListener("click", function () {
      var image = document.getElementById("main-product-image");
      if (image) image.src = button.dataset.imageUrl;
      Array.prototype.forEach.call(document.querySelectorAll(".thumb"), function (item) {
        item.classList.remove("active");
      });
      button.classList.add("active");
    });
  });

  function bindOption(attribute) {
    var selector = "[data-" + attribute + "]";
    Array.prototype.forEach.call(document.querySelectorAll(selector), function (button) {
      button.addEventListener("click", function () {
        Array.prototype.forEach.call(document.querySelectorAll(selector), function (item) {
          item.classList.remove("selected");
        });
        button.classList.add("selected");
      });
    });
  }
  bindOption("color");
  bindOption("size");

  var amount = 1;
  var output = document.getElementById("quantity");
  function setAmount(next) {
    amount = Math.max(1, Math.min(99, next));
    output.textContent = amount;
  }
  document.getElementById("minus").addEventListener("click", function () { setAmount(amount - 1); });
  document.getElementById("plus").addEventListener("click", function () { setAmount(amount + 1); });

  function selectedValue(attribute) {
    var selected = document.querySelector("[data-" + attribute + "].selected");
    return selected ? selected.dataset[attribute] : "";
  }

  function selectedVariant() {
    if (!variants.length) return null;
    var color = selectedValue("color");
    var size = selectedValue("size");
    return variants.filter(function (variant) {
      return variant.color === color && variant.size === size;
    })[0] || null;
  }

  function addToCart() {
    var validation = document.getElementById("validation");
    var variant = selectedVariant();
    if (variants.length && (!variant || !variant.available)) {
      validation.textContent = "Please select an available option.";
      return false;
    }
    var added = window.BuglessCart.add(
      root.dataset.productId,
      variant ? variant.variantId : null,
      amount
    );
    validation.textContent = added ? "Added to your cart." : "This product is currently unavailable.";
    return added;
  }

  document.getElementById("add-to-cart").addEventListener("click", addToCart);
  document.getElementById("buy-now").addEventListener("click", function () {
    if (addToCart()) window.location.assign(root.dataset.checkoutUrl);
  });
})();

