const root = document.documentElement;
const themeBtn = document.getElementById("theme-toggle");
const darkLabel = themeBtn.dataset.dark || "Dark";
const lightLabel = themeBtn.dataset.light || "Light";
if (localStorage.getItem("preview-theme") === "ink") {
  root.setAttribute("data-theme", "ink");
  themeBtn.textContent = lightLabel;
  themeBtn.setAttribute("aria-pressed", "true");
}
themeBtn.addEventListener("click", () => {
  const ink = root.getAttribute("data-theme") === "ink";
  root.setAttribute("data-theme", ink ? "paper" : "ink");
  themeBtn.textContent = ink ? darkLabel : lightLabel;
  themeBtn.setAttribute("aria-pressed", String(!ink));
  localStorage.setItem("preview-theme", ink ? "paper" : "ink");
  root.dispatchEvent(new Event("themechange"));
});

const langBtn = document.querySelector(".lang-toggle");
const langMenu = document.getElementById("lang-menu");
function closeLang() {
  langMenu.hidden = true;
  langBtn.setAttribute("aria-expanded", "false");
}
function placeLang() {
  langMenu.hidden = false;
  langMenu.style.left = "";
  langMenu.style.right = "";
  if (langMenu.getBoundingClientRect().left < 8) {
    langMenu.style.left = "0";
    langMenu.style.right = "auto";
  }
}
langBtn.addEventListener("click", () => {
  const willOpen = langMenu.hidden;
  if (willOpen) placeLang();
  else langMenu.hidden = true;
  langBtn.setAttribute("aria-expanded", String(willOpen));
});
document.addEventListener("click", (event) => {
  if (!event.target.closest(".lang")) closeLang();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeLang();
});

const menuBtn = document.getElementById("menu-toggle");
const drawer = document.getElementById("drawer");
menuBtn.addEventListener("click", () => {
  const open = drawer.classList.toggle("open");
  menuBtn.setAttribute("aria-expanded", String(open));
});
drawer.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    drawer.classList.remove("open");
    menuBtn.setAttribute("aria-expanded", "false");
  });
});

const greeting = document.querySelector(".lede");
if (greeting && greeting.textContent.startsWith("Hi!")) {
  greeting.innerHTML = greeting.innerHTML.replace(
    "Hi!",
    '<span id="rotating-greeting">Hi!</span>'
  );
  const el = document.getElementById("rotating-greeting");
  const greetings = ["Hi", "你好", "Hola", "Γεια", "Ciao", "Halò", "Merhaba", "Salut", "Hei"];

  function lockGreetingWidth() {
    const probe = document.createElement("span");
    probe.style.visibility = "hidden";
    probe.style.position = "absolute";
    probe.style.whiteSpace = "nowrap";
    el.parentNode.insertBefore(probe, el);
    let maxWidth = 0;
    greetings.forEach((word) => {
      probe.textContent = `${word}!`;
      maxWidth = Math.max(maxWidth, probe.offsetWidth);
    });
    probe.remove();
    el.style.display = "inline-block";
    el.style.whiteSpace = "nowrap";
    el.style.width = `${maxWidth}px`;
  }

  lockGreetingWidth();
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(lockGreetingWidth);
  }

  let greetingIndex = 0;
  setInterval(() => {
    greetingIndex = (greetingIndex + 1) % greetings.length;
    el.textContent = `${greetings[greetingIndex]}!`;
  }, 3000);
}

const lightbox = document.querySelector(".lightbox");
if (lightbox) {
  const preview = lightbox.querySelector("img");
  const captionBox = lightbox.querySelector(".lightbox-caption");
  const captionLabel = lightbox.querySelector(".lightbox-title");
  const placeLabel = lightbox.querySelector(".lightbox-place");
  let currentShot = null;

  function openShot(shot) {
    const image = shot.querySelector("img");
    preview.src = image.currentSrc || image.src;
    preview.alt = image.alt;
    const caption = shot.dataset.caption || "";
    const place = shot.dataset.place || "";
    captionLabel.textContent = caption;
    captionLabel.hidden = !caption;
    placeLabel.textContent = place;
    placeLabel.hidden = !place;
    captionBox.hidden = !caption && !place;
    captionBox.classList.toggle("place-only", !caption && !!place);
    lightbox.hidden = false;
    document.body.style.overflow = "hidden";
    currentShot = shot;
    lightbox.querySelector("[data-close]").focus();
  }

  function closeShot() {
    if (lightbox.hidden) return;
    lightbox.hidden = true;
    preview.removeAttribute("src");
    document.body.style.overflow = "";
    if (currentShot) currentShot.focus();
    currentShot = null;
  }

  document.querySelectorAll(".shot").forEach((shot) => {
    shot.addEventListener("click", () => openShot(shot));
  });
  lightbox.addEventListener("click", (event) => {
    if (event.target === lightbox || event.target.closest("[data-close]")) closeShot();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeShot();
  });
  document.querySelectorAll(".shot, .shot img, .lightbox, .lightbox img").forEach((node) => {
    node.addEventListener("contextmenu", (event) => event.preventDefault());
    node.addEventListener("dragstart", (event) => event.preventDefault());
  });
}

const mapEl = document.querySelector(".place-map");
const mapData = document.getElementById("place-map-data");
if (mapEl && mapData && window.L) {
  const pins = JSON.parse(mapData.textContent);
  const map = L.map(mapEl, { scrollWheelZoom: false });
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map);
  const markers = L.featureGroup();
  pins.forEach((pin) => {
    const marker = L.marker([pin.lat, pin.lon], {
      icon: L.divIcon({
        className: "pin",
        iconSize: [6, 6],
        iconAnchor: [3, 3],
        tooltipAnchor: [0, -4],
      }),
      alt: pin.name,
      keyboard: true,
    });
    const label = document.createElement("span");
    label.textContent = pin.name;
    marker.bindTooltip(label, { direction: "top", className: "pin-tip", opacity: 1 });
    marker.on("add", () => {
      const el = marker.getElement();
      if (el) el.setAttribute("aria-label", pin.name);
    });
    markers.addLayer(marker);
  });
  map.addLayer(markers);
  if (pins.length) map.fitBounds(markers.getBounds().pad(0.18), { padding: [24, 24] });
}

const papers = [...document.querySelectorAll(".paper")];
document.querySelectorAll("[data-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    const filter = button.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach((other) => {
      other.setAttribute("aria-pressed", String(other === button));
    });
    papers.forEach((paper) => {
      const tags = (paper.dataset.tags || "").split(" ").filter(Boolean);
      paper.hidden = filter !== "all" && !tags.includes(filter);
    });
  });
});
