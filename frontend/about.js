/* Custom Script */
    /* Scroll Top */
    $(document).ready(function() {
        "use strict";
        var offSetTop = 200;
        var $scrollToTopButton = $('.scrollToTop');
        //Check to see if the window is top if not then display button
        $(window).scroll(function() {
            if ($(this).scrollTop() > offSetTop) {
                $scrollToTopButton.fadeIn();
            } else {
                $scrollToTopButton.fadeOut();
            }
        });

        //Click event to scroll to top
        $scrollToTopButton.click(function() {
            $('html, body').animate({ scrollTop: 0 }, 200);
            return false;
        });

    });
    // fixed footer
    var siteFooter = document.getElementById('site-footer');
    if ((siteFooter.offsetTop + siteFooter.offsetHeight) < window.innerHeight) {
        siteFooter.classList.add('fixed-bottom', 'bottom-0', 'left-0', 'w-full');
    }
    /* Animate On Scroll */
    AOS.init();
    /* Owl Carousel */
    $('.owl-carousel').owlCarousel({
        loop: true,
        margin: 30,
        nav: false,
        center: true,
        dots: false,
        autoplay: true,
        responsive: {
            0: {
                items: 1
            },
            600: {
                items: 2
            },
            1000: {
                items: 3
            }
        }
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
