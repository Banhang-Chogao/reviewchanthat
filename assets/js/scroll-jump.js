(() => {
  const root = document.querySelector('.scroll-jump');
  if (!root) {
    return;
  }

  const topTarget = document.getElementById('main-content');
  const endTarget = document.getElementById('site-footer');
  const topButton = root.querySelector('[data-scroll-target="top"]');
  const endButton = root.querySelector('[data-scroll-target="end"]');
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const showOffset = 280;

  function isScrollable() {
    return document.documentElement.scrollHeight - window.innerHeight > showOffset;
  }

  function setVisible(visible) {
    root.hidden = !visible;
  }

  function scrollToTarget(target) {
    if (!target) {
      window.scrollTo({ top: 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
      return;
    }

    target.scrollIntoView({
      behavior: prefersReducedMotion ? 'auto' : 'smooth',
      block: 'start'
    });

    if (target === topTarget) {
      topTarget.focus({ preventScroll: true });
    }
  }

  function updateVisibility() {
    setVisible(isScrollable() && window.scrollY > showOffset);
  }

  topButton?.addEventListener('click', () => {
    scrollToTarget(topTarget);
  });

  endButton?.addEventListener('click', () => {
    scrollToTarget(endTarget);
  });

  window.addEventListener('scroll', updateVisibility, { passive: true });
  window.addEventListener('resize', updateVisibility);
  updateVisibility();
})();