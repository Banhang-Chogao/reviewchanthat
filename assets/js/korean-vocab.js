/**
 * Korean Specialized Vocabulary
 * Auth: SHA-256 PIN (same as Movie Calendar / Visa Promo = 0512)
 * Persistence: GitHub Contents API via personal token — permanent save
 */
(function () {
  'use strict';

  var ACCESS_HASH = '78c72f67941a420cd4e5ee9fdabcaeaba6d72f16160915085f9802220fd83799';
  var SESSION_KEY = 'kv_unlocked';
  var TOKEN_KEY = 'kv_gh_token';
  var GH_OWNER = 'banhang-chogao';
  var GH_REPO = 'reviewchanthat';
  var GH_PATH = 'data/korean-vocab.json';
  var GH_BRANCH = 'main';
  var CACHE_KEY = 'kv_local_cache_v1';

  var HEADERS = ['Tiếng Hàn', 'Tiếng Việt', 'Tiếng Anh', 'Lĩnh vực', 'Ghi chú', 'Đã học thuộc'];
  var HEADER_KEYS = {
    'tieng han': 'korean',
    'tiếng hàn': 'korean',
    'korean': 'korean',
    'hangul': 'korean',
    'han': 'korean',
    'tieng viet': 'vietnamese',
    'tiếng việt': 'vietnamese',
    'vietnamese': 'vietnamese',
    'viet': 'vietnamese',
    'tieng anh': 'english',
    'tiếng anh': 'english',
    'english': 'english',
    'anh': 'english',
    'linh vuc': 'field',
    'lĩnh vực': 'field',
    'field': 'field',
    'domain': 'field',
    'category': 'field',
    'ghi chu': 'notes',
    'ghi chú': 'notes',
    'notes': 'notes',
    'note': 'notes',
    'da hoc thuoc': 'learned',
    'đã học thuộc': 'learned',
    'learned': 'learned',
    'memorized': 'learned'
  };

  var S = {
    items: [],
    auditLog: [],
    lastSyncAt: null,
    filtered: [],
    editingId: null
  };
  var pendingImport = null;

  function $(id) { return document.getElementById(id); }
  function on(el, ev, fn) { if (el) el.addEventListener(ev, fn); }
  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }
  function gId() {
    if (crypto.randomUUID) return crypto.randomUUID();
    return 'kv_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }
  function sha256(str) {
    return crypto.subtle.digest('SHA-256', new TextEncoder().encode(str)).then(function (buf) {
      var hex = '', b = new Uint8Array(buf);
      for (var i = 0; i < b.length; i++) hex += b[i].toString(16).padStart(2, '0');
      return hex;
    });
  }
  function yesNo(v) {
    if (v === true || v === 1) return true;
    var s = String(v == null ? '' : v).trim().toLowerCase();
    return s === 'yes' || s === 'y' || s === 'true' || s === '1' || s === 'x' || s === '✓' || s === 'đã' || s === 'da';
  }
  function normHeader(h) {
    return String(h || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^\w\sàáạảãâăèéẹẻẽêìíịỉĩòóọỏõôơùúụủũưỳýỵỷỹđ]/gi, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }
  function mapHeader(h) {
    var n = normHeader(h);
    if (HEADER_KEYS[n]) return HEADER_KEYS[n];
    // fuzzy
    if (/han|korean|hangul/.test(n)) return 'korean';
    if (/viet|vietnamese/.test(n)) return 'vietnamese';
    if (/anh|english|eng/.test(n)) return 'english';
    if (/linh|field|domain|nganh/.test(n)) return 'field';
    if (/ghi|note/.test(n)) return 'notes';
    if (/hoc|learn|memo/.test(n)) return 'learned';
    return '';
  }

  function normalizeItem(raw) {
    raw = raw || {};
    return {
      id: raw.id || gId(),
      korean: String(raw.korean || raw.Korean || raw['Tiếng Hàn'] || '').trim(),
      vietnamese: String(raw.vietnamese || raw.Vietnamese || raw['Tiếng Việt'] || '').trim(),
      english: String(raw.english || raw.English || raw['Tiếng Anh'] || '').trim(),
      field: String(raw.field || raw.Field || raw['Lĩnh vực'] || '').trim(),
      notes: String(raw.notes || raw.Notes || raw['Ghi chú'] || '').trim(),
      learned: !!(raw.learned === true || raw.learned === 1 || yesNo(raw.learned) || yesNo(raw['Đã học thuộc'])),
      updatedAt: raw.updatedAt || new Date().toISOString()
    };
  }

  function getToken() { return localStorage.getItem(TOKEN_KEY) || ''; }
  function setToken(t) {
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
  }
  function getGHReadURL() {
    return 'https://raw.githubusercontent.com/' + GH_OWNER + '/' + GH_REPO + '/' + GH_BRANCH + '/' + GH_PATH + '?_=' + Date.now();
  }
  function getGHAPIURL() {
    return 'https://api.github.com/repos/' + GH_OWNER + '/' + GH_REPO + '/contents/' + GH_PATH;
  }
  function utf8ToB64(str) { return btoa(unescape(encodeURIComponent(str))); }

  function payload() {
    return {
      version: 1,
      items: S.items,
      auditLog: (S.auditLog || []).slice(0, 200),
      lastSyncAt: S.lastSyncAt,
      updatedAt: new Date().toISOString()
    };
  }
  function cacheLocal() {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify(payload())); } catch (e) {}
  }
  function loadLocalCache() {
    try {
      var raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return false;
      applyData(JSON.parse(raw));
      return true;
    } catch (e) { return false; }
  }
  function applyData(d) {
    if (!d || typeof d !== 'object') {
      S.items = [];
      S.auditLog = [];
      return;
    }
    S.items = Array.isArray(d.items) ? d.items.map(normalizeItem) : [];
    S.auditLog = Array.isArray(d.auditLog) ? d.auditLog : [];
    S.lastSyncAt = d.lastSyncAt || null;
  }
  function audit(action, detail) {
    S.auditLog.unshift({
      at: new Date().toISOString(),
      action: action,
      detail: detail || '',
      by: 'local-user'
    });
    if (S.auditLog.length > 200) S.auditLog.length = 200;
  }
  function setSync(text) {
    var el = $('kvSyncLabel');
    if (el) el.textContent = text;
  }
  function setProgress(show, pct, text, sha, isErr) {
    var pb = $('kvProgress'), pf = $('kvProgressFill'), pt = $('kvProgressText'), ps = $('kvProgressSha');
    if (!pb) return;
    pb.hidden = !show;
    if (pf) {
      pf.style.width = (pct || 0) + '%';
      pf.style.background = isErr ? '#ef4444' : '';
    }
    if (pt) pt.textContent = text || '';
    if (ps) ps.textContent = sha || '';
  }
  function setIoStatus(kind, msg) {
    var el = $('kvIoStatus');
    if (!el) return;
    el.hidden = false;
    el.className = 'kv-status kv-status--' + (kind === 'ok' ? 'ok' : kind === 'warn' ? 'warn' : 'err');
    el.textContent = msg;
  }
  function nowLabel() {
    return new Date().toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' });
  }

  function loadFromGitHub() {
    return fetch(getGHReadURL(), { cache: 'no-cache' })
      .then(function (r) {
        if (r.status === 404) return null;
        if (!r.ok) throw new Error('GitHub read failed: ' + r.status);
        return r.json();
      })
      .then(function (d) {
        if (!d) return false;
        applyData(d);
        cacheLocal();
        return true;
      });
  }

  function saveToGitHub() {
    var token = getToken();
    if (!token) {
      promptToken();
      token = getToken();
      if (!token) return Promise.reject(new Error('No token'));
    }
    var data = payload();
    var content = utf8ToB64(JSON.stringify(data, null, 2) + '\n');
    setProgress(true, 20, '🔍 Connecting GitHub…');
    setSync('Saving…');
    var api = getGHAPIURL();
    return fetch(api, { headers: { Accept: 'application/vnd.github.v3+json' } })
      .then(function (r) {
        if (r.status === 404) return null;
        if (!r.ok) throw new Error('Get SHA failed: ' + r.status);
        return r.json();
      })
      .then(function (existing) {
        setProgress(true, 55, '📤 Committing ' + S.items.length + ' terms…');
        var body = {
          message: 'korean-vocab: save ' + S.items.length + ' terms',
          content: content,
          branch: GH_BRANCH
        };
        if (existing && existing.sha) body.sha = existing.sha;
        return fetch(api, {
          method: 'PUT',
          headers: {
            Authorization: 'token ' + token,
            'Content-Type': 'application/json',
            Accept: 'application/vnd.github.v3+json'
          },
          body: JSON.stringify(body)
        });
      })
      .then(function (r) {
        if (!r.ok) {
          return r.json().then(function (e) {
            throw new Error((e && e.message) || ('Write failed ' + r.status));
          });
        }
        return r.json();
      })
      .then(function (res) {
        var sha = (res.content && res.content.sha) || '';
        var short = sha.slice(0, 7);
        S.lastSyncAt = new Date().toISOString();
        cacheLocal();
        setProgress(true, 100, '✅ Saved to GitHub', short ? 'Commit: ' + short : '');
        setSync('GitHub · ' + (short || nowLabel()));
        audit('save', 'GitHub commit ' + short + ' · ' + S.items.length + ' terms');
        setTimeout(function () { setProgress(false); }, 2000);
        return res;
      })
      ['catch'](function (err) {
        setProgress(true, 100, '❌ ' + (err.message || err), '', true);
        setSync('Save error');
        setTimeout(function () { setProgress(false); }, 4500);
        throw err;
      });
  }

  function promptToken() {
    var t = prompt('GitHub Personal Access Token (contents:write) — lưu trên trình duyệt, không hardcode:', getToken() || '');
    if (t !== null) {
      setToken(String(t).trim());
      setIoStatus('ok', '✓ Token đã lưu trên trình duyệt (localStorage).');
    }
  }

  /* ── Excel ─────────────────────────────────────────────── */
  function ensureXLSX() {
    if (typeof XLSX === 'undefined') {
      setIoStatus('err', '✗ Thư viện Excel chưa tải. Thử lại sau vài giây.');
      return false;
    }
    return true;
  }

  function itemToRow(it) {
    return [
      it.korean || '',
      it.vietnamese || '',
      it.english || '',
      it.field || '',
      it.notes || '',
      it.learned ? 'Yes' : ''
    ];
  }

  function downloadTemplate() {
    if (!ensureXLSX()) return;
    var sample = ['계약서', 'Hợp đồng', 'Contract', 'Pháp lý', 'Dùng trong hợp đồng lao động / mua bán', ''];
    var instr = [
      'Bắt buộc: Tiếng Hàn + Tiếng Việt',
      'Cột Đã học thuộc: Yes / x / 1 = đã thuộc',
      'Import: Append / Replace / Update',
      '',
      '',
      ''
    ];
    var aoa = [HEADERS.slice(), instr, sample];
    var ws = XLSX.utils.aoa_to_sheet(aoa);
    ws['!cols'] = [
      { wch: 18 }, { wch: 22 }, { wch: 18 }, { wch: 16 }, { wch: 36 }, { wch: 14 }
    ];
    var wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Korean Vocab');
    XLSX.writeFile(wb, 'Tu_vung_Han_chuyen_nganh_Template.xlsx');
    setIoStatus('ok', '✓ Đã tải mẫu Excel (sheet “Korean Vocab”, 1 dòng mẫu).');
  }

  function exportData(filename) {
    if (!ensureXLSX()) return;
    var aoa = [HEADERS.slice()].concat(S.items.map(itemToRow));
    var ws = XLSX.utils.aoa_to_sheet(aoa);
    ws['!cols'] = [
      { wch: 18 }, { wch: 22 }, { wch: 18 }, { wch: 16 }, { wch: 36 }, { wch: 14 }
    ];
    var wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Korean Vocab');
    XLSX.writeFile(wb, filename || 'Tu_vung_Han_chuyen_nganh_Export.xlsx');
    setIoStatus('ok', '✓ Đã export ' + S.items.length + ' dòng.');
  }

  function exportCsv() {
    var lines = [HEADERS.join(',')];
    S.items.forEach(function (it) {
      lines.push(itemToRow(it).map(function (c) {
        var s = String(c == null ? '' : c);
        if (/[",\n]/.test(s)) s = '"' + s.replace(/"/g, '""') + '"';
        return s;
      }).join(','));
    });
    var blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'tu-vung-han-chuyen-nganh.csv';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function parseSheetRows(rows) {
    if (!rows || !rows.length) return { valid: [], invalid: [], report: 'Empty sheet' };
    var headerRow = rows[0] || [];
    var colMap = {};
    headerRow.forEach(function (h, i) {
      var key = mapHeader(h);
      if (key) colMap[i] = key;
    });
    var hasKo = Object.keys(colMap).some(function (i) { return colMap[i] === 'korean'; });
    var hasVi = Object.keys(colMap).some(function (i) { return colMap[i] === 'vietnamese'; });
    if (!hasKo || !hasVi) {
      return {
        valid: [],
        invalid: [],
        report: 'Header thiếu “Tiếng Hàn” hoặc “Tiếng Việt”. Cần đúng template.'
      };
    }
    var valid = [];
    var invalid = [];
    for (var r = 1; r < rows.length; r++) {
      var row = rows[r] || [];
      var obj = {};
      Object.keys(colMap).forEach(function (i) {
        obj[colMap[i]] = row[i];
      });
      // skip instruction-like rows
      var ko = String(obj.korean || '').trim();
      var vi = String(obj.vietnamese || '').trim();
      if (!ko && !vi) continue;
      if (/^bắt buộc|^bat buoc|^cột |^cot /i.test(ko + ' ' + vi)) continue;
      var item = normalizeItem(obj);
      var errs = [];
      if (!item.korean) errs.push('Thiếu Tiếng Hàn');
      if (!item.vietnamese) errs.push('Thiếu Tiếng Việt');
      if (errs.length) {
        invalid.push({ item: item, errors: errs, row: r + 1 });
      } else {
        valid.push({ item: item, errors: [], row: r + 1 });
      }
    }
    return {
      valid: valid,
      invalid: invalid,
      report: 'Valid: ' + valid.length + ' · Invalid: ' + invalid.length
    };
  }

  function openImportPreview(result) {
    pendingImport = result;
    var modal = $('kvImportModal');
    if (modal) modal.hidden = false;
    var body = $('kvImportBody');
    if (!body) return;
    body.innerHTML = '';
    var rows = (result.valid || []).concat(result.invalid || []);
    rows.forEach(function (x) {
      var it = x.item;
      var tr = document.createElement('tr');
      if (x.errors && x.errors.length) tr.className = 'is-invalid';
      tr.innerHTML =
        '<td class="kv-ko">' + esc(it.korean) + '</td>' +
        '<td>' + esc(it.vietnamese) + '</td>' +
        '<td>' + esc(it.english) + '</td>' +
        '<td>' + esc(it.field) + '</td>' +
        '<td class="kv-notes">' + esc(it.notes) + '</td>' +
        '<td>' + esc((x.errors && x.errors.length) ? x.errors.join('; ') : (it.learned ? 'OK · learned' : 'OK')) + '</td>';
      body.appendChild(tr);
    });
    var rep = $('kvImportReport');
    if (rep) {
      rep.textContent = (result.report || '') + '\n' +
        ((result.invalid || []).slice(0, 10).map(function (x) {
          return '• Row ' + x.row + ': ' + (x.errors || []).join(', ');
        }).join('\n') || 'All valid rows ready.');
    }
    setIoStatus('ok', '✓ Parse xong — review preview rồi Confirm import.');
  }

  function closeImportPreview() {
    pendingImport = null;
    var modal = $('kvImportModal');
    if (modal) modal.hidden = true;
  }

  function confirmImport() {
    if (!pendingImport || !(pendingImport.valid || []).length) {
      setIoStatus('err', '✗ Không có dòng hợp lệ để import.');
      return;
    }
    var mode = (document.querySelector('input[name="kvImportMode"]:checked') || {}).value || 'append';
    var incoming = pendingImport.valid.map(function (x) { return normalizeItem(x.item); });
    var report = { imported: 0, updated: 0, skipped: 0 };

    if (mode === 'replace') {
      S.items = incoming;
      report.imported = incoming.length;
    } else if (mode === 'update') {
      var byKey = {};
      S.items.forEach(function (it, i) {
        byKey[fp(it)] = i;
      });
      incoming.forEach(function (it) {
        var k = fp(it);
        if (byKey[k] != null) {
          var keepId = S.items[byKey[k]].id;
          var merged = Object.assign({}, S.items[byKey[k]], it, { id: keepId });
          S.items[byKey[k]] = merged;
          report.updated += 1;
        } else {
          S.items.push(it);
          report.imported += 1;
          byKey[k] = S.items.length - 1;
        }
      });
    } else {
      // append
      var existing = {};
      S.items.forEach(function (it) { existing[fp(it)] = 1; });
      incoming.forEach(function (it) {
        if (existing[fp(it)]) {
          report.skipped += 1;
          return;
        }
        S.items.push(it);
        existing[fp(it)] = 1;
        report.imported += 1;
      });
    }

    audit('import-excel', mode + ' · +' + report.imported + ' ~' + report.updated + ' skip ' + report.skipped);
    cacheLocal();
    closeImportPreview();
    renderAll();
    setIoStatus('ok', '✓ Import xong — Imported: ' + report.imported +
      ', Updated: ' + report.updated + ', Skipped: ' + report.skipped +
      '. Nhớ 💾 Save to GitHub để lưu vĩnh viễn.');
  }

  function fp(it) {
    return String(it.korean || '').trim().toLowerCase() + '|' + String(it.vietnamese || '').trim().toLowerCase();
  }

  function handleImportFile(file) {
    if (!file) return;
    var name = file.name || '';
    if (/\.csv$/i.test(name)) {
      var reader = new FileReader();
      reader.onload = function (ev) {
        var text = String(ev.target.result || '');
        var rows = text.split(/\r?\n/).map(function (line) {
          // simple CSV split with quotes
          var out = [], cur = '', q = false;
          for (var i = 0; i < line.length; i++) {
            var ch = line[i];
            if (ch === '"') {
              if (q && line[i + 1] === '"') { cur += '"'; i++; }
              else q = !q;
            } else if (ch === ',' && !q) {
              out.push(cur); cur = '';
            } else cur += ch;
          }
          out.push(cur);
          return out;
        }).filter(function (r) { return r.some(function (c) { return String(c).trim(); }); });
        openImportPreview(parseSheetRows(rows));
      };
      reader.readAsText(file, 'UTF-8');
      return;
    }
    if (!ensureXLSX()) return;
    if (!/\.xlsx$/i.test(name)) {
      setIoStatus('err', '✗ Chỉ hỗ trợ .xlsx hoặc .csv');
      return;
    }
    var fr = new FileReader();
    fr.onload = function (ev) {
      try {
        var wb = XLSX.read(new Uint8Array(ev.target.result), { type: 'array' });
        var sheet = wb.Sheets[wb.SheetNames[0]];
        var rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '', raw: false });
        openImportPreview(parseSheetRows(rows));
      } catch (err) {
        setIoStatus('err', '✗ Không đọc được Excel: ' + (err.message || err));
      }
    };
    fr.readAsArrayBuffer(file);
  }

  /* ── Form ──────────────────────────────────────────────── */
  function showForm(item) {
    var panel = $('kvFormPanel');
    if (panel) panel.hidden = false;
    S.editingId = item ? item.id : null;
    $('kvFormTitle').textContent = item ? 'Sửa từ vựng' : 'Thêm từ vựng';
    $('kvFieldId').value = item ? item.id : '';
    $('kvFieldKo').value = item ? item.korean : '';
    $('kvFieldVi').value = item ? item.vietnamese : '';
    $('kvFieldEn').value = item ? item.english : '';
    $('kvFieldField').value = item ? item.field : '';
    $('kvFieldNotes').value = item ? item.notes : '';
    $('kvFieldLearned').checked = !!(item && item.learned);
    var del = $('kvFormDelete');
    if (del) del.hidden = !item;
    $('kvFieldKo').focus();
  }
  function hideForm() {
    var panel = $('kvFormPanel');
    if (panel) panel.hidden = true;
    S.editingId = null;
    var form = $('kvForm');
    if (form) form.reset();
    var del = $('kvFormDelete');
    if (del) del.hidden = true;
  }
  function saveForm(ev) {
    if (ev) ev.preventDefault();
    var item = normalizeItem({
      id: $('kvFieldId').value || gId(),
      korean: $('kvFieldKo').value,
      vietnamese: $('kvFieldVi').value,
      english: $('kvFieldEn').value,
      field: $('kvFieldField').value,
      notes: $('kvFieldNotes').value,
      learned: $('kvFieldLearned').checked
    });
    if (!item.korean || !item.vietnamese) {
      setIoStatus('err', '✗ Tiếng Hàn và Tiếng Việt là bắt buộc.');
      return;
    }
    var idx = S.items.findIndex(function (x) { return x.id === item.id; });
    if (idx >= 0) {
      S.items[idx] = item;
      audit('update', item.korean);
      setIoStatus('ok', '✓ Đã cập nhật: ' + item.korean);
    } else {
      S.items.unshift(item);
      audit('add', item.korean);
      setIoStatus('ok', '✓ Đã thêm: ' + item.korean + '. Nhớ 💾 Save to GitHub.');
    }
    cacheLocal();
    hideForm();
    renderAll();
  }
  function deleteCurrent() {
    if (!S.editingId) return;
    if (!confirm('Xóa từ này?')) return;
    var id = S.editingId;
    var found = S.items.find(function (x) { return x.id === id; });
    S.items = S.items.filter(function (x) { return x.id !== id; });
    audit('delete', found ? found.korean : id);
    cacheLocal();
    hideForm();
    renderAll();
    setIoStatus('ok', '✓ Đã xóa. Nhớ Save to GitHub nếu muốn đồng bộ.');
  }

  /* ── Dashboard ─────────────────────────────────────────── */
  function getFilters() {
    return {
      q: (($('kvSearch') && $('kvSearch').value) || '').trim().toLowerCase(),
      field: (($('kvFilterField') && $('kvFilterField').value) || '').trim(),
      learned: (($('kvFilterLearned') && $('kvFilterLearned').value) || '').trim()
    };
  }

  function applyFilters() {
    var f = getFilters();
    S.filtered = S.items.filter(function (it) {
      if (f.field && it.field !== f.field) return false;
      if (f.learned === 'yes' && !it.learned) return false;
      if (f.learned === 'no' && it.learned) return false;
      if (f.q) {
        var blob = [it.korean, it.vietnamese, it.english, it.field, it.notes].join(' ').toLowerCase();
        if (blob.indexOf(f.q) === -1) return false;
      }
      return true;
    });
  }

  function renderKpis() {
    var el = $('kvKpis');
    if (!el) return;
    var total = S.items.length;
    var learned = S.items.filter(function (x) { return x.learned; }).length;
    var fields = {};
    S.items.forEach(function (x) {
      var k = x.field || '—';
      fields[k] = (fields[k] || 0) + 1;
    });
    var fieldCount = Object.keys(fields).length;
    var pct = total ? Math.round((learned / total) * 100) : 0;
    el.innerHTML =
      '<div class="kv-kpi"><div class="kv-kpi__label">Tổng từ</div><div class="kv-kpi__value">' + total + '</div></div>' +
      '<div class="kv-kpi"><div class="kv-kpi__label">Đã học thuộc</div><div class="kv-kpi__value">' + learned + '</div></div>' +
      '<div class="kv-kpi"><div class="kv-kpi__label">Chưa thuộc</div><div class="kv-kpi__value">' + (total - learned) + '</div></div>' +
      '<div class="kv-kpi"><div class="kv-kpi__label">Tiến độ</div><div class="kv-kpi__value">' + pct + '%</div></div>' +
      '<div class="kv-kpi"><div class="kv-kpi__label">Lĩnh vực</div><div class="kv-kpi__value">' + fieldCount + '</div></div>';
  }

  function fillFieldFilter() {
    var sel = $('kvFilterField');
    if (!sel) return;
    var cur = sel.value;
    var set = {};
    S.items.forEach(function (it) {
      if (it.field) set[it.field] = 1;
    });
    var opts = Object.keys(set).sort(function (a, b) { return a.localeCompare(b, 'vi'); });
    sel.innerHTML = '<option value="">Lĩnh vực: Tất cả</option>' +
      opts.map(function (f) { return '<option value="' + esc(f) + '">' + esc(f) + '</option>'; }).join('');
    if (cur) sel.value = cur;
  }

  function renderDashboard() {
    applyFilters();
    renderKpis();
    fillFieldFilter();
    var body = $('kvDashBody');
    var empty = $('kvDashEmpty');
    if (!body) return;
    body.innerHTML = '';
    if (!S.filtered.length) {
      if (empty) empty.hidden = false;
      return;
    }
    if (empty) empty.hidden = true;
    S.filtered.forEach(function (it) {
      var tr = document.createElement('tr');
      if (it.learned) tr.className = 'is-learned';
      tr.innerHTML =
        '<td><div class="kv-ko">' + esc(it.korean) + '</div>' +
          '<div class="kv-row-actions">' +
          '<button type="button" class="kv-link-btn" data-edit="' + esc(it.id) + '">Sửa</button>' +
          '</div></td>' +
        '<td>' + esc(it.vietnamese) + '</td>' +
        '<td>' + esc(it.english) + '</td>' +
        '<td>' + esc(it.field || '—') + '</td>' +
        '<td class="kv-notes">' + esc(it.notes || '') + '</td>' +
        '<td class="kv-col-learned">' +
          '<input type="checkbox" class="kv-learn-check" data-learn="' + esc(it.id) + '" ' +
          (it.learned ? 'checked' : '') + ' title="Tick khi đã học thuộc" aria-label="Đã học thuộc: ' + esc(it.korean) + '">' +
        '</td>';
      body.appendChild(tr);
    });
  }

  function toggleLearned(id, checked) {
    var it = S.items.find(function (x) { return x.id === id; });
    if (!it) return;
    it.learned = !!checked;
    it.updatedAt = new Date().toISOString();
    audit(checked ? 'learned' : 'unlearned', it.korean);
    cacheLocal();
    renderDashboard();
  }

  function renderAll() {
    renderDashboard();
    if (S.lastSyncAt) setSync('Synced · ' + new Date(S.lastSyncAt).toLocaleString('vi-VN', { hour12: false }));
  }

  /* ── Tabs & gate ───────────────────────────────────────── */
  function switchTab(name) {
    document.querySelectorAll('.kv-tabs__btn').forEach(function (b) {
      b.classList.toggle('is-active', b.getAttribute('data-tab') === name);
    });
    document.querySelectorAll('.kv-panel').forEach(function (p) {
      var onP = p.getAttribute('data-panel') === name;
      p.hidden = !onP;
      p.classList.toggle('is-active', onP);
    });
    if (name === 'dashboard') renderDashboard();
  }

  function showApp() {
    var gate = $('kvGate');
    var app = $('kvApp');
    if (gate) gate.style.display = 'none';
    if (app) {
      app.hidden = false;
      app.style.display = '';
    }
  }
  function hideApp() {
    var gate = $('kvGate');
    var app = $('kvApp');
    if (gate) gate.style.display = '';
    if (app) {
      app.hidden = true;
      app.style.display = 'none';
    }
    sessionStorage.removeItem(SESSION_KEY);
  }

  function tryUnlock() {
    var input = $('kvGateInput');
    var err = $('kvGateError');
    var code = (input && input.value) || '';
    if (!/^\d{4}$/.test(code)) {
      if (err) err.textContent = 'Nhập đúng 4 chữ số.';
      return;
    }
    sha256(code).then(function (hash) {
      if (hash !== ACCESS_HASH) {
        if (err) err.textContent = 'Mã không đúng.';
        return;
      }
      sessionStorage.setItem(SESSION_KEY, '1');
      if (err) err.textContent = '';
      showApp();
      bootstrapData();
    });
  }

  function bootstrapData() {
    loadLocalCache();
    renderAll();
    setSync('Loading GitHub…');
    loadFromGitHub()
      .then(function (ok) {
        renderAll();
        setSync(ok ? ('GitHub · ' + nowLabel()) : 'Local only');
      })
      ['catch'](function () {
        setSync('Offline · local cache');
        renderAll();
      });
  }

  function initEvents() {
    on($('kvGateUnlock'), 'click', tryUnlock);
    on($('kvGateInput'), 'keydown', function (e) {
      if (e.key === 'Enter') tryUnlock();
    });

    document.querySelectorAll('.kv-tabs__btn').forEach(function (b) {
      on(b, 'click', function () { switchTab(b.getAttribute('data-tab')); });
    });

    on($('kvTokenBtn'), 'click', promptToken);
    on($('kvSaveBtn'), 'click', function () {
      saveToGitHub()['catch'](function (e) { alert('Save failed: ' + e.message); });
    });
    on($('kvLogoutBtn'), 'click', function () {
      hideApp();
      var input = $('kvGateInput');
      if (input) { input.value = ''; input.focus(); }
    });

    on($('kvDownloadTemplate'), 'click', downloadTemplate);
    on($('kvImportBtn'), 'click', function () { var f = $('kvImportFile'); if (f) f.click(); });
    on($('kvImportFile'), 'change', function (e) {
      var file = e.target.files && e.target.files[0];
      if (file) handleImportFile(file);
      e.target.value = '';
    });
    on($('kvExportDataBtn'), 'click', function () { exportData(); });
    on($('kvExportCsvDash'), 'click', exportCsv);
    on($('kvExportXlsxDash'), 'click', function () { exportData(); });
    on($('kvAddBtn'), 'click', function () { showForm(null); });
    on($('kvForm'), 'submit', saveForm);
    on($('kvFormCancel'), 'click', hideForm);
    on($('kvFormDelete'), 'click', deleteCurrent);
    on($('kvImportCancel'), 'click', closeImportPreview);
    on($('kvImportConfirm'), 'click', confirmImport);

    on($('kvBackupBtn'), 'click', function () {
      var blob = new Blob([JSON.stringify(payload(), null, 2)], { type: 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'korean-vocab-backup.json';
      a.click();
      URL.revokeObjectURL(a.href);
    });
    on($('kvRestoreBtn'), 'click', function () {
      var f = $('kvRestoreFile');
      if (f) f.click();
    });
    on($('kvRestoreFile'), 'change', function (e) {
      var file = e.target.files && e.target.files[0];
      if (!file) return;
      var fr = new FileReader();
      fr.onload = function (ev) {
        try {
          applyData(JSON.parse(ev.target.result));
          cacheLocal();
          renderAll();
          setIoStatus('ok', '✓ Restore OK · ' + S.items.length + ' terms. Save to GitHub để đẩy lên remote.');
        } catch (err) {
          setIoStatus('err', '✗ JSON không hợp lệ');
        }
      };
      fr.readAsText(file);
      e.target.value = '';
    });

    var drop = $('kvDrop');
    if (drop) {
      ['dragenter', 'dragover'].forEach(function (ev) {
        on(drop, ev, function (e) {
          e.preventDefault();
          drop.classList.add('is-drag');
        });
      });
      ['dragleave', 'drop'].forEach(function (ev) {
        on(drop, ev, function (e) {
          e.preventDefault();
          drop.classList.remove('is-drag');
        });
      });
      on(drop, 'drop', function (e) {
        var file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
        if (file) handleImportFile(file);
      });
      on(drop, 'click', function () {
        var f = $('kvImportFile');
        if (f) f.click();
      });
    }

    on($('kvSearch'), 'input', function () { renderDashboard(); });
    on($('kvFilterField'), 'change', function () { renderDashboard(); });
    on($('kvFilterLearned'), 'change', function () { renderDashboard(); });
    on($('kvClearFilters'), 'click', function () {
      if ($('kvSearch')) $('kvSearch').value = '';
      if ($('kvFilterField')) $('kvFilterField').value = '';
      if ($('kvFilterLearned')) $('kvFilterLearned').value = '';
      renderDashboard();
    });

    on($('kvDashBody'), 'change', function (e) {
      var t = e.target;
      if (t && t.getAttribute('data-learn')) {
        toggleLearned(t.getAttribute('data-learn'), t.checked);
      }
    });
    on($('kvDashBody'), 'click', function (e) {
      var t = e.target;
      if (t && t.getAttribute('data-edit')) {
        var id = t.getAttribute('data-edit');
        var it = S.items.find(function (x) { return x.id === id; });
        if (it) {
          switchTab('input');
          showForm(it);
        }
      }
    });
  }

  function init() {
    initEvents();
    if (sessionStorage.getItem(SESSION_KEY) === '1') {
      showApp();
      bootstrapData();
    } else {
      hideApp();
      // gate visible by default in HTML; ensure app hidden
      var gate = $('kvGate');
      if (gate) gate.style.display = '';
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
