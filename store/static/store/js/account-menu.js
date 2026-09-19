/* ============================================
   Account sidebar toggle.
   Only wires up if the logged-in avatar button
   and sidebar exist on the page (they're only
   rendered when the visitor is authenticated).
   ============================================ */
(function () {
  "use strict";

  var avatarBtn = document.getElementById("account-avatar-btn");
  var sidebar = document.getElementById("account-sidebar");
  var overlay = document.getElementById("account-overlay");
  var closeBtn = document.getElementById("account-sidebar-close");
  if (!avatarBtn || !sidebar || !overlay) return;

  function openSidebar() {
    overlay.hidden = false;
    sidebar.classList.add("is-open");
    requestAnimationFrame(function () {
      overlay.classList.add("is-visible");
    });
    sidebar.setAttribute("aria-hidden", "false");
    avatarBtn.setAttribute("aria-expanded", "true");
  }

  function closeSidebar() {
    sidebar.classList.remove("is-open");
    overlay.classList.remove("is-visible");
    sidebar.setAttribute("aria-hidden", "true");
    avatarBtn.setAttribute("aria-expanded", "false");
    window.setTimeout(function () {
      overlay.hidden = true;
    }, 300);
  }

  avatarBtn.addEventListener("click", function (event) {
    event.stopPropagation();
    if (sidebar.classList.contains("is-open")) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  if (closeBtn) closeBtn.addEventListener("click", closeSidebar);
  overlay.addEventListener("click", closeSidebar);

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && sidebar.classList.contains("is-open")) {
      closeSidebar();
    }
  });
})();
