document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".sitemap-posts").forEach((box) => {
    const input = box.querySelector(".sitemap-posts__search");
    const items = [...box.querySelectorAll(".sitemap-posts__item")];
    if (!input || !items.length) return;

    input.addEventListener("input", () => {
      const q = input.value.trim().toLowerCase();
      items.forEach((item) => {
        const text = item.textContent.toLowerCase();
        item.hidden = q && !text.includes(q);
      });
    });
  });
});
