(function() {
  'use strict';

  // Static gate only; not a replacement for real server-side authentication.
  var ACCESS_HASH = '46eaa26621e4955c1675b55d446c6d03325f458b59a465f898d42924010e7286';
  var SESSION_KEY = 'reviewchanthat_auth_unlocked';
  var STORAGE_KEY = 'reviewchanthat_authors_v1';
  var BASE_PATH = document.querySelector('base') ? document.querySelector('base').getAttribute('href') || '' : '';

  function sha256(str) {
    var buffer = new TextEncoder().encode(str);
    return crypto.subtle.digest('SHA-256', buffer).then(function(hash) {
      var hex = '';
      var bytes = new Uint8Array(hash);
      for (var i = 0; i < bytes.length; i++) {
        hex += bytes[i].toString(16).padStart(2, '0');
      }
      return hex;
    });
  }

  function getInitialAuthors() {
    try {
      var el = document.getElementById('author-data-json');
      if (el) {
        var data = JSON.parse(el.textContent);
        if (data && data.authors) return data.authors;
      }
    } catch (e) {}
    return [];
  }

  function loadAuthors() {
    try {
      var stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        var parsed = JSON.parse(stored);
        if (parsed && parsed.authors) return parsed.authors;
      }
    } catch (e) {}
    return getInitialAuthors();
  }

  function saveAuthors(authors) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ authors: authors }));
    } catch (e) {
      alert('Không thể lưu vào localStorage: ' + e.message);
    }
  }

  function exportJSON(authors) {
    return JSON.stringify({ authors: authors }, null, 2);
  }

  function copyToClipboard(text) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(function() {
        alert('Đã copy JSON vào clipboard!');
      }).catch(function() {
        fallbackCopy(text);
      });
    } else {
      fallbackCopy(text);
    }
  }

  function fallbackCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
      alert('Đã copy JSON vào clipboard!');
    } catch (e) {
      alert('Không thể copy, hãy dùng Export JSON để tải file.');
    }
    document.body.removeChild(ta);
  }

  function downloadJSON(text, filename) {
    var blob = new Blob([text], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename || 'authors.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function renderAuthors(authors) {
    var container = document.getElementById('author-list-container');
    if (!container) return;
    if (!authors || authors.length === 0) {
      container.innerHTML = '<p class="author-empty">Chưa có author nào.</p>';
      return;
    }
    var html = '';
    for (var i = 0; i < authors.length; i++) {
      var a = authors[i];
      html += '<div class="author-card" data-index="' + i + '">';
      html += '  <div class="author-card-header">';
      html += '    <div class="author-card-avatar-wrap">';
      html += '      <img src="' + escapeHtml(a.image || defaultAvatar(i)) + '" alt="" class="author-card-avatar" loading="lazy">';
      html += '    </div>';
      html += '    <div class="author-card-id">' + escapeHtml(a.id) + '</div>';
      html += '  </div>';
      html += '  <div class="author-card-body">';
      html += '    <label>Name</label>';
      html += '    <input type="text" class="author-input" data-field="name" value="' + escapeHtml(a.name || '') + '">';
      html += '    <label>Image URL</label>';
      html += '    <input type="text" class="author-input" data-field="image" value="' + escapeHtml(a.image || '') + '">';
      html += '    <label>Title</label>';
      html += '    <input type="text" class="author-input" data-field="title" value="' + escapeHtml(a.title || '') + '">';
      html += '    <label>Company</label>';
      html += '    <input type="text" class="author-input" data-field="company" value="' + escapeHtml(a.company || '') + '">';
      html += '    <label>Introduction</label>';
      html += '    <textarea class="author-textarea" data-field="intro" rows="3">' + escapeHtml(a.intro || '') + '</textarea>';
      html += '  </div>';
      html += '</div>';
    }
    container.innerHTML = html;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function defaultAvatar(index) {
    return BASE_PATH + 'images/authors/default.svg';
  }

  function collectFromDOM() {
    var container = document.getElementById('author-list-container');
    if (!container) return [];
    var cards = container.querySelectorAll('.author-card');
    var authors = [];
    for (var i = 0; i < cards.length; i++) {
      var card = cards[i];
      var idEl = card.querySelector('.author-card-id');
      if (!idEl) continue;
      var author = {
        id: idEl.textContent.trim(),
        name: getFieldValue(card, 'name'),
        image: getFieldValue(card, 'image'),
        title: getFieldValue(card, 'title'),
        company: getFieldValue(card, 'company'),
        intro: getFieldValue(card, 'intro')
      };
      authors.push(author);
    }
    return authors;
  }

  function getFieldValue(card, field) {
    var input = card.querySelector('[data-field="' + field + '"]');
    return input ? input.value.trim() : '';
  }

  function handleSave() {
    var authors = collectFromDOM();
    saveAuthors(authors);
    var btn = document.getElementById('author-save-btn');
    if (btn) {
      var orig = btn.textContent;
      btn.textContent = 'Saved!';
      btn.disabled = true;
      setTimeout(function() {
        btn.textContent = orig;
        btn.disabled = false;
      }, 1500);
    }
  }

  function handleReset() {
    if (!confirm('Reset all authors to default? Unsaved changes will be lost.')) return;
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {}
    var authors = getInitialAuthors();
    renderAuthors(authors);
    saveAuthors(authors);
  }

  function handleExport() {
    var authors = collectFromDOM();
    var json = exportJSON(authors);
    var overlay = document.createElement('div');
    overlay.className = 'author-export-overlay';
    overlay.innerHTML = '<div class="author-export-modal">'
      + '<h3>Export JSON</h3>'
      + '<textarea class="author-export-textarea" readonly rows="12">' + escapeHtml(json) + '</textarea>'
      + '<div class="author-export-actions">'
      + '  <button class="author-btn author-btn-primary" id="author-copy-btn">Copy JSON</button>'
      + '  <button class="author-btn author-btn-secondary" id="author-download-btn">Download File</button>'
      + '  <button class="author-btn author-btn-ghost" id="author-export-close">Close</button>'
      + '</div>'
      + '</div>';
    document.body.appendChild(overlay);
    document.getElementById('author-copy-btn').onclick = function() {
      copyToClipboard(json);
    };
    document.getElementById('author-download-btn').onclick = function() {
      downloadJSON(json, 'authors.json');
    };
    document.getElementById('author-export-close').onclick = function() {
      document.body.removeChild(overlay);
    };
    overlay.onclick = function(e) {
      if (e.target === overlay) document.body.removeChild(overlay);
    };
  }

  function unlockGate() {
    var gate = document.getElementById('author-gate');
    var panel = document.getElementById('author-management-panel');
    if (gate) gate.style.display = 'none';
    if (panel) panel.style.display = 'block';
    try { sessionStorage.setItem(SESSION_KEY, '1'); } catch (e) {}
    var authors = loadAuthors();
    renderAuthors(authors);
  }

  function handleUnlock() {
    var input = document.getElementById('author-gate-input');
    var errorEl = document.getElementById('author-gate-error');
    if (!input || !errorEl) return;
    var code = input.value.trim();
    if (code.length !== 4) {
      errorEl.style.display = 'block';
      return;
    }
    sha256(code).then(function(hash) {
      if (hash === ACCESS_HASH) {
        errorEl.style.display = 'none';
        unlockGate();
      } else {
        errorEl.style.display = 'block';
        input.value = '';
        input.focus();
      }
    });
  }

  function init() {
    var toggleBtn = document.getElementById('author-manage-toggle');
    var panel = document.getElementById('author-management-panel');
    var gate = document.getElementById('author-gate');
    var unlockBtn = document.getElementById('author-gate-unlock');
    var gateInput = document.getElementById('author-gate-input');

    if (!toggleBtn) return;

    var isUnlocked = false;
    try { isUnlocked = sessionStorage.getItem(SESSION_KEY) === '1'; } catch (e) {}

    if (isUnlocked) {
      if (gate) gate.style.display = 'none';
      if (panel) panel.style.display = 'block';
      var authors = loadAuthors();
      renderAuthors(authors);
    } else {
      if (panel) panel.style.display = 'none';
      if (gate) gate.style.display = 'block';
    }

    toggleBtn.addEventListener('click', function() {
      var currentlyUnlocked = false;
      try { currentlyUnlocked = sessionStorage.getItem(SESSION_KEY) === '1'; } catch (e) {}

      if (!currentlyUnlocked) {
        if (gate) gate.style.display = 'block';
        if (panel) panel.style.display = 'none';
        if (gateInput) { gateInput.value = ''; gateInput.focus(); }
        var errorEl = document.getElementById('author-gate-error');
        if (errorEl) errorEl.style.display = 'none';
        return;
      }

      var isOpen = panel && panel.style.display !== 'none';
      if (panel) panel.style.display = isOpen ? 'none' : 'block';
      toggleBtn.textContent = isOpen ? 'Manage Authors' : 'Close';
      if (!isOpen) {
        var authors = loadAuthors();
        renderAuthors(authors);
      }
    });

    if (unlockBtn) {
      unlockBtn.addEventListener('click', handleUnlock);
    }
    if (gateInput) {
      gateInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') handleUnlock();
      });
    }

    var saveBtn = document.getElementById('author-save-btn');
    if (saveBtn) saveBtn.addEventListener('click', handleSave);
    var resetBtn = document.getElementById('author-reset-btn');
    if (resetBtn) resetBtn.addEventListener('click', handleReset);
    var exportBtn = document.getElementById('author-export-btn');
    if (exportBtn) exportBtn.addEventListener('click', handleExport);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
