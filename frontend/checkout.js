/* ============================================
   Mobile navigation toggle (hamburger menu)
   Same reusable pattern used on every other page.
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

  var navLinks = navMenu.querySelectorAll('.menu-link');
  for (var i = 0; i < navLinks.length; i++) {
    navLinks[i].addEventListener('click', function () {
      burgerBtn.classList.remove('is-active');
      navMenu.classList.remove('is-active');
    });
  }

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
   Checkout — order summary + placeholder confirm
   Reads the cart that shop2.html already saves to
   localStorage on every change, so nothing needs
   to be duplicated or passed manually. There is no
   backend order endpoint yet, so "Confirm Order"
   just shows a thank-you confirmation and clears
   the cart, exactly as requested.
   ============================================ */
(function () {
  var CART_STORAGE_KEY = 'bfCart';
  var itemsEl = document.getElementById('checkout-items');
  var totalEl = document.getElementById('checkout-total');
  var subtotalEl = document.getElementById('checkout-subtotal');
  var discountEl = document.getElementById('checkout-discount');
  var discountLineEl = document.getElementById('discount-line');
  var promoInput = document.getElementById('promo-code-input');
  var applyPromoBtn = document.getElementById('apply-promo-btn');
  var promoMessageEl = document.getElementById('promo-message');
  var form = document.getElementById('checkout-form');
  var confirmationEl = document.getElementById('order-confirmation');
  var emptyMsgEl = document.getElementById('empty-cart-msg');
  var orderNumberEl = document.getElementById('order-number');
  if (!itemsEl || !totalEl) return;

  // No backend/promo-code endpoint yet, so a small fixed set of codes is
  // used here as a placeholder — the same approach as the order confirmation.
  var PROMO_CODES = {
    'SAVE10': { type: 'percent', value: 10 },
    'SAVE20': { type: 'percent', value: 20 },
    'WELCOME50': { type: 'fixed', value: 50 }
  };
  var appliedPromo = null; // { code, type, value }

  function loadCart() {
    try {
      return JSON.parse(localStorage.getItem(CART_STORAGE_KEY)) || [];
    } catch (e) {
      return [];
    }
  }

  function getSubtotal(cart) {
    var subtotal = 0;
    cart.forEach(function (item) {
      subtotal += item.price * item.qty;
    });
    return subtotal;
  }

  function getDiscount(subtotal) {
    if (!appliedPromo) return 0;
    if (appliedPromo.type === 'percent') {
      return subtotal * (appliedPromo.value / 100);
    }
    return Math.min(appliedPromo.value, subtotal); // never discount below 0
  }

  function renderSummary() {
    var cart = loadCart();
    itemsEl.innerHTML = '';

    if (!cart.length) {
      if (emptyMsgEl) emptyMsgEl.style.display = 'block';
      if (form) form.style.display = 'none';
      subtotalEl.textContent = '0.00';
      totalEl.textContent = '0.00';
      if (discountLineEl) discountLineEl.style.display = 'none';
      return;
    }

    cart.forEach(function (item) {
      var row = document.createElement('div');
      row.className = 'checkout-item';
      row.innerHTML =
        '<span class="checkout-item-name">' + item.name + ' x ' + item.qty + '</span>' +
        '<span class="checkout-item-price">EGP ' + (item.price * item.qty).toFixed(2) + '</span>';
      itemsEl.appendChild(row);
    });

    var subtotal = getSubtotal(cart);
    var discount = getDiscount(subtotal);
    var total = subtotal - discount;

    subtotalEl.textContent = subtotal.toFixed(2);
    totalEl.textContent = total.toFixed(2);

    if (discount > 0 && discountLineEl && discountEl) {
      discountEl.textContent = discount.toFixed(2);
      discountLineEl.style.display = 'flex';
    } else if (discountLineEl) {
      discountLineEl.style.display = 'none';
    }
  }

  renderSummary();

  if (applyPromoBtn && promoInput) {
    applyPromoBtn.addEventListener('click', function () {
      var code = promoInput.value.trim().toUpperCase();
      if (!code) return;

      var promo = PROMO_CODES[code];
      if (promo) {
        appliedPromo = { code: code, type: promo.type, value: promo.value };
        promoMessageEl.textContent =
          promo.type === 'percent'
            ? 'Promo code applied: ' + promo.value + '% off!'
            : 'Promo code applied: EGP ' + promo.value + ' off!';
        promoMessageEl.className = 'promo-message promo-success';
      } else {
        appliedPromo = null;
        promoMessageEl.textContent = 'Invalid promo code.';
        promoMessageEl.className = 'promo-message promo-error';
      }
      renderSummary();
    });
  }

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var cart = loadCart();
      if (!cart.length) return;

      var orderNumber = '#BF-' + Date.now().toString().slice(-6);
      if (orderNumberEl) orderNumberEl.textContent = orderNumber;

      // No backend order endpoint yet — placeholder confirmation only.
      // The (mock) order is considered placed, so the cart is cleared.
      try {
        localStorage.removeItem(CART_STORAGE_KEY);
      } catch (err) {
        // ignore if storage is unavailable
      }

      form.style.display = 'none';
      if (emptyMsgEl) emptyMsgEl.style.display = 'none';
      if (confirmationEl) confirmationEl.style.display = 'block';
    });
  }
})();
