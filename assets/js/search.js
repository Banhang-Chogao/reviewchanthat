(() => {
  const body = document.body;
  const base = (body.dataset.siteBase || '/').replace(/\/?$/, '/');
  const indexUrl = `${base}search-index.json`;
  const searchRoot = document.getElementById('site-search');
  const toggle = document.getElementById('site-search-toggle');
  const panel = document.getElementById('site-search-panel');
  const input = document.getElementById('site-search-input');
  const results = document.getElementById('site-search-results');
  const closeBtn = document.getElementById('site-search-close');
  const hint = document.getElementById('site-search-hint');

  if (!searchRoot || !toggle || !panel || !input || !results) {
    return;
  }

  let index = [];
  let activeIndex = -1;
  let loaded = false;
  let timer = 0;

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  async function ensureIndex() {
    if (loaded) {
      return index;
    }
    try {
      const response = await fetch(indexUrl, { credentials: 'same-origin' });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      index = await response.json();
      loaded = true;
      if (hint) {
        hint.textContent = `${index.length} bài viết · Gõ để tìm · Enter mở · Esc đóng`;
      }
    } catch (error) {
      if (hint) {
        hint.textContent = 'Không tải được chỉ mục tìm kiếm.';
      }
      index = [];
      loaded = true;
    }
    return index;
  }

  function normalize(value) {
    return String(value || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
  }

  function scoreItem(item, query) {
    const haystack = normalize([item.title, item.description, ...(item.tags || []), ...(item.categories || []), item.author].join(' '));
    const needle = normalize(query);
    if (!needle) {
      return 0;
    }
    if (normalize(item.title).includes(needle)) {
      return 100;
    }
    if (haystack.includes(needle)) {
      return 50;
    }
    return 0;
  }

  function render(matches) {
    results.innerHTML = '';
    activeIndex = -1;
    if (!matches.length) {
      results.innerHTML = '<li class="site-search__empty">Không có kết quả phù hợp.</li>';
      return;
    }
    matches.slice(0, 8).forEach((item, index) => {
      const li = document.createElement('li');
      li.className = 'site-search__result';
      li.setAttribute('role', 'option');
      li.dataset.index = String(index);
      li.innerHTML = `
        <a class="site-search__result-link" href="${escapeHtml(item.url)}" tabindex="-1">
          <span class="site-search__result-title">${escapeHtml(item.title)}</span>
          <span class="site-search__result-meta">${escapeHtml((item.categories || []).join(' · ') || item.date || '')}</span>
        </a>
      `;
      results.append(li);
    });
  }

  function openSearch() {
    panel.hidden = false;
    toggle.setAttribute('aria-expanded', 'true');
    document.documentElement.classList.add('site-search-open');
    ensureIndex().then(() => {
      input.focus();
      runSearch(input.value);
    });
  }

  function closeSearch() {
    panel.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');
    document.documentElement.classList.remove('site-search-open');
    input.value = '';
    render([]);
    toggle.focus();
  }

  function runSearch(query) {
    const trimmed = query.trim();
    if (!trimmed) {
      render([]);
      return;
    }
    const matches = index
      .map((item) => ({ item, score: scoreItem(item, trimmed) }))
      .filter((entry) => entry.score > 0)
      .sort((a, b) => b.score - a.score)
      .map((entry) => entry.item);
    render(matches);
  }

  function moveActive(delta) {
    const items = [...results.querySelectorAll('.site-search__result-link')];
    if (!items.length) {
      return;
    }
    activeIndex = (activeIndex + delta + items.length) % items.length;
    items.forEach((node, index) => {
      node.parentElement.classList.toggle('is-active', index === activeIndex);
    });
    items[activeIndex].focus();
  }

  toggle.addEventListener('click', () => {
    if (panel.hidden) {
      openSearch();
    } else {
      closeSearch();
    }
  });

  closeBtn.addEventListener('click', closeSearch);

  input.addEventListener('input', () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => runSearch(input.value), 120);
  });

  input.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      moveActive(1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      moveActive(-1);
    } else if (event.key === 'Enter') {
      const active = results.querySelector('.site-search__result.is-active .site-search__result-link')
        || results.querySelector('.site-search__result-link');
      if (active) {
        window.location.href = active.getAttribute('href');
      }
    } else if (event.key === 'Escape') {
      closeSearch();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === '/' && panel.hidden && !/input|textarea|select/i.test(document.activeElement.tagName)) {
      event.preventDefault();
      openSearch();
    }
    if (event.key === 'Escape' && !panel.hidden) {
      closeSearch();
    }
  });

  panel.addEventListener('click', (event) => {
    if (event.target === panel) {
      closeSearch();
    }
  });
})();