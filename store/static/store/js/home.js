(function () {
  "use strict";

  var input = document.querySelector(".search-input");
  var portfolio = document.querySelector(".portfolio");
  if (!input || !portfolio) return;

  var cards = Array.prototype.slice.call(portfolio.querySelectorAll(".project"));
  var message = document.createElement("p");
  message.id = "search-no-results";
  message.textContent = "No results found.";
  message.style.display = "none";
  portfolio.parentNode.insertBefore(message, portfolio);

  input.addEventListener("input", function () {
    var query = input.value.trim().toLowerCase();
    var visible = 0;
    cards.forEach(function (card) {
      var matches = !query || (card.dataset.searchText || "").indexOf(query) !== -1;
      card.style.display = matches ? "" : "none";
      if (matches) visible += 1;
    });
    message.style.display = query && !visible ? "block" : "none";
  });
})();

