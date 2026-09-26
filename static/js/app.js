// Small Alpine components shared across pages.
document.addEventListener("alpine:init", () => {
  // Ctrl/⌘+K quick search.
  Alpine.data("palette", () => ({
    open: false,
    toggle() {
      this.open = !this.open;
      if (this.open) this.$nextTick(() => document.getElementById("palette-input")?.focus());
    },
  }));

  Alpine.data("theme", () => ({
    dark: document.documentElement.classList.contains("dark"),
    toggle() {
      this.dark = !this.dark;
      document.documentElement.classList.toggle("dark", this.dark);
      try { localStorage.setItem("theme", this.dark ? "dark" : "light"); } catch (e) {}
    },
  }));

  Alpine.data("toast", (delay = 6000) => ({
    show: true,
    init() { setTimeout(() => (this.show = false), delay); },
  }));

  Alpine.data("stars", (initial = 0) => ({
    value: initial,
    hover: 0,
    get shown() { return this.hover || this.value; },
  }));

  Alpine.data("unwrap", () => ({
    opened: false,
    open() { this.opened = true; this.confetti(); },
    confetti() {
      if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const colors = ["#d9481c", "#e3a72f", "#1f6f6b", "#6b2f5b", "#f7c6c7"];
      for (let i = 0; i < 60; i++) {
        const p = document.createElement("span");
        p.style.cssText = `position:fixed;top:-12px;left:${Math.random() * 100}vw;width:8px;height:14px;` +
          `background:${colors[i % colors.length]};z-index:60;border-radius:2px;pointer-events:none;` +
          `animation:confetti ${1.8 + Math.random() * 1.6}s cubic-bezier(.2,.6,.4,1) ${Math.random() * .4}s forwards`;
        document.body.appendChild(p);
        setTimeout(() => p.remove(), 4000);
      }
    },
  }));
});

// Covers from Open Library that don't exist fall back to the generated cover.
document.addEventListener("error", (e) => {
  if (e.target.tagName === "IMG" && e.target.dataset.cover !== undefined) e.target.remove();
}, true);
