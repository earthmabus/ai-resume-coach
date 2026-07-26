(() => {
  "use strict";

  const rotator = document.querySelector("[data-hero-rotator]");
  if (!rotator) return;

  const scenes = Array.from(rotator.querySelectorAll("[data-hero-scene]"));
  const dots = Array.from(rotator.querySelectorAll("[data-hero-dot]"));
  const captionKicker = rotator.querySelector("[data-hero-caption-kicker]");
  const caption = rotator.querySelector("[data-hero-caption]");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const slides = [
    {
      kicker: "Launch your strategy",
      caption: "Turn career direction into forward motion.",
    },
    {
      kicker: "See the opportunity",
      caption: "Match your experience to roles with confidence.",
    },
  ];

  let activeIndex = 0;
  let timerId = null;

  function showSlide(index, { restart = false } = {}) {
    activeIndex = (index + scenes.length) % scenes.length;

    scenes.forEach((scene, sceneIndex) => {
      const active = sceneIndex === activeIndex;
      scene.classList.toggle("is-active", active);
      scene.setAttribute("aria-hidden", String(!active));
    });

    dots.forEach((dot, dotIndex) => {
      const active = dotIndex === activeIndex;
      dot.classList.toggle("is-active", active);
      dot.setAttribute("aria-pressed", String(active));
    });

    const slide = slides[activeIndex];
    if (captionKicker) captionKicker.textContent = slide.kicker;
    if (caption) caption.textContent = slide.caption;

    if (restart) startRotation();
  }

  function stopRotation() {
    if (timerId !== null) {
      window.clearInterval(timerId);
      timerId = null;
    }
  }

  function startRotation() {
    stopRotation();
    if (reduceMotion.matches || scenes.length < 2) return;
    timerId = window.setInterval(() => showSlide(activeIndex + 1), 10000);
  }

  dots.forEach((dot, index) => {
    dot.addEventListener("click", () => showSlide(index, { restart: true }));
  });

  rotator.addEventListener("mouseenter", stopRotation);
  rotator.addEventListener("mouseleave", startRotation);
  rotator.addEventListener("focusin", stopRotation);
  rotator.addEventListener("focusout", (event) => {
    if (!rotator.contains(event.relatedTarget)) startRotation();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stopRotation();
    else startRotation();
  });
  reduceMotion.addEventListener?.("change", startRotation);

  showSlide(0);
  startRotation();
})();
