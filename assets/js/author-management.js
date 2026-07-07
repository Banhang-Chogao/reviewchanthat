(function() {
  'use strict';

  var STORAGE_KEY = 'reviewchanthat_authors_v1';
  var BASE_PATH = document.querySelector('base') ? document.querySelector('base').getAttribute('href') || '' : '';

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

  function init() {
    var toggleBtn = document.getElementById('author-manage-toggle');
    var panel = document.getElementById('author-management-panel');
    if (!toggleBtn || !panel) return;
    toggleBtn.addEventListener('click', function() {
      var isOpen = panel.style.display !== 'none';
      panel.style.display = isOpen ? 'none' : 'block';
      toggleBtn.textContent = isOpen ? 'Manage Authors' : 'Close';
      if (!isOpen) {
        var authors = loadAuthors();
        renderAuthors(authors);
      }
    });
    document.getElementById('author-save-btn').addEventListener('click', handleSave);
    document.getElementById('author-reset-btn').addEventListener('click', handleReset);
    document.getElementById('author-export-btn').addEventListener('click', handleExport);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
