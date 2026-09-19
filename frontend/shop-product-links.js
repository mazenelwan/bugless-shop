/* Makes every existing Shop card open the single reusable details page. */
(function () {
  function initialize() {
    if (!window.BF_PRODUCTS) return;
    var cards = document.querySelectorAll('.product-card');
    cards.forEach(function (card, index) {
      var product = window.BF_PRODUCTS[index];
      if (!product) return;
      card.dataset.productId = product.id;
      card.setAttribute('role', 'link');
      card.setAttribute('tabindex', '0');
      card.setAttribute('aria-label', 'View ' + product.name);
      function open(event) {
        if (event.target.closest('.add-btn')) return;
        window.location.href = 'product.html?id=' + encodeURIComponent(product.id);
      }
      card.addEventListener('click', open);
      card.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(event); }
      });
    });
    var query = new URLSearchParams(window.location.search).get('search');
    var searchInput = document.querySelector('.search-input');
    if (query && searchInput) {
      searchInput.value = query;
      searchInput.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize); else initialize();
})();
