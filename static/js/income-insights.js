(function() {
  'use strict';

  var ACCESS_HASH = '46eaa26621e4955c1675b55d446c6d03325f458b59a465f898d42924010e7286';
  var SESSION_KEY = 'income_insights_unlocked';
  var DB_NAME = 'income_insights_db';
  var STORE_NAME = 'encrypted_data';
  var APP_SALT = 'income-insights-v1-salt';
  var UNDO_LIMIT = 20;
  var BASE_PATH = document.body && document.body.getAttribute('data-site-base') || '';
  var MAX_RETRY_CHART = 5;

  var state = {
    transactions: [],
    filtered: [],
    cryptoKey: null,
    charts: {},
    undoStack: [],
    currentMonth: new Date().getMonth() + 1,
    currentYear: new Date().getFullYear(),
    filterMonth: 0,
    filterYear: 0,
    searchQuery: '',
    sortCol: null,
    sortDir: 'asc',
    editingIndex: -1
  };

  /* ─── Crypto ─────────────────────────────────────────── */
  function sha256(str) {
    var buf = new TextEncoder().encode(str);
    return crypto.subtle.digest('SHA-256', buf).then(function(hash) {
      var hex = '';
      var bytes = new Uint8Array(hash);
      for (var i = 0; i < bytes.length; i++) hex += bytes[i].toString(16).padStart(2, '0');
      return hex;
    });
  }

  function deriveKey(pin) {
    var enc = new TextEncoder();
    return crypto.subtle.importKey('raw', enc.encode(pin), 'PBKDF2', false, ['deriveKey']).then(function(key) {
      return crypto.subtle.deriveKey(
        { name: 'PBKDF2', salt: enc.encode(APP_SALT), iterations: 600000, hash: 'SHA-256' },
        key,
        { name: 'AES-GCM', length: 256 },
        false,
        ['encrypt', 'decrypt']
      );
    });
  }

  function encryptData(plaintext, key) {
    var iv = crypto.getRandomValues(new Uint8Array(12));
    var enc = new TextEncoder();
    return crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, key, enc.encode(plaintext)).then(function(ct) {
      return {
        iv: arrayToBase64(iv),
        ct: arrayToBase64(new Uint8Array(ct))
      };
    });
  }

  function decryptData(encrypted, key) {
    var iv = base64ToArray(encrypted.iv);
    var ct = base64ToArray(encrypted.ct);
    return crypto.subtle.decrypt({ name: 'AES-GCM', iv: iv }, key, ct).then(function(plain) {
      return new TextDecoder().decode(plain);
    });
  }

  function arrayToBase64(arr) {
    var bin = '';
    for (var i = 0; i < arr.length; i++) bin += String.fromCharCode(arr[i]);
    return btoa(bin);
  }

  function base64ToArray(str) {
    var bin = atob(str);
    var arr = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    return arr;
  }

  /* ─── IndexedDB ──────────────────────────────────────── */
  function openDB() {
    return new Promise(function(resolve, reject) {
      var req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = function(e) {
        var db = e.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'id' });
        }
      };
      req.onsuccess = function(e) { resolve(e.target.result); };
      req.onerror = function(e) { reject(e.target.error); };
    });
  }

  function saveToDB(data) {
    return openDB().then(function(db) {
      return new Promise(function(resolve, reject) {
        var tx = db.transaction(STORE_NAME, 'readwrite');
        tx.objectStore(STORE_NAME).put({ id: 'income-data', data: data, updated: Date.now() });
        tx.oncomplete = function() { resolve(); };
        tx.onerror = function(e) { reject(e.target.error); };
      });
    });
  }

  function loadFromDB() {
    return openDB().then(function(db) {
      return new Promise(function(resolve, reject) {
        var tx = db.transaction(STORE_NAME, 'readonly');
        var req = tx.objectStore(STORE_NAME).get('income-data');
        req.onsuccess = function(e) { resolve(e.target.result ? e.target.result.data : null); };
        req.onerror = function(e) { reject(e.target.error); };
      });
    });
  }

  function clearDB() {
    return openDB().then(function(db) {
      return new Promise(function(resolve, reject) {
        var tx = db.transaction(STORE_NAME, 'readwrite');
        tx.objectStore(STORE_NAME)['delete']('income-data');
        tx.oncomplete = function() { resolve(); };
        tx.onerror = function(e) { reject(e.target.error); };
      });
    });
  }

  /* ─── VND Format ─────────────────────────────────────── */
  function formatVND(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return '0';
    return Math.round(amount).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function parseNumber(str) {
    if (typeof str === 'number') return str;
    if (!str) return 0;
    var cleaned = String(str).replace(/[^\d\-.,]/g, '').replace(/\./g, '').replace(',', '');
    var num = parseFloat(cleaned);
    return isNaN(num) ? 0 : num;
  }

  /* ─── Date helpers ────────────────────────────────────── */
  function isValidDate(y, m, d) {
    var dt = new Date(y, m - 1, d);
    return dt.getFullYear() === y && dt.getMonth() === m - 1 && dt.getDate() === d;
  }

  function formatDate(y, m, d) {
    if (!isValidDate(y, m, d)) return 'Ngày không hợp lệ';
    return y + '-' + String(m).padStart(2, '0') + '-' + String(d).padStart(2, '0');
  }

  function genId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }

  /* ─── Data helpers ──────────────────────────────────── */
  function computeFormulas(row) {
    row.subTotal = (row.income || 0) + (row.debt || 0);
    row.date = isValidDate(row.year, row.month, row.day) ? formatDate(row.year, row.month, row.day) : '';
    return row;
  }

  function cloneData(arr) {
    return JSON.parse(JSON.stringify(arr));
  }

  /* ─── Access Gate ───────────────────────────────────── */
  function initGate() {
    var gate = document.getElementById('incomeGate');
    var app = document.getElementById('incomeApp');
    var input = document.getElementById('incomeGateInput');
    var btn = document.getElementById('incomeGateUnlock');
    var err = document.getElementById('incomeGateError');
    var lockBtn = document.getElementById('incomeLockBtn');
    var attemptCount = 0;
    var lastAttempt = 0;

    if (sessionStorage.getItem(SESSION_KEY) === '1') {
      gate.style.display = 'none';
      app.style.display = '';
      lockBtn.style.display = '';
      afterUnlock();
      return;
    }

    function doUnlock() {
      var code = input.value.trim();
      if (!code || code.length !== 4) {
        err.textContent = 'Vui lòng nhập đủ 4 số.';
        return;
      }
      var now = Date.now();
      if (now - lastAttempt < 2000) {
        err.textContent = 'Quá nhanh. Vui lòng đợi 2 giây.';
        return;
      }
      lastAttempt = now;
      attemptCount++;
      if (attemptCount > 5) {
        err.textContent = 'Quá nhiều lần thử. Tải lại trang để thử lại.';
        btn.disabled = true;
        input.disabled = true;
        return;
      }
      sha256(code).then(function(hash) {
        if (hash === ACCESS_HASH) {
          sessionStorage.setItem(SESSION_KEY, '1');
          deriveKey(code).then(function(key) {
            state.cryptoKey = key;
            gate.style.display = 'none';
            app.style.display = '';
            lockBtn.style.display = '';
            afterUnlock();
          });
        } else {
          err.textContent = 'Mã truy cập không đúng. Còn ' + (5 - attemptCount) + ' lần thử.';
          input.value = '';
          input.focus();
        }
      });
    }

    btn.addEventListener('click', doUnlock);
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') doUnlock();
    });
    input.focus();

    lockBtn.addEventListener('click', function() {
      sessionStorage.removeItem(SESSION_KEY);
      state.cryptoKey = null;
      location.reload();
    });
  }

  /* ─── After Unlock ───────────────────────────────────── */
  function afterUnlock() {
    loadFromDB().then(function(encrypted) {
      if (encrypted && state.cryptoKey) {
        return decryptData(encrypted, state.cryptoKey).then(function(json) {
          state.transactions = JSON.parse(json);
          applyFilters();
          renderAll();
          scheduleAutosave();
        });
      } else {
        renderAll();
        scheduleAutosave();
      }
    })['catch'](function() {
      state.transactions = [];
      renderAll();
      scheduleAutosave();
    });
  }

  /* ─── Autosave ───────────────────────────────────────── */
  var autosaveTimer = null;

  function scheduleAutosave() {
    if (autosaveTimer) clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(doAutosave, 3000);
  }

  function doAutosave() {
    if (!state.cryptoKey) return;
    var plain = JSON.stringify(state.transactions);
    encryptData(plain, state.cryptoKey).then(function(enc) {
      return saveToDB(enc);
    })['catch'](function(e) {
      console.warn('Autosave failed:', e);
    });
  }

  document.addEventListener('visibilitychange', function() {
    if (document.hidden) doAutosave();
  });

  /* ─── Undo ────────────────────────────────────────────── */
  function pushUndo() {
    state.undoStack.push(cloneData(state.transactions));
    if (state.undoStack.length > UNDO_LIMIT) state.undoStack.shift();
    document.getElementById('incomeUndoBtn').disabled = false;
  }

  function undo() {
    if (state.undoStack.length === 0) return;
    state.transactions = state.undoStack.pop();
    if (state.undoStack.length === 0) document.getElementById('incomeUndoBtn').disabled = true;
    applyFilters();
    renderAll();
    scheduleAutosave();
  }

  /* ─── Filters ─────────────────────────────────────────── */
  function applyFilters() {
    var filtered = state.transactions.slice();
    var fm = parseInt(document.getElementById('incomeFilterMonth').value, 10);
    var fy = parseInt(document.getElementById('incomeFilterYear').value, 10);
    state.filterMonth = fm;
    state.filterYear = fy;

    if (fm > 0) filtered = filtered.filter(function(t) { return t.month === fm; });
    if (fy > 0) filtered = filtered.filter(function(t) { return t.year === fy; });

    if (state.searchQuery) {
      var q = state.searchQuery.toLowerCase();
      filtered = filtered.filter(function(t) {
        return String(t.sequence).indexOf(q) !== -1 ||
          (t.incomeLabel || '').toLowerCase().indexOf(q) !== -1 ||
          (t.debtLabel || '').toLowerCase().indexOf(q) !== -1 ||
          (t.transactionType || '').toLowerCase().indexOf(q) !== -1 ||
          (t.route || '').toLowerCase().indexOf(q) !== -1 ||
          (t.remark || '').toLowerCase().indexOf(q) !== -1;
      });
    }

    if (state.sortCol) {
      var col = state.sortCol;
      var dir = state.sortDir === 'asc' ? 1 : -1;
      filtered.sort(function(a, b) {
        var va = a[col], vb = b[col];
        if (typeof va === 'string') va = va.toLowerCase();
        if (typeof vb === 'string') vb = vb.toLowerCase();
        if (va < vb) return -1 * dir;
        if (va > vb) return 1 * dir;
        return 0;
      });
    }

    state.filtered = filtered;
  }

  /* ─── Render All ─────────────────────────────────────── */
  var filterListenersInitialized = false;

  function renderAll() {
    populateMonthYearFilters();
    renderTable();
    renderKPIs();
    renderCharts();
    renderInsights();
  }

  function onFilterChange() {
    applyFilters();
    renderTable();
    renderKPIs();
    renderCharts();
    renderInsights();
  }

  function populateMonthYearFilters() {
    var mSel = document.getElementById('incomeFilterMonth');
    var ySel = document.getElementById('incomeFilterYear');
    if (!mSel || !ySel) return;
    var curValM = mSel.value;
    var curValY = ySel.value;

    mSel.innerHTML = '<option value="0">Tất cả</option>';
    ySel.innerHTML = '<option value="0">Tất cả</option>';

    var months = {}, years = {};
    for (var i = 0; i < state.transactions.length; i++) {
      var t = state.transactions[i];
      months[t.month] = true;
      years[t.year] = true;
    }
    for (var m = 1; m <= 12; m++) {
      if (months[m]) {
        var opt = document.createElement('option');
        opt.value = m;
        opt.textContent = 'Tháng ' + m;
        mSel.appendChild(opt);
      }
    }
    var sortedYears = Object.keys(years).map(Number).sort(function(a, b) { return b - a; });
    for (var j = 0; j < sortedYears.length; j++) {
      var opt2 = document.createElement('option');
      opt2.value = sortedYears[j];
      opt2.textContent = sortedYears[j];
      ySel.appendChild(opt2);
    }

    if (curValM) mSel.value = curValM;
    if (curValY) ySel.value = curValY;

    if (!filterListenersInitialized) {
      mSel.addEventListener('change', onFilterChange);
      ySel.addEventListener('change', onFilterChange);
      filterListenersInitialized = true;
    }
  }

  /* ─── Table ──────────────────────────────────────────── */
  var TRANSACTION_TYPES = ['', 'Chuyển khoản', 'Tiền mặt', 'Thẻ tín dụng', 'Ví điện tử', 'QR Code', 'Thu hộ', 'Khác'];
  var transactionTypeListeners = [];
  var routeListeners = [];

  function getAllRoutes() {
    var routes = {};
    for (var i = 0; i < state.transactions.length; i++) {
      if (state.transactions[i].route) routes[state.transactions[i].route] = true;
    }
    return Object.keys(routes);
  }

  function getTypeDatalist() {
    return TRANSACTION_TYPES;
  }

  function renderTable() {
    var tbody = document.getElementById('incomeTableBody');
    tbody.innerHTML = '';
    var rows = state.filtered;

    for (var i = 0; i < rows.length; i++) {
      var t = rows[i];
      var tr = document.createElement('tr');

      tr.appendChild(cellInput('text', t.sequence, 'sequence', i, { cls: 'income-table__col-seq' }));
      tr.appendChild(cellInput('text', formatVND(t.income), 'income', i, { cls: 'income-table__col-income', align: 'right' }));
      tr.appendChild(cellInput('text', t.incomeLabel || '', 'incomeLabel', i, { cls: 'income-table__col-label' }));
      tr.appendChild(cellInput('text', formatVND(t.debt || 0), 'debt', i, { cls: 'income-table__col-debt', align: 'right' }));
      tr.appendChild(cellInput('text', t.debtLabel || '', 'debtLabel', i, { cls: 'income-table__col-label' }));
      tr.appendChild(cellInput('text', formatVND(t.subTotal), 'subTotal', i, { cls: 'income-table__col-total', readonly: true, align: 'right' }));

      // Type select
      var tdType = document.createElement('td');
      tdType.setAttribute('data-label', 'Type');
      var sel = document.createElement('select');
      for (var k = 0; k < TRANSACTION_TYPES.length; k++) {
        var opt = document.createElement('option');
        opt.value = TRANSACTION_TYPES[k];
        opt.textContent = TRANSACTION_TYPES[k] || 'Chọn...';
        sel.appendChild(opt);
      }
      sel.value = t.transactionType || '';
      sel.dataset.idx = i;
      sel.dataset.field = 'transactionType';
      sel.addEventListener('change', onFieldChange);
      tdType.appendChild(sel);
      tr.appendChild(tdType);

      tr.appendChild(cellInput('text', t.route || '', 'route', i, { cls: 'income-table__col-route' }));
      tr.appendChild(cellInput('text', t.remark || '', 'remark', i, { cls: 'income-table__col-remark' }));
      tr.appendChild(cellInput('text', t.date || '', 'date', i, { cls: 'income-table__col-date', readonly: true }));
      tr.appendChild(cellInput('number', t.day || '', 'day', i, { cls: 'income-table__col-d' }));
      tr.appendChild(cellInput('number', t.month || '', 'month', i, { cls: 'income-table__col-m' }));
      tr.appendChild(cellInput('number', t.year || '', 'year', i, { cls: 'income-table__col-y' }));

      // Actions
      var tdActions = document.createElement('td');
      tdActions.setAttribute('data-label', 'Hành động');
      tdActions.className = 'income-table__col-actions';
      var actDiv = document.createElement('div');
      actDiv.className = 'income-table__row-actions';
      var dupBtn = document.createElement('button');
      dupBtn.className = 'income-table__row-btn';
      dupBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
      dupBtn.title = 'Nhân bản';
      dupBtn.addEventListener('click', (function(idx) { return function() { duplicateRow(idx); }; })(i));
      actDiv.appendChild(dupBtn);
      var delBtn = document.createElement('button');
      delBtn.className = 'income-table__row-btn income-table__row-btn--danger';
      delBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>';
      delBtn.title = 'Xóa';
      delBtn.addEventListener('click', (function(idx) { return function() { deleteRow(idx); }; })(i));
      actDiv.appendChild(delBtn);
      tdActions.appendChild(actDiv);
      tr.appendChild(tdActions);

      tbody.appendChild(tr);
    }

    if (rows.length === 0) {
      var emptyTr = document.createElement('tr');
      var emptyTd = document.createElement('td');
      emptyTd.colSpan = 14;
      emptyTd.style.textAlign = 'center';
      emptyTd.style.padding = '2rem';
      emptyTd.style.color = '#888';
      emptyTd.textContent = 'Chưa có dữ liệu. Nhấn "+ Thêm dòng" để bắt đầu.';
      emptyTr.appendChild(emptyTd);
      tbody.appendChild(emptyTr);
    }

    // Filter listeners are set once in populateMonthYearFilters
  }

  function cellInput(type, val, field, idx, opts) {
    opts = opts || {};
    var td = document.createElement('td');
    td.setAttribute('data-label', getColumnLabel(field));
    if (opts.align) td.style.textAlign = opts.align;
    var input = document.createElement('input');
    input.type = type;
    input.value = val !== null && val !== undefined ? val : '';
    input.dataset.idx = idx;
    input.dataset.field = field;
    if (opts.readonly) input.readOnly = true;
    if (field === 'subTotal' || field === 'date') input.readOnly = true;
    if (opts.cls) { var clsParts = opts.cls.split(' '); for (var c = 0; c < clsParts.length; c++) td.classList.add(clsParts[c]); }
    if (!opts.readonly && field !== 'subTotal' && field !== 'date') {
      input.addEventListener('blur', onFieldChange);
      input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') this.blur();
      });
    }
    td.appendChild(input);
    return td;
  }

  function getColumnLabel(field) {
    var labels = {
      sequence: 'Sequence', income: 'Income', incomeLabel: 'Inc.Label',
      debt: 'Debt', debtLabel: 'Debt Label', subTotal: 'Sub Total',
      transactionType: 'Type', route: 'Route', remark: 'Remark',
      date: 'Date', day: 'Day', month: 'Month', year: 'Year'
    };
    return labels[field] || field;
  }

  function onFieldChange(e) {
    var input = e.target;
    var idx = parseInt(input.dataset.idx, 10);
    var field = input.dataset.field;

    if (idx < 0 || idx >= state.filtered.length) return;

    // Map filtered index to actual index
    var actualIdx = state.transactions.indexOf(state.filtered[idx]);
    if (actualIdx === -1) return;

    pushUndo();

    var raw = input.value;
    var t = state.transactions[actualIdx];

    if (field === 'income' || field === 'debt') {
      var parsed = parseNumber(raw);
      t[field] = (field === 'debt' && parsed > 0) ? -parsed : parsed;
    } else if (field === 'sequence') {
      t[field] = parseInt(raw, 10) || 0;
    } else if (field === 'day') {
      t[field] = parseInt(raw, 10) || 0;
    } else if (field === 'month') {
      t[field] = parseInt(raw, 10) || 0;
    } else if (field === 'year') {
      t[field] = parseInt(raw, 10) || 0;
    } else {
      t[field] = raw;
    }

    computeFormulas(t);

    // Validate date
    if (field === 'day' || field === 'month' || field === 'year') {
      if (t.day && t.month && t.year && !isValidDate(t.year, t.month, t.day)) {
        t.date = 'Ngày không hợp lệ';
      }
    }

    applyFilters();
    renderAll();
    scheduleAutosave();
  }

  /* ─── CRUD ───────────────────────────────────────────── */
  function addRow() {
    pushUndo();
    state.transactions.push(computeFormulas({
      id: genId(),
      sequence: state.transactions.length + 1,
      income: 0,
      incomeLabel: '',
      debt: 0,
      debtLabel: '',
      subTotal: 0,
      transactionType: '',
      route: '',
      remark: '',
      date: '',
      day: new Date().getDate(),
      month: new Date().getMonth() + 1,
      year: new Date().getFullYear()
    }));
    applyFilters();
    renderAll();
    scheduleAutosave();
  }

  function deleteRow(filteredIdx) {
    var actualIdx = state.transactions.indexOf(state.filtered[filteredIdx]);
    if (actualIdx === -1) return;
    pushUndo();
    state.transactions.splice(actualIdx, 1);
    applyFilters();
    renderAll();
    scheduleAutosave();
  }

  function duplicateRow(filteredIdx) {
    var actualIdx = state.transactions.indexOf(state.filtered[filteredIdx]);
    if (actualIdx === -1) return;
    pushUndo();
    var copy = JSON.parse(JSON.stringify(state.transactions[actualIdx]));
    copy.id = genId();
    state.transactions.splice(actualIdx + 1, 0, copy);
    applyFilters();
    renderAll();
    scheduleAutosave();
  }

  function clearAllData() {
    if (!confirm('Xóa toàn bộ dữ liệu? Hành động này không thể hoàn tác.')) return;
    pushUndo();
    state.transactions = [];
    clearDB()['catch'](function(e) { console.warn('Clear DB error:', e); });
    applyFilters();
    renderAll();
  }

  function loadSampleData() {
    pushUndo();
    var sample = [
      { id: genId(), sequence: 1, income: 16000000, incomeLabel: 'Lương tháng 7', debt: -3900000, debtLabel: 'Trả thẻ tín dụng', transactionType: 'Chuyển khoản', route: 'Techcombank', remark: 'Lương chính', day: 15, month: 7, year: 2026 },
      { id: genId(), sequence: 2, income: 2500000, incomeLabel: 'Freelance', debt: 0, debtLabel: '', transactionType: 'Chuyển khoản', route: 'MB Bank', remark: 'Dự án web', day: 18, month: 7, year: 2026 },
      { id: genId(), sequence: 3, income: 0, incomeLabel: '', debt: -1200000, debtLabel: 'Tiền nhà', transactionType: 'Chuyển khoản', route: 'Techcombank', remark: 'Tiền nhà T7', day: 5, month: 7, year: 2026 },
      { id: genId(), sequence: 4, income: 0, incomeLabel: '', debt: -500000, debtLabel: 'Ăn uống', transactionType: 'Tiền mặt', route: 'ATM', remark: 'Đi chợ', day: 8, month: 7, year: 2026 },
      { id: genId(), sequence: 5, income: 15000000, incomeLabel: 'Lương tháng 8', debt: -4200000, debtLabel: 'Trả thẻ tín dụng', transactionType: 'Chuyển khoản', route: 'Techcombank', remark: 'Lương T8', day: 15, month: 8, year: 2026 },
      { id: genId(), sequence: 6, income: 3000000, incomeLabel: 'Freelance', debt: 0, debtLabel: '', transactionType: 'Chuyển khoản', route: 'MB Bank', remark: 'Dự án mobile', day: 20, month: 8, year: 2026 },
      { id: genId(), sequence: 7, income: 0, incomeLabel: '', debt: -1200000, debtLabel: 'Tiền nhà', transactionType: 'Chuyển khoản', route: 'Techcombank', remark: 'Tiền nhà T8', day: 5, month: 8, year: 2026 },
      { id: genId(), sequence: 8, income: 0, incomeLabel: '', debt: -600000, debtLabel: 'Ăn uống', transactionType: 'Tiền mặt', route: 'ATM', remark: 'Đi chợ', day: 10, month: 8, year: 2026 }
    ];
    for (var i = 0; i < sample.length; i++) computeFormulas(sample[i]);
    state.transactions = state.transactions.concat(sample);
    applyFilters();
    renderAll();
    scheduleAutosave();
  }

  /* ─── KPI ──────────────────────────────────────────────── */
  function renderKPIs() {
    var rows = state.filtered;
    var totalIncome = 0, totalDebt = 0;
    var last = rows.length > 0 ? rows[rows.length - 1] : null;
    for (var i = 0; i < rows.length; i++) {
      totalIncome += rows[i].income || 0;
      totalDebt += rows[i].debt || 0;
    }
    var net = totalIncome + totalDebt;
    var ratio = totalIncome > 0 ? (Math.abs(totalDebt) / totalIncome) * 100 : 0;

    // Income & Net lấy giá trị dòng cuối cùng, Debt vẫn là tổng
    var displayIncome = last ? (last.income || 0) : totalIncome;
    var displayNet = last ? (last.subTotal || 0) : net;

    document.getElementById('kpiIncome').textContent = formatVND(displayIncome) + '₫';
    document.getElementById('kpiDebt').textContent = formatVND(Math.abs(totalDebt)) + '₫';
    document.getElementById('kpiNet').textContent = formatVND(displayNet) + '₫';
    document.getElementById('kpiNet').style.color = net < 0 ? 'var(--chip-red, #e74c3c)' : '';
    document.getElementById('kpiRatio').textContent = Math.round(ratio) + '%';
    document.getElementById('kpiRatio').style.color = ratio > 50 ? 'var(--chip-red, #e74c3c)' : ratio > 30 ? 'var(--chip-yellow, #f39c12)' : '';
  }

  /* ─── Charts ──────────────────────────────────────────── */
  function renderCharts() {
    if (typeof Chart === 'undefined') {
      var retries = 0;
      var interval = setInterval(function() {
        retries++;
        if (typeof Chart !== 'undefined') {
          clearInterval(interval);
          doRenderCharts();
        } else if (retries >= MAX_RETRY_CHART) {
          clearInterval(interval);
        }
      }, 500);
    } else {
      doRenderCharts();
    }
  }

  var chartInstances = {};

  function destroyChart(id) {
    if (chartInstances[id]) {
      chartInstances[id].destroy();
      delete chartInstances[id];
    }
  }

  function doRenderCharts() {
    var rows = state.filtered;
    if (!rows || rows.length === 0) {
      var chartIds = ['chartIncomeVsDebt', 'chartCashFlow', 'chartDebtByLabel', 'chartIncomeByLabel', 'chartTransactionType', 'chartRoute', 'chartMonthlyTrend', 'chartRatio'];
      for (var z = 0; z < chartIds.length; z++) destroyChart(chartIds[z]);
      return;
    }

    renderIncomeVsDebt(rows);
    renderCashFlow(rows);
    renderDebtByLabel(rows);
    renderIncomeByLabel(rows);
    renderTransactionType(rows);
    renderRoute(rows);
    renderMonthlyTrend(rows);
    renderRatio(rows);
  }

  function getCanvasCtx(id) {
    var canvas = document.getElementById(id);
    if (!canvas) return null;
    return canvas.getContext('2d');
  }

  function createChart(id, config) {
    destroyChart(id);
    var ctx = getCanvasCtx(id);
    if (!ctx) return null;
    try {
      chartInstances[id] = new Chart(ctx, config);
      return chartInstances[id];
    } catch (e) {
      return null;
    }
  }

  function incomeVsDebtChartData(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var t = rows[i];
      var key = t.year + '-' + String(t.month).padStart(2, '0') + '-' + String(t.day).padStart(2, '0');
      if (!map[key]) map[key] = { income: 0, debt: 0 };
      map[key].income += t.income || 0;
      map[key].debt += t.debt || 0;
    }
    var keys = Object.keys(map).sort();
    return {
      labels: keys,
      income: keys.map(function(k) { return map[k].income; }),
      debt: keys.map(function(k) { return Math.abs(map[k].debt); })
    };
  }

  function renderIncomeVsDebt(rows) {
    var data = incomeVsDebtChartData(rows);
    createChart('chartIncomeVsDebt', {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [
          { label: 'Income', data: data.income, backgroundColor: 'rgba(0, 167, 160, 0.7)', borderRadius: 4 },
          { label: 'Debt', data: data.debt, backgroundColor: 'rgba(231, 76, 60, 0.7)', borderRadius: 4 }
        ]
      },
      options: chartOpts('Ngày', 'VND')
    });
  }

  function renderCashFlow(rows) {
    var sorted = rows.slice().sort(function(a, b) { return a.year - b.year || a.month - b.month || a.day - b.day; });
    var labels = sorted.map(function(t) { return t.date || (t.year + '-' + t.month + '-' + t.day); });
    var net = sorted.map(function(t) { return (t.income || 0) + (t.debt || 0); });
    createChart('chartCashFlow', {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Net Cash Flow',
          data: net,
          borderColor: 'rgba(0, 167, 160, 1)',
          backgroundColor: 'rgba(0, 167, 160, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 3
        }]
      },
      options: chartOpts('Thời gian', 'VND')
    });
  }

  function renderDebtByLabel(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var lbl = rows[i].debtLabel || 'Khác';
      map[lbl] = (map[lbl] || 0) + Math.abs(rows[i].debt || 0);
    }
    var labels = Object.keys(map);
    var colors = labels.map(function(_, idx) { return chipColor(idx); });
    createChart('chartDebtByLabel', {
      type: 'doughnut',
      data: { labels: labels, datasets: [{ data: labels.map(function(k) { return map[k]; }), backgroundColor: colors }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } } }
    });
  }

  function renderIncomeByLabel(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var lbl = rows[i].incomeLabel || 'Khác';
      map[lbl] = (map[lbl] || 0) + (rows[i].income || 0);
    }
    var labels = Object.keys(map);
    var colors = labels.map(function(_, idx) { return chipColor(idx + 3); });
    createChart('chartIncomeByLabel', {
      type: 'doughnut',
      data: { labels: labels, datasets: [{ data: labels.map(function(k) { return map[k]; }), backgroundColor: colors }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } } }
    });
  }

  function renderTransactionType(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var typ = rows[i].transactionType || 'Khác';
      map[typ] = (map[typ] || 0) + (rows[i].income || 0) + Math.abs(rows[i].debt || 0);
    }
    var labels = Object.keys(map);
    createChart('chartTransactionType', {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{ label: 'Giá trị', data: labels.map(function(k) { return map[k]; }), backgroundColor: labels.map(function(_, idx) { return chipColor(idx); }), borderRadius: 4 }]
      },
      options: chartOpts('Loại', 'VND')
    });
  }

  function renderRoute(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i].route || 'Khác';
      map[r] = (map[r] || 0) + (rows[i].income || 0) + Math.abs(rows[i].debt || 0);
    }
    var labels = Object.keys(map);
    createChart('chartRoute', {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{ label: 'Giá trị', data: labels.map(function(k) { return map[k]; }), backgroundColor: labels.map(function(_, idx) { return chipColor(idx + 2); }), borderRadius: 4 }]
      },
      options: chartOpts('Route', 'VND')
    });
  }

  function renderMonthlyTrend(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var key = rows[i].year + '-' + String(rows[i].month).padStart(2, '0');
      if (!map[key]) map[key] = { income: 0, debt: 0, net: 0 };
      map[key].income += rows[i].income || 0;
      map[key].debt += rows[i].debt || 0;
    }
    var keys = Object.keys(map).sort();
    createChart('chartMonthlyTrend', {
      type: 'line',
      data: {
        labels: keys,
        datasets: [
          { label: 'Income', data: keys.map(function(k) { return map[k].income; }), borderColor: 'rgba(0, 167, 160, 0.8)', tension: 0.3, pointRadius: 3 },
          { label: 'Debt', data: keys.map(function(k) { return Math.abs(map[k].debt); }), borderColor: 'rgba(231, 76, 60, 0.8)', tension: 0.3, pointRadius: 3 },
          { label: 'Net', data: keys.map(function(k) { return map[k].income + map[k].debt; }), borderColor: 'rgba(52, 152, 219, 0.8)', tension: 0.3, pointRadius: 3, borderDash: [5, 3] }
        ]
      },
      options: chartOpts('Tháng', 'VND')
    });
  }

  function renderRatio(rows) {
    var totalInc = 0, totalDeb = 0;
    for (var i = 0; i < rows.length; i++) {
      totalInc += rows[i].income || 0;
      totalDeb += Math.abs(rows[i].debt || 0);
    }
    var ratio = totalInc > 0 ? (totalDeb / totalInc) : 0;
    var ratioPct = Math.round(ratio * 100);
    var remaining = 100 - ratioPct;
    createChart('chartRatio', {
      type: 'doughnut',
      data: {
        labels: ['Debt (' + ratioPct + '%)', 'Còn lại (' + remaining + '%)'],
        datasets: [{
          data: [ratioPct, Math.max(remaining, 0)],
          backgroundColor: [ratio > 0.5 ? 'rgba(231, 76, 60, 0.8)' : ratio > 0.3 ? 'rgba(243, 156, 18, 0.8)' : 'rgba(0, 167, 160, 0.8)', 'rgba(200, 200, 200, 0.3)']
        }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } } }
    });
  }

  function chartOpts(xLabel, yLabel) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 10 }, boxWidth: 12, padding: 8 } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 9 } } },
        y: {
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: {
            font: { size: 9 },
            callback: function(val) { if (Math.abs(val) >= 1000000) return (val / 1000000).toFixed(1) + 'M'; if (Math.abs(val) >= 1000) return (val / 1000).toFixed(0) + 'k'; return val; }
          }
        }
      }
    };
  }

  var CHIP_COLORS = [
    'rgba(0, 167, 160, 0.7)', 'rgba(231, 76, 60, 0.7)', 'rgba(243, 156, 18, 0.7)',
    'rgba(52, 152, 219, 0.7)', 'rgba(155, 89, 182, 0.7)', 'rgba(46, 204, 113, 0.7)',
    'rgba(230, 126, 34, 0.7)', 'rgba(149, 165, 166, 0.7)', 'rgba(241, 196, 15, 0.7)',
    'rgba(26, 188, 156, 0.7)'
  ];

  function chipColor(idx) { return CHIP_COLORS[idx % CHIP_COLORS.length]; }

  /* ─── AI Insights ────────────────────────────────────── */
  function renderInsights() {
    var container = document.getElementById('incomeInsightsContent');
    if (!container) return;
    if (!state.filtered || state.filtered.length === 0) {
      container.innerHTML = '<p class="income-insights-box__empty">Chưa có dữ liệu để phân tích.</p>';
      return;
    }
    var engine = window.IncomeInsightsEngine;
    if (!engine) {
      container.innerHTML = '<p>Engine phân tích chưa sẵn sàng.</p>';
      return;
    }
    var insights = engine.analyze(state.filtered);
    var html = '';
    for (var i = 0; i < insights.length; i++) {
      var ins = insights[i];
      var cls = 'income-insight-item';
      if (ins.level === 'warning') cls += ' income-insight-item--warning';
      else if (ins.level === 'danger') cls += ' income-insight-item--danger';
      else if (ins.level === 'safe') cls += ' income-insight-item--safe';
      html += '<div class="' + cls + '">' + escapeHtml(ins.text) + '</div>';
    }
    container.innerHTML = html;
  }

  function escapeHtml(str) {
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  /* ─── Export/Import ────────────────────────────────────── */
  function downloadExcelTemplate() {
    if (typeof XLSX === 'undefined') {
      alert('Thư viện Excel chưa sẵn sàng, thử lại sau.');
      return;
    }
    var headers = ['Sequence', 'Income', 'Income_Label', 'Debt', 'Debt_Label', 'Sub Total', 'Transaction_Type', 'Route', 'Remark', 'Date', 'Day', 'Month', 'Year'];
    var sample = [1, 16000000, 'Lương tháng 7', -3900000, 'Trả thẻ tín dụng', 12100000, 'Chuyển khoản', 'Techcombank', 'Lương chính', '2026-07-15', 15, 7, 2026];
    var wsData = [headers, sample];
    var ws = XLSX.utils.aoa_to_sheet(wsData);
    ws['!cols'] = headers.map(function(h) {
      return { wch: h === 'Remark' ? 30 : h === 'Income_Label' || h === 'Debt_Label' ? 18 : h === 'STT' ? 6 : 14 };
    });
    var wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Transactions');
    XLSX.writeFile(wb, 'income-insights-template.xlsx');
  }

  function importFromExcel(file) {
    if (typeof XLSX === 'undefined') {
      alert('Thư viện Excel chưa sẵn sàng, thử lại sau.');
      return;
    }
    var reader = new FileReader();
    reader.onload = function(ev) {
      try {
        var data = new Uint8Array(ev.target.result);
        var wb = XLSX.read(data, { type: 'array' });
        var ws = wb.Sheets[wb.SheetNames[0]];
        var rows = XLSX.utils.sheet_to_json(ws, { header: 1 });
        if (rows.length < 2) { alert('File Excel không có dữ liệu (cần ít nhất 1 dòng header + 1 dòng dữ liệu).'); return; }

        var headerRow = rows[0];
        var colMap = {};
        var expected = ['sequence', 'income', 'incomeLabel', 'debt', 'debtLabel', 'transactionType', 'route', 'remark', 'day', 'month', 'year'];
        var headerNorm = headerRow.map(function(h) {
          return String(h).toLowerCase().replace(/[^a-z0-9]/g, '');
        });
        for (var e = 0; e < expected.length; e++) {
          var idx = headerNorm.indexOf(expected[e]);
          if (idx === -1) idx = headerNorm.indexOf(expected[e].replace('label', ''));
          if (idx !== -1) colMap[expected[e]] = idx;
        }

        var imported = [];
        for (var r = 1; r < rows.length; r++) {
          var row = rows[r];
          if (!row || row.length === 0) continue;
          var hasData = false;
          for (var c = 0; c < row.length; c++) {
            if (row[c] !== undefined && row[c] !== null && row[c] !== '') { hasData = true; break; }
          }
          if (!hasData) continue;

          function getVal(key) {
            var idx = colMap[key];
            if (idx === undefined) return key === 'debt' ? 0 : key === 'sequence' ? 0 : key === 'day' || key === 'month' || key === 'year' ? (key === 'year' ? 2026 : key === 'month' ? 1 : 1) : '';
            var v = row[idx];
            return (v !== undefined && v !== null) ? v : (key === 'debt' ? 0 : key === 'sequence' ? 0 : key === 'day' || key === 'month' || key === 'year' ? (key === 'year' ? 2026 : 1) : '');
          }

          var inc = parseNumber(getVal('income'));
          var deb = parseNumber(getVal('debt'));
          if (deb > 0) deb = -deb;
          var d = parseInt(getVal('day'), 10) || 1;
          var m = parseInt(getVal('month'), 10) || 1;
          var y = parseInt(getVal('year'), 10) || 2026;
          var seq = parseInt(getVal('sequence'), 10) || 0;

          var txn = computeFormulas({
            id: genId(),
            sequence: seq || (imported.length + 1),
            income: inc,
            incomeLabel: String(getVal('incomeLabel') || ''),
            debt: deb,
            debtLabel: String(getVal('debtLabel') || ''),
            subTotal: 0,
            transactionType: String(getVal('transactionType') || ''),
            route: String(getVal('route') || ''),
            remark: String(getVal('remark') || ''),
            date: '',
            day: d,
            month: m,
            year: y
          });
          imported.push(txn);
        }

        if (imported.length === 0) { alert('Không tìm thấy dòng dữ liệu hợp lệ trong file.'); return; }
        pushUndo();
        state.transactions = state.transactions.concat(imported);
        applyFilters();
        renderAll();
        scheduleAutosave();
        alert('Import Excel thành công: ' + imported.length + ' giao dịch.');
      } catch (e) {
        alert('Lỗi đọc file Excel: ' + e.message);
      }
    };
    reader.readAsArrayBuffer(file);
  }

  function exportEncrypted() {
    if (!state.cryptoKey || state.transactions.length === 0) {
      alert('Không có dữ liệu để export.');
      return;
    }
    var plain = JSON.stringify(state.transactions);
    encryptData(plain, state.cryptoKey).then(function(enc) {
      var blob = JSON.stringify({ v: 1, iv: enc.iv, ct: enc.ct }, null, 2);
      downloadFile(blob, 'income-insights-export.json', 'application/json');
    })['catch'](function(e) {
      alert('Export thất bại: ' + e.message);
    });
  }

  function importEncrypted() {
    var input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,.xlsx';
    input.addEventListener('change', function(e) {
      var file = e.target.files[0];
      if (!file) return;

      if (file.name.endsWith('.xlsx')) {
        importFromExcel(file);
        return;
      }

      var reader = new FileReader();
      reader.onload = function(ev) {
        try {
          var data = JSON.parse(ev.target.result);
          if (!data.iv || !data.ct) { alert('File không hợp lệ.'); return; }
          if (!state.cryptoKey) { alert('Chưa có mã truy cập.'); return; }
          decryptData({ iv: data.iv, ct: data.ct }, state.cryptoKey).then(function(json) {
            var transactions = JSON.parse(json);
            if (!Array.isArray(transactions)) { alert('File không chứa dữ liệu giao dịch.'); return; }
            pushUndo();
            state.transactions = transactions;
            applyFilters();
            renderAll();
            scheduleAutosave();
            alert('Import thành công: ' + transactions.length + ' giao dịch.');
          })['catch'](function() {
            alert('Giải mã thất bại. Sai mã truy cập hoặc file bị hỏng.');
          });
        } catch (e) {
          alert('File không hợp lệ.');
        }
      };
      reader.readAsText(file);
    });
    input.click();
  }

  function exportCSV() {
    if (state.transactions.length === 0) {
      alert('Không có dữ liệu để export.');
      return;
    }
    var rows = state.transactions;
    var headers = ['STT', 'Income', 'Income_Label', 'Debt', 'Debt_Label', 'Sub_Total', 'Transaction_Type', 'Route', 'Remark', 'Date', 'Day', 'Month', 'Year'];
    var csv = '\uFEFF' + headers.join(',') + '\n';
    for (var i = 0; i < rows.length; i++) {
      var t = rows[i];
      csv += [
        t.sequence, t.income, csvEscape(t.incomeLabel), t.debt || 0, csvEscape(t.debtLabel),
        t.subTotal, csvEscape(t.transactionType), csvEscape(t.route), csvEscape(t.remark),
        t.date || '', t.day, t.month, t.year
      ].join(',') + '\n';
    }
    downloadFile(csv, 'income-insights-export.csv', 'text/csv;charset=utf-8');
  }

  function csvEscape(str) {
    if (!str) return '';
    var s = String(str);
    if (s.indexOf(',') !== -1 || s.indexOf('"') !== -1 || s.indexOf('\n') !== -1) {
      return '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
  }

  function downloadFile(content, filename, mimeType) {
    var blob = new Blob([content], { type: mimeType });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(function() {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 100);
  }

  /* ─── Search ──────────────────────────────────────────── */
  function initSearch() {
    var container = document.querySelector('.income-app__toolbar');
    if (!container) return;
    var searchInput = document.createElement('input');
    searchInput.type = 'search';
    searchInput.placeholder = 'Tìm kiếm...';
    searchInput.className = 'income-app__select';
    searchInput.style.minWidth = '160px';
    searchInput.addEventListener('input', function() {
      state.searchQuery = this.value;
      applyFilters();
      renderTable();
      renderKPIs();
      renderCharts();
      renderInsights();
    });
    container.insertBefore(searchInput, container.querySelector('.income-app__undo'));
  }

  /* ─── Export Report ─────────────────────────────────────── */
  function exportReport() {
    var rows = state.transactions;
    var now = new Date();
    var dateStr = now.getDate() + '-' + (now.getMonth() + 1) + '-' + now.getFullYear();
    var timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0') + ':' + now.getSeconds().toString().padStart(2, '0');
    var totalInc = 0, totalDeb = 0, count = rows.length;
    for (var i = 0; i < rows.length; i++) {
      totalInc += rows[i].income || 0;
      totalDeb += Math.abs(rows[i].debt || 0);
    }
    var net = totalInc - totalDeb;
    var ratio = totalInc > 0 ? ((totalDeb / totalInc) * 100).toFixed(1) : 'N/A';

    // Generate a deterministic blockchain-like address from data
    var dataStr = JSON.stringify(rows) + 'https://banhang-chogao.github.io/reviewchanthat/';
    var addrHash = 0;
    for (var j = 0; j < dataStr.length; j++) {
      addrHash = ((addrHash << 5) - addrHash) + dataStr.charCodeAt(j);
      addrHash = addrHash & addrHash;
    }
    var blockAddr = '0x' + Math.abs(addrHash).toString(16).toUpperCase().slice(0, 14).padStart(14, '0');

    var lines = [];
    lines.push('═══════════════════════════════════════════════════');
    lines.push('  Insights Report of Review Chân Thật — ' + dateStr);
    lines.push('═══════════════════════════════════════════════════');
    lines.push('');
    lines.push('  Thời gian xuất: ' + dateStr + ' ' + timeStr + ' GMT +7');
    lines.push('  Tổng số giao dịch: ' + count);
    lines.push('');
    lines.push('  ─── TỔNG QUAN ───');
    lines.push('  Tổng Income:        ' + fmt(totalInc));
    lines.push('  Tổng Debt:          ' + fmt(totalDeb));
    lines.push('  Net:                ' + fmt(net));
    lines.push('  Debt/Income Ratio:  ' + ratio + '%');
    lines.push('');
    lines.push('  ─── CHI TIẾT ───');
    for (var k = 0; k < rows.length; k++) {
      var t = rows[k];
      var line = '  ' + (k + 1) + '. ';
      if (t.date) line += '[' + t.date + '] ';
      line += 'Income: ' + fmt(t.income || 0);
      if (t.incomeLabel) line += ' (' + t.incomeLabel + ')';
      line += ' | Debt: ' + fmt(Math.abs(t.debt || 0));
      if (t.debtLabel) line += ' (' + t.debtLabel + ')';
      if (t.transactionType) line += ' | ' + t.transactionType;
      if (t.route) line += ' | ' + t.route;
      if (t.remark) line += ' | ' + t.remark;
      lines.push(line);
    }
    lines.push('');
    lines.push('═══════════════════════════════════════════════════');
    lines.push('  Blockchain: ' + blockAddr);
    lines.push('  ' + 'https://banhang-chogao.github.io/reviewchanthat/');
    lines.push('═══════════════════════════════════════════════════');

    var blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'insights-report-' + dateStr.replace(/\//g, '-') + '.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /* ─── Save ────────────────────────────────────────────── */
  function saveNow() {
    var msg = document.getElementById('incomeSaveMsg');
    if (msg) {
      msg.classList.remove('income-toast--hidden');
      msg.classList.add('income-toast--show');
      return;
    }
    doAutosave();
    var messages = [
      'Bạn đã quan tâm thu nhập của mình rồi đó — lưu thành công! 🎉',
      'Dữ liệu đã an toàn rồi, chủ nhân yên tâm nhé! 💪',
      'Lưu xong rồi! Càng theo dõi, càng giàu to. 📈',
      'Số liệu đã ghi nhận — tiếp tục làm chủ tài chính nhé! 🔥',
      'Lưu rồi! Bạn giỏi quá, hôm nay lại có thêm 1 sao. ⭐'
    ];
    var text = messages[Math.floor(Math.random() * messages.length)];
    var toast = document.createElement('div');
    toast.className = 'income-toast';
    toast.id = 'incomeSaveMsg';
    toast.textContent = text;
    document.body.appendChild(toast);
    requestAnimationFrame(function() {
      toast.classList.add('income-toast--show');
    });
    setTimeout(function() {
      toast.classList.remove('income-toast--show');
      toast.classList.add('income-toast--hidden');
      setTimeout(function() { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 400);
    }, 3500);
  }

  function fmt(num) {
    if (Math.abs(num) >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (Math.abs(num) >= 1000) return (num / 1000).toFixed(0) + 'k';
    return num.toString();
  }

  /* ─── Init ────────────────────────────────────────────── */
  function init() {
    initGate();
    initSearch();

    document.getElementById('incomeAddRow').addEventListener('click', addRow);
    document.getElementById('incomeSaveBtn').addEventListener('click', saveNow);
    document.getElementById('incomeUndoBtn').addEventListener('click', undo);
    document.getElementById('incomeReportBtn').addEventListener('click', exportReport);
    document.getElementById('incomeSampleBtn').addEventListener('click', loadSampleData);
    document.getElementById('incomeExportBtn').addEventListener('click', exportEncrypted);
    document.getElementById('incomeImportBtn').addEventListener('click', importEncrypted);
    document.getElementById('incomeCSVBtn').addEventListener('click', exportCSV);
    document.getElementById('incomeTemplateBtn').addEventListener('click', downloadExcelTemplate);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
