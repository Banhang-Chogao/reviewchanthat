(() => {
  /* ── Mobile header menu ── */
  const menu = document.querySelector('.site-header__mobile-menu');
  if (menu) {
    const summary = menu.querySelector('summary');
    const dropdown = menu.querySelector('.site-header__mobile-dropdown');
    if (summary && dropdown) {
      function setExpanded(open) {
        summary.setAttribute('aria-expanded', open ? 'true' : 'false');
      }

      menu.addEventListener('toggle', () => {
        setExpanded(menu.open);
        if (menu.open) {
          const firstLink = dropdown.querySelector('a');
          if (firstLink) {
            firstLink.focus();
          }
        }
      });

      document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && menu.open) {
          menu.open = false;
          setExpanded(false);
          summary.focus();
        }
      });

      document.addEventListener('click', (event) => {
        if (!menu.open) {
          return;
        }
        if (!menu.contains(event.target)) {
          menu.open = false;
          setExpanded(false);
        }
      });

      setExpanded(menu.open);
    }
  }

  /* ── Footer Experimental gate ──
     Default: no experimental <a> in DOM (homepage / crawl only see blog + normal footer).
     Manual click "Load Experimental" injects tool links for this tab session only. */
  const STORAGE_KEY = 'rct_footer_experimental_loaded';
  const root = document.getElementById('footerExperimental');
  const loadBtn = document.getElementById('footerExperimentalLoad');
  const panel = document.getElementById('footerExperimentalPanel');
  const linksHost = document.getElementById('footerExperimentalLinks');
  const catalogEl = document.getElementById('footerExperimentalCatalog');

  if (!root || !loadBtn || !panel || !linksHost || !catalogEl) {
    return;
  }

  function readCatalog() {
    try {
      const data = JSON.parse(catalogEl.textContent || '[]');
      return Array.isArray(data) ? data : [];
    } catch (_) {
      return [];
    }
  }

  function injectLinks() {
    if (root.getAttribute('data-experimental-loaded') === '1') {
      return;
    }
    const items = readCatalog();
    const frag = document.createDocumentFragment();
    items.forEach((item) => {
      if (!item || !item.href || !item.label) return;
      const a = document.createElement('a');
      a.href = item.href;
      a.className = 'footer-nav-link footer-nav-link--featured';
      a.textContent = item.label;
      frag.appendChild(a);
    });
    linksHost.replaceChildren(frag);
    root.setAttribute('data-experimental-loaded', '1');
  }

  function showExperimental() {
    injectLinks();
    panel.hidden = false;
    loadBtn.setAttribute('aria-expanded', 'true');
    loadBtn.textContent = '🧪 Experimental loaded';
    loadBtn.title = 'Bấm lại để ẩn danh sách Experimental';
    try {
      sessionStorage.setItem(STORAGE_KEY, '1');
    } catch (_) { /* private mode */ }
  }

  function hideExperimental() {
    panel.hidden = true;
    // Remove anchors so crawlers/DOM snapshot stay clean if user hides again
    linksHost.replaceChildren();
    root.setAttribute('data-experimental-loaded', '0');
    loadBtn.setAttribute('aria-expanded', 'false');
    loadBtn.textContent = '🧪 Load Experimental';
    loadBtn.title = '';
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch (_) { /* private mode */ }
  }

  loadBtn.addEventListener('click', () => {
    if (panel.hidden) {
      showExperimental();
    } else {
      hideExperimental();
    }
  });

  // Do NOT auto-load on first paint. Only restore if user already opted-in this tab session.
  // (Still requires an earlier manual click in this browser tab.)
  try {
    if (sessionStorage.getItem(STORAGE_KEY) === '1') {
      showExperimental();
    }
  } catch (_) { /* ignore */ }
})();
