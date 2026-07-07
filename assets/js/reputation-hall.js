(function () {
  'use strict';

  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function initReveal() {
    var cards = document.querySelectorAll('.reputation-reveal');
    if (!cards.length) {
      return;
    }

    if (prefersReduced || !('IntersectionObserver' in window)) {
      cards.forEach(function (card) {
        card.classList.add('is-visible');
      });
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.2 });

    cards.forEach(function (card) {
      observer.observe(card);
    });
  }

  function initBadgeTooltips() {
    var medals = document.querySelectorAll('.badge-medal');
    medals.forEach(function (medal) {
      medal.addEventListener('click', function () {
        var open = medal.classList.contains('is-tooltip-open');
        medals.forEach(function (item) {
          item.classList.remove('is-tooltip-open');
        });
        if (!open) {
          medal.classList.add('is-tooltip-open');
        }
      });
    });

    document.addEventListener('click', function (event) {
      if (!event.target.closest('.badge-medal')) {
        medals.forEach(function (item) {
          item.classList.remove('is-tooltip-open');
        });
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initReveal();
      initBadgeTooltips();
    });
  } else {
    initReveal();
    initBadgeTooltips();
  }
})();