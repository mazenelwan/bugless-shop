(function () {
  "use strict";

  var burger = document.getElementById("burger");
  var menu = document.getElementById("menu");
  if (!burger || !menu) return;

  function setOpen(open) {
    burger.classList.toggle("is-active", open);
    menu.classList.toggle("is-active", open);
    burger.setAttribute("aria-expanded", open ? "true" : "false");
  }

  burger.addEventListener("click", function (event) {
    event.stopPropagation();
    setOpen(!menu.classList.contains("is-active"));
  });

  burger.addEventListener("keydown", function (event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      burger.click();
    }
  });

  menu.addEventListener("click", function (event) {
    if (event.target.closest(".menu-link")) setOpen(false);
  });

  document.addEventListener("click", function (event) {
    if (
      menu.classList.contains("is-active") &&
      !menu.contains(event.target) &&
      !burger.contains(event.target)
    ) {
      setOpen(false);
    }
  });

  window.addEventListener("resize", function () {
    setOpen(false);
  });
})();

