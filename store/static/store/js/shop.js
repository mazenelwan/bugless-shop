(function () {
  "use strict";

  if (!window.BuglessCart) return;
  window.BuglessCart.bindSidebar({ quantityControls: true });

  var cards = Array.prototype.slice.call(document.querySelectorAll(".product-card"));
  cards.forEach(function (card) {
    function openProduct(event) {
      if (event.target.closest(".add-btn")) return;
      if (card.dataset.productUrl) window.location.assign(card.dataset.productUrl);
    }

    card.addEventListener("click", openProduct);
    card.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openProduct(event);
      }
    });
  });

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-add-product]");
    if (!button) return;
    event.preventDefault();

    var product = window.BuglessCart.catalog.filter(function (item) {
      return item.productId === button.dataset.addProduct;
    })[0];
    if (!product) return;
    if ((product.variants || []).length) {
      window.location.assign(product.url);
      return;
    }

    window.BuglessCart.add(product.productId, null, 1);
    var panel = document.getElementById("cart");
    if (panel) panel.classList.remove("cart-open");
  });

  var input = document.querySelector(".search-input");
  var resultRoot = document.getElementById("catalog-results");
  if (!input || !resultRoot) return;

  var groups = Array.prototype.slice.call(resultRoot.querySelectorAll(".products"));
  var noResults = document.getElementById("search-no-results");
  if (!noResults) {
    noResults = document.createElement("p");
    noResults.id = "search-no-results";
    noResults.textContent = "No results found.";
    noResults.style.display = "none";
    resultRoot.appendChild(noResults);
  }

  input.addEventListener("input", function () {
    var query = input.value.trim().toLowerCase();
    var visible = 0;
    groups.forEach(function (group) {
      var heading = group.previousElementSibling;
      var groupVisible = 0;
      Array.prototype.forEach.call(group.querySelectorAll(".product-card"), function (card) {
        var matches = !query || (card.dataset.searchText || "").indexOf(query) !== -1;
        card.style.display = matches ? "" : "none";
        if (matches) groupVisible += 1;
      });
      group.style.display = groupVisible ? "" : "none";
      if (heading && heading.tagName === "H1") heading.style.display = groupVisible ? "" : "none";
      visible += groupVisible;
    });
    noResults.style.display = query && !visible ? "block" : "none";
  });
})();

