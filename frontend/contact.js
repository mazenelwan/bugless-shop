


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
