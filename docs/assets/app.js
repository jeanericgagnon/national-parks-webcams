const toggle = document.querySelector(".nav-toggle");
const nav = document.querySelector(".site-nav");

if (toggle && nav) {
  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
  });
}

const search = document.querySelector("#park-search");
const cards = Array.from(document.querySelectorAll(".park-card"));

if (search && cards.length) {
  search.addEventListener("input", () => {
    const query = search.value.trim().toLowerCase();
    for (const card of cards) {
      const title = card.dataset.title || "";
      card.hidden = query.length > 0 && !title.includes(query);
    }
  });
}
