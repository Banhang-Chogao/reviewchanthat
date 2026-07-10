(function() {
  'use strict';

  var ACCESS_HASH = '46eaa26621e4955c1675b55d446c6d03325f458b59a465f898d42924010e7286';
  var SESSION_KEY = 'expense_management_unlocked';
  var DB_NAME = 'expense_management_db';
  var STORE_NAME = 'encrypted_data';
  var APP_SALT = 'expense-management-v1-salt';
  var UNDO_LIMIT = 20;
  var BASE_PATH = document.body && document.body.getAttribute('data-site-base') || '';
  var MAX_RETRY_CHART = 5;
  var EXPENSE_TYPES = ['', 'Fixed', 'Variable', 'One-time', 'Recurring', 'Discretionary', 'Essential', 'Non-essential'];

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
      return { iv: arrayToBase64(iv), ct: arrayToBase64(new Uint8Array(ct)) };
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
        tx.objectStore(STORE_NAME).put({ id: 'expense-data', data: data, updated: Date.now() });
        tx.oncomplete = function() { resolve(); };
        tx.onerror = function(e) { reject(e.target.error); };
      });
    });
  }

  function loadFromDB() {
    return openDB().then(function(db) {
      return new Promise(function(resolve, reject) {
        var tx = db.transaction(STORE_NAME, 'readonly');
        var req = tx.objectStore(STORE_NAME).get('expense-data');
        req.onsuccess = function(e) { resolve(e.target.result ? e.target.result.data : null); };
        req.onerror = function(e) { reject(e.target.error); };
      });
    });
  }

  function clearDB() {
    return openDB().then(function(db) {
      return new Promise(function(resolve, reject) {
        var tx = db.transaction(STORE_NAME, 'readwrite');
        tx.objectStore(STORE_NAME)['delete']('expense-data');
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
    if (row.day && row.month && row.year && isValidDate(row.year, row.month, row.day)) {
      row.date = formatDate(row.year, row.month, row.day);
    } else if (row.day || row.month || row.year) {
      row.date = 'Ngày không hợp lệ';
    } else {
      row.date = '';
    }
    return row;
  }

  function cloneData(arr) {
    return JSON.parse(JSON.stringify(arr));
  }

  /* ─── Access Gate ───────────────────────────────────── */
  function initGate() {
    var gate = document.getElementById('expenseGate');
    var app = document.getElementById('expenseApp');
    var input = document.getElementById('expenseGateInput');
    var btn = document.getElementById('expenseGateUnlock');
    var err = document.getElementById('expenseGateError');
    var lockBtn = document.getElementById('expenseLockBtn');
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
      var code = prompt('Nhập mã truy cập để KHOÁ phiên làm việc?');
      if (!code) return;
      sha256(code).then(function(hash) {
        if (hash !== ACCESS_HASH) {
          alert('Mã truy cập không đúng.');
          return;
        }
        sessionStorage.removeItem(SESSION_KEY);
        state.cryptoKey = null;
        gate.style.display = '';
        app.style.display = 'none';
        lockBtn.style.display = 'none';
        input.value = '';
        input.focus();
      });
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
    document.getElementById('expenseUndoBtn').disabled = false;
  }

  function undo() {
    if (state.undoStack.length === 0) return;
    state.transactions = state.undoStack.pop();
    if (state.undoStack.length === 0) document.getElementById('expenseUndoBtn').disabled = true;
    applyFilters();
    renderAll();
    scheduleAutosave();
  }

  /* ─── Filters ─────────────────────────────────────────── */
  function applyFilters() {
    var filtered = state.transactions.slice();
    var fm = parseInt(document.getElementById('expenseFilterMonth').value, 10);
    var fy = parseInt(document.getElementById('expenseFilterYear').value, 10);
    state.filterMonth = fm;
    state.filterYear = fy;

    if (fm > 0) filtered = filtered.filter(function(t) { return t.month === fm; });
    if (fy > 0) filtered = filtered.filter(function(t) { return t.year === fy; });

    if (state.searchQuery) {
      var q = state.searchQuery.toLowerCase();
      filtered = filtered.filter(function(t) {
        return String(t.sequence).indexOf(q) !== -1 ||
          (t.expenseLabel || '').toLowerCase().indexOf(q) !== -1 ||
          (t.expenseType || '').toLowerCase().indexOf(q) !== -1 ||
          (t.transactionType || '').toLowerCase().indexOf(q) !== -1 ||
          (t.route || '').toLowerCase().indexOf(q) !== -1 ||
          (t.bankRoute || '').toLowerCase().indexOf(q) !== -1 ||
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
    var mSel = document.getElementById('expenseFilterMonth');
    var ySel = document.getElementById('expenseFilterYear');
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
  function renderTable() {
    var tbody = document.getElementById('expenseTableBody');
    tbody.innerHTML = '';
    var rows = state.filtered;

    for (var i = 0; i < rows.length; i++) {
      var t = rows[i];
      var tr = document.createElement('tr');

      tr.appendChild(cellInput('text', t.sequence, 'sequence', i, { cls: 'expense-table__col-seq' }));
      tr.appendChild(cellInput('text', formatVND(t.income), 'income', i, { cls: 'expense-table__col-income', align: 'right' }));
      tr.appendChild(cellInput('text', formatVND(t.expense), 'expense', i, { cls: 'expense-table__col-expense', align: 'right' }));
      tr.appendChild(cellInput('text', t.expenseLabel || '', 'expenseLabel', i, { cls: 'expense-table__col-label' }));
      tr.appendChild(cellSelect(t.expenseType || '', 'expenseType', i, EXPENSE_TYPES, 'expense-table__col-type'));
      tr.appendChild(cellInput('text', t.transactionType || '', 'transactionType', i, { cls: 'expense-table__col-txn' }));
      tr.appendChild(cellInput('text', t.route || '', 'route', i, { cls: 'expense-table__col-route' }));
      tr.appendChild(cellInput('text', t.bankRoute || '', 'bankRoute', i, { cls: 'expense-table__col-bank' }));
      tr.appendChild(cellInput('text', t.remark || '', 'remark', i, { cls: 'expense-table__col-remark' }));
      tr.appendChild(cellInput('text', t.date || '', 'date', i, { cls: 'expense-table__col-date', readonly: true }));
      tr.appendChild(cellInput('number', t.day || '', 'day', i, { cls: 'expense-table__col-d' }));
      tr.appendChild(cellInput('number', t.month || '', 'month', i, { cls: 'expense-table__col-m' }));
      tr.appendChild(cellInput('number', t.year || '', 'year', i, { cls: 'expense-table__col-y' }));

      var tdActions = document.createElement('td');
      tdActions.setAttribute('data-label', 'Hành động');
      tdActions.className = 'expense-table__col-actions';
      var actDiv = document.createElement('div');
      actDiv.className = 'expense-table__row-actions';
      var dupBtn = document.createElement('button');
      dupBtn.className = 'expense-table__row-btn';
      dupBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
      dupBtn.title = 'Nhân bản';
      dupBtn.addEventListener('click', (function(idx) { return function() { duplicateRow(idx); }; })(i));
      actDiv.appendChild(dupBtn);
      var delBtn = document.createElement('button');
      delBtn.className = 'expense-table__row-btn expense-table__row-btn--danger';
      delBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>';
      delBtn.title = 'Xoá';
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
    if (opts.readonly || field === 'date') input.readOnly = true;
    if (opts.cls) { var clsParts = opts.cls.split(' '); for (var c = 0; c < clsParts.length; c++) td.classList.add(clsParts[c]); }
    if (!opts.readonly && field !== 'date') {
      input.addEventListener('blur', onFieldChange);
      input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') this.blur();
      });
    }
    td.appendChild(input);
    return td;
  }

  function cellSelect(val, field, idx, options, cls) {
    var td = document.createElement('td');
    td.setAttribute('data-label', getColumnLabel(field));
    var select = document.createElement('select');
    select.dataset.idx = idx;
    select.dataset.field = field;
    if (cls) { var clsParts = cls.split(' '); for (var c = 0; c < clsParts.length; c++) td.classList.add(clsParts[c]); }
    for (var o = 0; o < options.length; o++) {
      var opt = document.createElement('option');
      opt.value = options[o];
      opt.textContent = options[o] || '(chọn)';
      if (options[o] === val) opt.selected = true;
      select.appendChild(opt);
    }
    select.addEventListener('change', onFieldChange);
    td.appendChild(select);
    return td;
  }

  function getColumnLabel(field) {
    var labels = {
      sequence: 'A - Sequence', income: 'B - Income', expense: 'C - Expense Amount',
      expenseLabel: 'D - Expense Label', expenseType: 'E - Expense Type',
      transactionType: 'F - Transaction Type', route: 'G - Route', bankRoute: 'H - Bank Route',
      remark: 'I - Remark', date: 'J - Date', day: 'K - D', month: 'L - M', year: 'M - Y'
    };
    return labels[field] || field;
  }

  function onFieldChange(e) {
    var el = e.target;
    var idx = parseInt(el.dataset.idx, 10);
    var field = el.dataset.field;

    if (idx < 0 || idx >= state.filtered.length) return;

    var actualIdx = state.transactions.indexOf(state.filtered[idx]);
    if (actualIdx === -1) return;

    pushUndo();

    var raw = el.value;
    var t = state.transactions[actualIdx];

    if (field === 'income' || field === 'expense') {
      t[field] = parseNumber(raw);
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
      expense: 0,
      expenseLabel: '',
      expenseType: '',
      transactionType: '',
      route: '',
      bankRoute: '',
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
    if (!confirm('Xoá toàn bộ dữ liệu? Hành động này không thể hoàn tác.')) return;
    pushUndo();
    state.transactions = [];
    clearDB()['catch'](function(e) { console.warn('Clear DB error:', e); });
    applyFilters();
    renderAll();
  }

  function loadSampleData() {
    pushUndo();
    var sample = [
      { id: genId(), sequence: 1, income: 16000000, expense: 3900000, expenseLabel: 'Trả thẻ tín dụng', expenseType: 'Fixed', transactionType: 'Chuyển khoản', route: 'Techcombank', bankRoute: 'Visa', remark: 'Thanh toán thẻ', day: 15, month: 7, year: 2026 },
      { id: genId(), sequence: 2, income: 0, expense: 800000, expenseLabel: 'Ăn uống', expenseType: 'Variable', transactionType: 'Tiền mặt', route: 'Rút ATM', bankRoute: '', remark: 'Đi chợ', day: 18, month: 7, year: 2026 },
      { id: genId(), sequence: 3, income: 5000000, expense: 1200000, expenseLabel: 'Tiền nhà', expenseType: 'Fixed', transactionType: 'Chuyển khoản', route: 'Techcombank', bankRoute: '', remark: 'Tiền nhà T7', day: 5, month: 7, year: 2026 },
      { id: genId(), sequence: 4, income: 0, expense: 500000, expenseLabel: 'Xăng xe', expenseType: 'Variable', transactionType: 'Tiền mặt', route: 'Rút ATM', bankRoute: '', remark: 'Đổ xăng', day: 8, month: 7, year: 2026 },
      { id: genId(), sequence: 5, income: 15000000, expense: 4200000, expenseLabel: 'Trả thẻ tín dụng', expenseType: 'Fixed', transactionType: 'Chuyển khoản', route: 'Techcombank', bankRoute: 'Mastercard', remark: 'Thanh toán tháng 8', day: 15, month: 8, year: 2026 },
      { id: genId(), sequence: 6, income: 3000000, expense: 500000, expenseLabel: 'Bảo hiểm', expenseType: 'Fixed', transactionType: 'Chuyển khoản', route: 'MB Bank', bankRoute: '', remark: 'Bảo hiểm tháng 8', day: 20, month: 8, year: 2026 },
      { id: genId(), sequence: 7, income: 0, expense: 1200000, expenseLabel: 'Tiền nhà', expenseType: 'Fixed', transactionType: 'Chuyển khoản', route: 'Techcombank', bankRoute: '', remark: 'Tiền nhà T8', day: 5, month: 8, year: 2026 },
      { id: genId(), sequence: 8, income: 0, expense: 600000, expenseLabel: 'Ăn uống', expenseType: 'Variable', transactionType: 'Tiền mặt', route: 'Rút ATM', bankRoute: '', remark: 'Đi chợ tuần 1', day: 10, month: 8, year: 2026 }
    ];
    for (var i = 0; i < sample.length; i++) { computeFormulas(sample[i]); sample[i]._sample = true; }
    state.transactions = state.transactions.concat(sample);
    applyFilters();
    renderAll();
    scheduleAutosave();
  }

  /* ─── KPI ──────────────────────────────────────────────── */
  function renderKPIs() {
    var rows = state.filtered;
    var totalIncome = 0, totalExpense = 0, maxExpense = 0, count = rows.length;
    var dailySet = {};

    for (var i = 0; i < rows.length; i++) {
      var inc = rows[i].income || 0;
      var exp = rows[i].expense || 0;
      totalIncome += inc;
      totalExpense += exp;
      if (exp > maxExpense) maxExpense = exp;
      var dk = (rows[i].year || 0) + '-' + (rows[i].month || 0) + '-' + (rows[i].day || 0);
      if (!dailySet[dk]) dailySet[dk] = 0;
      dailySet[dk] += exp;
    }

    var net = totalIncome - totalExpense;
    var dailyCount = Object.keys(dailySet).length || 1;
    var avgDaily = Math.round(totalExpense / dailyCount);

    document.getElementById('kpiTotalExpense').textContent = formatVND(totalExpense) + '₫';
    document.getElementById('kpiTotalIncome').textContent = formatVND(totalIncome) + '₫';
    document.getElementById('kpiNetCashflow').textContent = formatVND(net) + '₫';
    document.getElementById('kpiMaxExpense').textContent = formatVND(maxExpense) + '₫';
    document.getElementById('kpiTransactionCount').textContent = count;
    document.getElementById('kpiAvgDaily').textContent = formatVND(avgDaily) + '₫';

    // Status + delta
    setKpiStatus('kpiNetCashflow', net, 'kpiDeltaNet');
    setKpiStatus('kpiMaxExpense', maxExpense, 'kpiDeltaMax');
    setKpiStatus('kpiTotalExpense', totalExpense, 'kpiDeltaExpense');
  }

  function setKpiStatus(elId, val, deltaId) {
    var el = document.getElementById(elId);
    if (!el) return;
    var card = el.closest('.expense-kpi');
    if (!card) return;
    if (elId === 'kpiNetCashflow') {
      if (val < 0) card.dataset.status = 'danger';
      else if (val < 1000000) card.dataset.status = 'warning';
      else card.dataset.status = 'safe';
    }
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
      var ids = ['chartDailyExpense', 'chartIncomeVsExpense', 'chartExpenseType', 'chartExpenseLabel', 'chartTransactionType', 'chartBankRoute', 'chartTopExpenses', 'chartMonthlyTrend', 'chartAvgDaily', 'chartHeatmap'];
      for (var z = 0; z < ids.length; z++) destroyChart(ids[z]);
      return;
    }
    renderDailyExpense(rows);
    renderIncomeVsExpense(rows);
    renderExpenseType(rows);
    renderExpenseLabel(rows);
    renderTransactionType(rows);
    renderBankRoute(rows);
    renderTopExpenses(rows);
    renderMonthlyTrend(rows);
    renderAvgDaily(rows);
    renderHeatmap(rows);
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

  function renderDailyExpense(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var key = rows[i].year + '-' + String(rows[i].month).padStart(2, '0') + '-' + String(rows[i].day).padStart(2, '0');
      map[key] = (map[key] || 0) + (rows[i].expense || 0);
    }
    var keys = Object.keys(map).sort();
    createChart('chartDailyExpense', {
      type: 'bar',
      data: {
        labels: keys,
        datasets: [{ label: 'Chi tiêu', data: keys.map(function(k) { return map[k]; }), backgroundColor: 'rgba(0, 167, 160, 0.7)', borderRadius: 4 }]
      },
      options: chartOpts('Ngày', 'VND')
    });
  }

  function renderIncomeVsExpense(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var key = rows[i].year + '-' + String(rows[i].month).padStart(2, '0') + '-' + String(rows[i].day).padStart(2, '0');
      if (!map[key]) map[key] = { income: 0, expense: 0 };
      map[key].income += rows[i].income || 0;
      map[key].expense += rows[i].expense || 0;
    }
    var keys = Object.keys(map).sort();
    createChart('chartIncomeVsExpense', {
      type: 'bar',
      data: {
        labels: keys,
        datasets: [
          { label: 'Thu nhập', data: keys.map(function(k) { return map[k].income; }), backgroundColor: 'rgba(46, 204, 113, 0.7)', borderRadius: 4 },
          { label: 'Chi tiêu', data: keys.map(function(k) { return map[k].expense; }), backgroundColor: 'rgba(231, 76, 60, 0.7)', borderRadius: 4 }
        ]
      },
      options: chartOpts('Ngày', 'VND')
    });
  }

  function renderExpenseType(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var typ = rows[i].expenseType || 'Khác';
      map[typ] = (map[typ] || 0) + (rows[i].expense || 0);
    }
    var labels = Object.keys(map);
    var colors = labels.map(function(_, idx) { return chipColor(idx); });
    createChart('chartExpenseType', {
      type: 'doughnut',
      data: { labels: labels, datasets: [{ data: labels.map(function(k) { return map[k]; }), backgroundColor: colors }] },
      options: chartOptsPie()
    });
  }

  function renderExpenseLabel(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var lbl = rows[i].expenseLabel || 'Khác';
      map[lbl] = (map[lbl] || 0) + (rows[i].expense || 0);
    }
    var labels = Object.keys(map);
    var colors = labels.map(function(_, idx) { return chipColor(idx + 2); });
    createChart('chartExpenseLabel', {
      type: 'doughnut',
      data: { labels: labels, datasets: [{ data: labels.map(function(k) { return map[k]; }), backgroundColor: colors }] },
      options: chartOptsPie()
    });
  }

  function renderTransactionType(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var typ = rows[i].transactionType || 'Khác';
      map[typ] = (map[typ] || 0) + (rows[i].expense || 0);
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

  function renderBankRoute(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i].bankRoute || 'Khác';
      map[r] = (map[r] || 0) + (rows[i].expense || 0);
    }
    var labels = Object.keys(map);
    createChart('chartBankRoute', {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{ label: 'Giá trị', data: labels.map(function(k) { return map[k]; }), backgroundColor: labels.map(function(_, idx) { return chipColor(idx + 3); }), borderRadius: 4 }]
      },
      options: chartOpts('Bank Route', 'VND')
    });
  }

  function renderTopExpenses(rows) {
    var sorted = rows.slice().sort(function(a, b) { return (b.expense || 0) - (a.expense || 0); });
    var top = sorted.slice(0, 10);
    var labels = top.map(function(t) { return t.expenseLabel || t.remark || '#' + t.sequence; });
    var data = top.map(function(t) { return t.expense || 0; });
    createChart('chartTopExpenses', {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{ label: 'Chi phí', data: data, backgroundColor: labels.map(function(_, idx) { return chipColor(idx); }), borderRadius: 4 }]
      },
      options: chartOpts('Khoản chi', 'VND')
    });
  }

  function renderMonthlyTrend(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var key = rows[i].year + '-' + String(rows[i].month).padStart(2, '0');
      if (!map[key]) map[key] = { income: 0, expense: 0, net: 0 };
      map[key].income += rows[i].income || 0;
      map[key].expense += rows[i].expense || 0;
    }
    var keys = Object.keys(map).sort();
    createChart('chartMonthlyTrend', {
      type: 'line',
      data: {
        labels: keys,
        datasets: [
          { label: 'Thu nhập', data: keys.map(function(k) { return map[k].income; }), borderColor: 'rgba(46, 204, 113, 0.8)', tension: 0.3, pointRadius: 3 },
          { label: 'Chi tiêu', data: keys.map(function(k) { return map[k].expense; }), borderColor: 'rgba(231, 76, 60, 0.8)', tension: 0.3, pointRadius: 3 },
          { label: 'Dòng tiền ròng', data: keys.map(function(k) { return map[k].income - map[k].expense; }), borderColor: 'rgba(0, 167, 160, 0.8)', tension: 0.3, pointRadius: 3, borderDash: [5, 3] }
        ]
      },
      options: chartOpts('Tháng', 'VND')
    });
  }

  function renderAvgDaily(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var key = rows[i].year + '-' + String(rows[i].month).padStart(2, '0');
      if (!map[key]) map[key] = { total: 0, days: {} };
      var dayKey = rows[i].day || 0;
      if (dayKey && !map[key].days[dayKey]) {
        map[key].days[dayKey] = true;
      }
      map[key].total += rows[i].expense || 0;
    }
    var keys = Object.keys(map).sort();
    var avgs = keys.map(function(k) {
      var dCount = Object.keys(map[k].days).length || 1;
      return Math.round(map[k].total / dCount);
    });
    createChart('chartAvgDaily', {
      type: 'bar',
      data: {
        labels: keys,
        datasets: [{ label: 'Trung bình/ngày', data: avgs, backgroundColor: 'rgba(52, 152, 219, 0.7)', borderRadius: 4 }]
      },
      options: chartOpts('Tháng', 'VND')
    });
  }

  function renderHeatmap(rows) {
    var map = {};
    for (var i = 0; i < rows.length; i++) {
      var day = rows[i].day || 0;
      if (day > 0 && (rows[i].expense || 0) > 0) {
        map[day] = (map[day] || 0) + (rows[i].expense || 0);
      }
    }
    var days = [];
    for (var d = 1; d <= 31; d++) {
      days.push(map[d] || 0);
    }
    var maxVal = Math.max.apply(null, days) || 1;
    var bgColors = days.map(function(v) {
      var intensity = v / maxVal;
      if (intensity > 0.7) return 'rgba(231, 76, 60, 0.8)';
      if (intensity > 0.4) return 'rgba(243, 156, 18, 0.7)';
      if (intensity > 0.1) return 'rgba(0, 167, 160, 0.5)';
      return 'rgba(200, 200, 200, 0.2)';
    });
    createChart('chartHeatmap', {
      type: 'bar',
      data: {
        labels: days.map(function(_, idx) { return 'Ngày ' + (idx + 1); }),
        datasets: [{ label: 'Chi tiêu', data: days, backgroundColor: bgColors, borderRadius: 2 }]
      },
      options: chartOpts('Ngày', 'VND')
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

  function chartOptsPie() {
    return { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } } };
  }

  var CHIP_COLORS = [
    'rgba(0, 167, 160, 0.7)', 'rgba(231, 76, 60, 0.7)', 'rgba(243, 156, 18, 0.7)',
    'rgba(52, 152, 219, 0.7)', 'rgba(155, 89, 182, 0.7)', 'rgba(46, 204, 113, 0.7)',
    'rgba(230, 126, 34, 0.7)', 'rgba(149, 165, 166, 0.7)', 'rgba(241, 196, 15, 0.7)',
    'rgba(26, 188, 156, 0.7)'
  ];

  function chipColor(idx) { return CHIP_COLORS[idx % CHIP_COLORS.length]; }

  /* ─── Insights ────────────────────────────────────────── */
  function renderInsights() {
    var container = document.getElementById('expenseInsightsContent');
    if (!container) return;
    if (!state.filtered || state.filtered.length === 0) {
      container.innerHTML = '<p class="expense-insights-box__empty">Chưa có dữ liệu để phân tích.</p>';
      return;
    }
    var engine = window.ExpenseInsightsEngine;
    if (!engine) {
      container.innerHTML = '<p>Engine phân tích chưa sẵn sàng.</p>';
      return;
    }
    var insights = engine.analyze(state.filtered);
    var html = '';
    for (var i = 0; i < insights.length; i++) {
      var ins = insights[i];
      var cls = 'expense-insight-item';
      if (ins.level === 'warning') cls += ' expense-insight-item--warning';
      else if (ins.level === 'danger') cls += ' expense-insight-item--danger';
      else if (ins.level === 'safe') cls += ' expense-insight-item--safe';
      else if (ins.level === 'info') cls += ' expense-insight-item--info';
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
  function exportEncrypted() {
    if (!state.cryptoKey || state.transactions.length === 0) {
      alert('Không có dữ liệu để export.');
      return;
    }
    var plain = JSON.stringify(state.transactions);
    encryptData(plain, state.cryptoKey).then(function(enc) {
      var blob = JSON.stringify({ v: 1, iv: enc.iv, ct: enc.ct }, null, 2);
      downloadFile(blob, 'expense-management-export.json', 'application/json');
    })['catch'](function(e) {
      alert('Export thất bại: ' + e.message);
    });
  }

  function importEncrypted() {
    var input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.addEventListener('change', function(e) {
      var file = e.target.files[0];
      if (!file) return;
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
    var headers = ['Sequence', 'Income', 'Expense', 'Expense Label', 'Expense Type', 'Transaction Type', 'Route', 'Bank Route', 'Remark', 'Date', 'Day', 'Month', 'Year'];
    var csv = '\uFEFF' + headers.join(',') + '\n';
    for (var i = 0; i < rows.length; i++) {
      var t = rows[i];
      csv += [
        t.sequence, t.income || 0, t.expense || 0, csvEscape(t.expenseLabel || ''), csvEscape(t.expenseType || ''),
        csvEscape(t.transactionType || ''), csvEscape(t.route || ''), csvEscape(t.bankRoute || ''),
        csvEscape(t.remark || ''), t.date || '', t.day || '', t.month || '', t.year || ''
      ].join(',') + '\n';
    }
    downloadFile(csv, 'expense-management-export.csv', 'text/csv;charset=utf-8');
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

  /* ─── Save ────────────────────────────────────────────── */
  function saveNow() {
    doAutosave();
    var messages = [
      'Đã lưu dữ liệu chi phí thành công!',
      'Dữ liệu đã an toàn!',
      'Lưu xong rồi — tiếp tục theo dõi nhé!',
      'Ghi nhận thành công!',
    ];
    var text = messages[Math.floor(Math.random() * messages.length)];
    var toast = document.createElement('div');
    toast.className = 'expense-toast';
    toast.id = 'expenseSaveMsg';
    toast.textContent = text;
    document.body.appendChild(toast);
    requestAnimationFrame(function() {
      toast.classList.add('expense-toast--show');
    });
    setTimeout(function() {
      toast.classList.remove('expense-toast--show');
      toast.classList.add('expense-toast--hidden');
      setTimeout(function() { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 400);
    }, 2500);
  }

  function loadVersion() {
    fetch(BASE_PATH.replace(/\/$/, '') + '/build-info.json').then(function(r) {
      if (!r.ok) return null;
      return r.json();
    })['catch'](function() { return null; }).then(function(info) {
      var el = document.getElementById('expenseVersion');
      if (!el) return;
      if (!info) {
        el.textContent = 'Phiên bản dịch vụ: ' + new Date().toLocaleDateString('vi-VN') + '-dev';
        return;
      }
      var datePart = info.generated_at_display ? info.generated_at_display.split(' ')[0] : new Date().toLocaleDateString('vi-VN');
      el.textContent = 'Phiên bản dịch vụ: ' + datePart + '-' + info.short_sha;
    });
  }

  /* ─── Init ────────────────────────────────────────────── */
  function init() {
    initGate();
    loadVersion();

    document.getElementById('expenseAddRow').addEventListener('click', addRow);
    document.getElementById('expenseSaveBtn').addEventListener('click', saveNow);
    document.getElementById('expenseUndoBtn').addEventListener('click', undo);
    document.getElementById('expenseSampleBtn').addEventListener('click', loadSampleData);
    document.getElementById('expenseClearBtn').addEventListener('click', clearAllData);
    document.getElementById('expenseExportBtn').addEventListener('click', exportEncrypted);
    document.getElementById('expenseImportBtn').addEventListener('click', importEncrypted);
    document.getElementById('expenseCSVBtn').addEventListener('click', exportCSV);

    document.getElementById('expenseSearch').addEventListener('input', function() {
      state.searchQuery = this.value;
      applyFilters();
      renderTable();
      renderKPIs();
      renderCharts();
      renderInsights();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
