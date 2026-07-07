(() => {
  const menu = document.querySelector('.site-header__mobile-menu');
  if (!menu) {
    return;
  }

  const summary = menu.querySelector('summary');
  const dropdown = menu.querySelector('.site-header__mobile-dropdown');
  if (!summary || !dropdown) {
    return;
  }

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
})();