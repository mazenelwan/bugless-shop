/* ============================================
   Mobile navigation toggle (hamburger menu)
   The header/CSS already support a mobile menu
   overlay (.menu.is-active / .burger.is-active),
   but no script was ever wired up to toggle it,
   so the nav (Home/Shop/Contact/About) was stuck
   off-screen and unreachable on mobile. This adds
   just the missing click handling.
   ============================================ */
(function () {
  var burgerBtn = document.getElementById('burger');
  var navMenu = document.getElementById('menu');
  if (!burgerBtn || !navMenu) return;

  burgerBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    burgerBtn.classList.toggle('is-active');
    navMenu.classList.toggle('is-active');
  });

  // Close the menu once a nav link is tapped
  var navLinks = navMenu.querySelectorAll('.menu-link');
  for (var i = 0; i < navLinks.length; i++) {
    navLinks[i].addEventListener('click', function () {
      burgerBtn.classList.remove('is-active');
      navMenu.classList.remove('is-active');
    });
  }

  // Close the menu when tapping outside of it
  document.addEventListener('click', function (e) {
    if (
      navMenu.classList.contains('is-active') &&
      !navMenu.contains(e.target) &&
      !burgerBtn.contains(e.target)
    ) {
      burgerBtn.classList.remove('is-active');
      navMenu.classList.remove('is-active');
    }
  });
})();


/* ============================================
   Search bar: filter products by name, and by
   the category heading (<h1>) each product sits
   under, so typing "shirt" matches both the
   "Men's Shirts" category and any product named
   with "shirt" in it. Hides empty categories and
   shows a "No results found" message when nothing
   on the whole page matches.
   ============================================ */
(function () {
  var searchInput = document.querySelector('.search-input');
  var searchForm = document.querySelector('.search-form');
  if (!searchInput) return;

  if (searchForm) {
    searchForm.addEventListener('submit', function (e) {
      e.preventDefault();
    });
  }

  var categories = document.querySelectorAll('.products');
  if (!categories.length) return;

  var noResultsMsg = document.getElementById('search-no-results');
  if (!noResultsMsg) {
    noResultsMsg = document.createElement('p');
    noResultsMsg.id = 'search-no-results';
    noResultsMsg.textContent = 'No results found.';
    noResultsMsg.style.display = 'none';
    var lastCategory = categories[categories.length - 1];
    lastCategory.parentNode.insertBefore(noResultsMsg, lastCategory.nextSibling);
  }

  function filterProducts(query) {
    var q = query.trim().toLowerCase();
    var anyVisible = false;

    categories.forEach(function (categoryDiv) {
      var heading = categoryDiv.previousElementSibling; // the <h1> right before .products
      var categoryName = (heading && heading.tagName === 'H1') ? heading.textContent.toLowerCase() : '';
      var cards = categoryDiv.querySelectorAll('.product-card');
      var categoryHasMatch = false;

      cards.forEach(function (card) {
        var nameEl = card.querySelector('h3');
        var name = nameEl ? nameEl.textContent.toLowerCase() : '';
        var matches = q === '' || name.indexOf(q) !== -1 || categoryName.indexOf(q) !== -1;
        card.style.display = matches ? '' : 'none';
        if (matches) categoryHasMatch = true;
      });

      var showCategory = q === '' || categoryHasMatch;
      categoryDiv.style.display = showCategory ? '' : 'none';
      if (heading && heading.tagName === 'H1') {
        heading.style.display = showCategory ? '' : 'none';
      }
      if (showCategory) anyVisible = true;
    });

    noResultsMsg.style.display = (q !== '' && !anyVisible) ? 'block' : 'none';
  }

  searchInput.addEventListener('input', function () {
    filterProducts(searchInput.value);
  });
})();


/* ============================================
   Cart icon toggle
   The cart panel starts hidden. Clicking the
   floating cart icon shows/hides the order panel.
   Clicking "Add to cart" on a product also closes
   the panel automatically (so the user sees the
   product list again right after adding). Editing
   something INSIDE the open panel — quantity +/-,
   remove, or Clear Cart — never closes it; only
   the toggle icon or an "Add to cart" click do.
   ============================================ */
(function () {
  var cartToggleBtn = document.getElementById('cart-toggle-btn');
  var cartPanel = document.getElementById('cart');
  if (!cartToggleBtn || !cartPanel) return;

  cartToggleBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    cartPanel.classList.toggle('cart-open');
  });

  // Auto-close only for "Add to cart" clicks (product list), never for
  // actions that happen inside the cart panel itself.
  document.addEventListener('click', function (e) {
    if (e.target.closest('.add-btn')) {
      cartPanel.classList.remove('cart-open');
    }
  });
})();
