const toggle = document.querySelector(".nav-toggle");
const nav = document.querySelector(".site-nav");
const recentNav = document.querySelector("#recent-parks");
const pageSlug = document.body.dataset.pageSlug;
const pageTitle = document.body.dataset.pageTitle;
const pageDepth = Number(document.body.dataset.pageDepth || "0");

if (toggle && nav) {
  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
  });
}

const storageKey = "nationalParkCam.recentParks";
const homeHref = pageDepth === 0 ? "" : "../";

const getParkHref = (slug) => `${homeHref}parks/${slug}.html`;

const readRecentParks = () => {
  try {
    return JSON.parse(localStorage.getItem(storageKey) || "[]");
  } catch {
    return [];
  }
};

const writeRecentParks = (items) => {
  localStorage.setItem(storageKey, JSON.stringify(items.slice(0, 5)));
};

const renderRecentParks = () => {
  if (!recentNav) return;
  const items = readRecentParks();
  recentNav.replaceChildren();
  if (!items.length) {
    recentNav.hidden = true;
    return;
  }
  recentNav.hidden = false;
  const label = document.createElement("span");
  label.textContent = "Recent";
  recentNav.append(label);
  for (const item of items.slice(0, 5)) {
    const link = document.createElement("a");
    link.href = getParkHref(item.slug);
    link.textContent = item.shortTitle || item.title;
    if (item.slug === pageSlug) link.setAttribute("aria-current", "page");
    recentNav.append(link);
  }
};

if (pageSlug && pageSlug !== "national-park-webcam-home" && pageSlug !== "resources") {
  const shortTitle = pageTitle
    .replace("National and State Parks Webcams", "")
    .replace("National Parks Webcams", "")
    .replace("National Park Webcams", "")
    .replace("National Park", "")
    .replace("Webcams", "")
    .trim();
  const nextRecent = [
    { slug: pageSlug, title: pageTitle, shortTitle: shortTitle || pageTitle },
    ...readRecentParks().filter((item) => item.slug !== pageSlug),
  ];
  writeRecentParks(nextRecent);
}

renderRecentParks();

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

const weatherSection = document.querySelector(".weather-section[data-lat][data-lng]");

const formatTemp = (value, unit) => {
  if (value === null || value === undefined) return "";
  return `${Math.round(value)}°${unit === "F" ? "F" : unit}`;
};

const renderWeatherError = (message) => {
  document.querySelectorAll("[data-weather-hourly], [data-weather-daily]").forEach((el) => {
    el.textContent = message;
    el.classList.add("weather-unavailable");
  });
};

if (weatherSection) {
  const lat = weatherSection.dataset.lat;
  const lng = weatherSection.dataset.lng;
  const hourlyEl = weatherSection.querySelector("[data-weather-hourly]");
  const dailyEl = weatherSection.querySelector("[data-weather-daily]");

  fetch(`https://api.weather.gov/points/${lat},${lng}`)
    .then((response) => {
      if (!response.ok) throw new Error("Forecast point unavailable");
      return response.json();
    })
    .then((point) =>
      Promise.all([
        fetch(point.properties.forecastHourly).then((response) => response.json()),
        fetch(point.properties.forecast).then((response) => response.json()),
      ])
    )
    .then(([hourly, daily]) => {
      const hourlyItems = (hourly.properties?.periods || []).slice(0, 12);
      const dailyItems = (daily.properties?.periods || []).filter((period) => period.isDaytime).slice(0, 7);

      if (hourlyEl) {
        hourlyEl.replaceChildren(
          ...hourlyItems.map((period) => {
            const item = document.createElement("div");
            item.className = "hourly-item";
            const time = new Date(period.startTime);
            item.innerHTML = `<span>${time.toLocaleTimeString([], { hour: "numeric" })}</span><strong>${formatTemp(period.temperature, period.temperatureUnit)}</strong><small>${period.shortForecast}</small>`;
            return item;
          })
        );
      }

      if (dailyEl) {
        dailyEl.replaceChildren(
          ...dailyItems.map((period) => {
            const item = document.createElement("div");
            item.className = "daily-item";
            item.innerHTML = `<strong>${period.name}</strong><span>${formatTemp(period.temperature, period.temperatureUnit)}</span><p>${period.shortForecast}</p>`;
            return item;
          })
        );
      }
    })
    .catch(() => renderWeatherError("Weather is temporarily unavailable."));
}
