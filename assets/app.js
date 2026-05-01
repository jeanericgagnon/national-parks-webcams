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
const mapButtons = [];

if (search) {
  search.addEventListener("input", () => {
    const query = search.value.trim().toLowerCase();
    for (const card of cards) {
      const title = card.dataset.title || "";
      card.hidden = query.length > 0 && !title.includes(query);
    }
    for (const button of mapButtons) {
      const title = button.dataset.title || "";
      button.hidden = query.length > 0 && !title.includes(query);
    }
  });
}

const mapEl = document.querySelector("#webcam-map");
const mapDataEl = document.querySelector("#park-map-data");

if (mapEl && mapDataEl && window.L) {
  const parks = JSON.parse(mapDataEl.textContent || "[]");
  const map = L.map(mapEl, {
    scrollWheelZoom: false,
    worldCopyJump: true,
  });

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 18,
  }).addTo(map);

  const titleEl = document.querySelector("#map-active-title");
  const metaEl = document.querySelector("#map-active-meta");
  const linkEl = document.querySelector("#map-active-link");
  const listEl = document.querySelector("#map-list");
  const markers = new Map();
  const bounds = [];

  const activatePark = (park, options = {}) => {
    const shouldFocus = options.focus ?? true;
    const shouldOpenPopup = options.popup ?? true;
    if (!park) return;
    if (titleEl) titleEl.textContent = park.fullTitle;
    if (metaEl) {
      metaEl.textContent = `${park.cams} live cam source${park.cams === 1 ? "" : "s"} · ${park.embeds} total embeds · ${park.links} planning links`;
    }
    if (linkEl) linkEl.href = park.href;
    for (const button of mapButtons) {
      button.classList.toggle("active", button.dataset.slug === park.slug);
    }
    const marker = markers.get(park.slug);
    if (marker) {
      if (shouldOpenPopup) {
        marker.openPopup();
      }
      if (shouldFocus) {
        map.flyTo([park.lat, park.lng], Math.max(map.getZoom(), 5), { duration: 0.6 });
      }
    }
  };

  for (const park of parks) {
    bounds.push([park.lat, park.lng]);
    const marker = L.marker([park.lat, park.lng], {
      icon: L.divIcon({
        className: "",
        html: `<span class="cam-marker${park.cams ? "" : " no-live"}">${park.cams || "Map"}</span>`,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
      }),
      title: park.fullTitle,
    }).addTo(map);

    marker.bindPopup(
      `<div class="map-popup"><strong>${park.fullTitle}</strong><span class="cam-pill">${park.cams} live cam source${park.cams === 1 ? "" : "s"}</span><p><a href="${park.href}">Open live cams</a></p></div>`
    );
    marker.on("click", () => activatePark(park));
    markers.set(park.slug, marker);

    if (listEl) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "map-park-button";
      button.dataset.slug = park.slug;
      button.dataset.title = `${park.title} ${park.fullTitle}`.toLowerCase();
      button.innerHTML = `<strong>${park.title}</strong><span>${park.cams} live cam source${park.cams === 1 ? "" : "s"}</span>`;
      button.addEventListener("click", () => activatePark(park));
      listEl.append(button);
      mapButtons.push(button);
    }
  }

  if (bounds.length) {
    map.fitBounds(bounds, { padding: [35, 35] });
    activatePark(parks.find((park) => park.slug === "yellowstone-webcam") || parks[0], {
      focus: false,
      popup: false,
    });
  }
}
