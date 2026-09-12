




var buttons = document.querySelectorAll(".dropbtn");
var dropdowns = document.querySelectorAll(".cont");
var luis = document.getElementsByClassName("bar");
var puc = document.getElementsByClassName("side-wrap");

var documentClickHandler = function (event) {
  var isClickInsideDropdown = false;
  for (var i = 0; i < dropdowns.length; i++) {
    if (
      dropdowns[i].contains(event.target) ||
      buttons[i].contains(event.target)
    ) {
      isClickInsideDropdown = true;
    }
  }

  for (var i = 0; i < dropdowns.length; i++) {
    if (!isClickInsideDropdown) {
      dropdowns[i].classList.remove("active");
    }
  }

  for (var j = 0; j < puc.length; j++) {
    if (!puc[j].contains(event.target)) {
      puc[j].classList.remove("sum");
    }
  }
};

var closeDropdowns = function () {
  for (var i = 0; i < dropdowns.length; i++) {
    dropdowns[i].classList.remove("active");
  }
};

var closeSideMenu = function () {
  for (var j = 0; j < puc.length; j++) {
    puc[j].classList.remove("sum");
  }
};

for (var i = 0; i < buttons.length; i++) {
  buttons[i].addEventListener("click", function (event) {
    var index = Array.from(buttons).indexOf(event.currentTarget);
    dropdowns[index].classList.toggle("active");
    for (var i = 0; i < dropdowns.length; i++) {
      if (i !== index) {
        dropdowns[i].classList.remove("active");
      }
    }
    closeSideMenu();
    event.stopPropagation();
  });
}

for (var i = 0; i < luis.length; i++) {
  luis[i].addEventListener("click", function (event) {
    closeDropdowns();
    for (var j = 0; j < puc.length; j++) {
      puc[j].classList.toggle("sum");
    }
    event.stopPropagation();
  });
}

window.addEventListener("resize", function () {
  closeDropdowns();
  closeSideMenu();
});

document.addEventListener("click", documentClickHandler);


// Optional: Scroll animation for articles
const articles = document.querySelectorAll('.article-list article');
window.addEventListener('scroll', () => {
  const triggerBottom = window.innerHeight / 5 * 4;
  articles.forEach(article => {
    const articleTop = article.getBoundingClientRect().top;
    if(articleTop < triggerBottom) {
      article.style.transform = 'translateY(0)';
      article.style.opacity = '1';
    } else {
      article.style.transform = 'translateY(50px)';
      article.style.opacity = '0';
    }
  });
});

// Initialize articles with hidden state
articles.forEach(article => {
  article.style.transform = 'translateY(50px)';
  article.style.opacity = '0';
  article.style.transition = 'all 0.6s ease-out';
});








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
   Search bar: filter the category cards
   (Men's Shirts, Jacket, Pants, T-Shirts, Polo,
   Shoes) by matching the typed text against each
   card's title. Simple substring match, case
   insensitive, exactly per the existing content.
   ============================================ */
(function () {
  var searchInput = document.querySelector('.search-input');
  var searchForm = document.querySelector('.search-form');
  if (!searchInput) return;

  // This page has no real search endpoint, so stop the default
  // GET submission (which would reload the page) and filter instead.
  if (searchForm) {
    searchForm.addEventListener('submit', function (e) {
      e.preventDefault();
    });
  }

  var cards = document.querySelectorAll('.portfolio .project');
  if (!cards.length) return; // e.g. this script also loads on about.html

  var noResultsMsg = document.getElementById('search-no-results');
  if (!noResultsMsg) {
    noResultsMsg = document.createElement('p');
    noResultsMsg.id = 'search-no-results';
    noResultsMsg.textContent = 'No results found.';
    noResultsMsg.style.display = 'none';
    var portfolio = document.querySelector('.portfolio');
    portfolio.parentNode.insertBefore(noResultsMsg, portfolio);
  }

  function filterCards(query) {
    var q = query.trim().toLowerCase();
    var anyVisible = false;

    cards.forEach(function (card) {
      var titleEl = card.querySelector('.project-info-title');
      var title = titleEl ? titleEl.textContent.toLowerCase() : '';
      var matches = q === '' || title.indexOf(q) !== -1;
      card.style.display = matches ? '' : 'none';
      if (matches) anyVisible = true;
    });

    noResultsMsg.style.display = (q !== '' && !anyVisible) ? 'block' : 'none';
  }

  searchInput.addEventListener('input', function () {
    filterCards(searchInput.value);
  });
})();
