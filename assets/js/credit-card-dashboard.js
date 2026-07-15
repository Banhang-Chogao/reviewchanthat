/**
 * Credit Card Dashboard — business logic
 * Auth: SHA-256 PIN (0512), session-scoped unlock
 * Storage: AES-GCM + IndexedDB adapter (R2-ready interface)
 * UI shells stay in HTML; this file only populates / wires behavior.
 */
(function () {
  'use strict';

  var ACCESS_HASH = '78c72f67941a420cd4e5ee9fdabcaeaba6d72f16160915085f9802220fd83799'; // SHA-256("0512")
  var SESSION_KEY = 'ccd_unlocked';
  var SESSION_PIN_KEY = 'ccd_session_pin';
  var APP_SALT = 'credit-card-dashboard-v1-salt';
  var IDB_NAME = 'credit_card_dashboard_db';
  var IDB_STORE = 'encrypted_data';
  var IDB_KEY = 'ccd-cards';
  var STORAGE_BACKEND = 'indexeddb'; // future: 'r2'

  var CHART_COLORS = [
    'rgba(0,200,83,0.75)', 'rgba(59,130,246,0.75)', 'rgba(245,158,11,0.75)',
    'rgba(239,68,68,0.75)', 'rgba(124,77,255,0.75)', 'rgba(255,138,0,0.75)',
    'rgba(16,185,129,0.75)', 'rgba(99,102,241,0.75)'
  ];

  var state = {
    cards: [],
    cryptoKey: null,
    view: 'home', // home | input | dashboard
    editingId: null,
    search: '',
    sort: 'name-asc',
    showArchived: false,
    selectedCardId: '__all__',
    filters: { bank: '', status: '', reward: '', util: '', due: '' },
    charts: {}
  };

  /* ───────────── Utils ───────────── */
  function $(id) { return document.getElementById(id); }
  function on(el, ev, fn) { if (el) el.addEventListener(ev, fn); }

  function sha256(str) {
    return crypto.subtle.digest('SHA-256', new TextEncoder().encode(str)).then(function (buf) {
      var hex = '', bytes = new Uint8Array(buf);
      for (var i = 0; i < bytes.length; i++) hex += bytes[i].toString(16).padStart(2, '0');
      return hex;
    });
  }

  function deriveKey(pin) {
    var enc = new TextEncoder();
    return crypto.subtle.importKey('raw', enc.encode(pin), 'PBKDF2', false, ['deriveKey']).then(function (base) {
      return crypto.subtle.deriveKey(
        { name: 'PBKDF2', salt: enc.encode(APP_SALT), iterations: 600000, hash: 'SHA-256' },
        base,
        { name: 'AES-GCM', length: 256 },
        false,
        ['encrypt', 'decrypt']
      );
    });
  }

  function a2b(arr) {
    var bin = '';
    for (var i = 0; i < arr.length; i++) bin += String.fromCharCode(arr[i]);
    return btoa(bin);
  }
  function b2a(str) {
    var bin = atob(str), arr = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    return arr;
  }

  function encryptData(plaintext, key) {
    var iv = crypto.getRandomValues(new Uint8Array(12));
    return crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, key, new TextEncoder().encode(plaintext)).then(function (ct) {
      return { iv: a2b(iv), ct: a2b(new Uint8Array(ct)) };
    });
  }

  function decryptData(encrypted, key) {
    return crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: b2a(encrypted.iv) },
      key,
      b2a(encrypted.ct)
    ).then(function (plain) {
      return new TextDecoder().decode(plain);
    });
  }

  function genId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }

  function parseMoney(str) {
    if (typeof str === 'number') return isNaN(str) ? 0 : str;
    if (str === null || str === undefined || str === '') return 0;
    // Accept "12.500.000", "12500000", "12,500,000"
    var s = String(str).trim().replace(/[^\d\-.,]/g, '');
    if (s.indexOf(',') !== -1 && s.indexOf('.') !== -1) {
      // assume . thousands, , decimal OR opposite — prefer last separator as decimal
      if (s.lastIndexOf(',') > s.lastIndexOf('.')) {
        s = s.replace(/\./g, '').replace(',', '.');
      } else {
        s = s.replace(/,/g, '');
      }
    } else if (s.indexOf(',') !== -1) {
      // single comma: thousands if multiple groups, else decimal
      s = (s.match(/,/g) || []).length > 1 ? s.replace(/,/g, '') : s.replace(',', '.');
    } else if (s.indexOf('.') !== -1) {
      // multiple dots → VND thousands
      if ((s.match(/\./g) || []).length > 1) s = s.replace(/\./g, '');
    }
    var n = parseFloat(s);
    return isNaN(n) ? 0 : n;
  }

  function formatVND(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return '0';
    return Math.round(amount).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ' VND';
  }

  function formatNum(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return '0';
    return Math.round(amount).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function clamp(n, min, max) { return Math.max(min, Math.min(max, n)); }

  function isValidISODate(s) {
    if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
    var p = s.split('-').map(Number);
    var d = new Date(p[0], p[1] - 1, p[2]);
    return d.getFullYear() === p[0] && d.getMonth() === p[1] - 1 && d.getDate() === p[2];
  }

  function daysUntil(iso) {
    if (!isValidISODate(iso)) return null;
    var t = new Date();
    t.setHours(0, 0, 0, 0);
    var d = new Date(iso + 'T00:00:00');
    return Math.round((d - t) / 86400000);
  }

  function utilization(card) {
    var lim = Number(card.creditLimit) || 0;
    var bal = Number(card.outstandingBalance) || 0;
    if (lim <= 0) return bal > 0 ? 100 : 0;
    return (bal / lim) * 100;
  }

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function nowLabel() {
    var d = new Date();
    return d.toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  /* ───────────── Storage adapter (IndexedDB → future R2) ───────────── */
  var StorageAdapter = {
    backend: STORAGE_BACKEND,

    openDB: function () {
      return new Promise(function (resolve, reject) {
        var req = indexedDB.open(IDB_NAME, 1);
        req.onupgradeneeded = function (e) {
          var db = e.target.result;
          if (!db.objectStoreNames.contains(IDB_STORE)) {
            db.createObjectStore(IDB_STORE, { keyPath: 'id' });
          }
        };
        req.onsuccess = function (e) { resolve(e.target.result); };
        req.onerror = function (e) { reject(e.target.error); };
      });
    },

    loadEncrypted: function () {
      if (this.backend === 'r2') {
        // Placeholder for Cloudflare R2: return fetch(...).then(r => r.json())
        return Promise.resolve(null);
      }
      return this.openDB().then(function (db) {
        return new Promise(function (resolve, reject) {
          var tx = db.transaction(IDB_STORE, 'readonly');
          var q = tx.objectStore(IDB_STORE).get(IDB_KEY);
          q.onsuccess = function (e) {
            resolve(e.target.result ? e.target.result.data : null);
          };
          q.onerror = function (e) { reject(e.target.error); };
        });
      });
    },

    saveEncrypted: function (payload) {
      if (this.backend === 'r2') {
        // Placeholder for Cloudflare R2 PUT
        return Promise.resolve();
      }
      return this.openDB().then(function (db) {
        return new Promise(function (resolve, reject) {
          var tx = db.transaction(IDB_STORE, 'readwrite');
          tx.objectStore(IDB_STORE).put({ id: IDB_KEY, data: payload, updated: Date.now() });
          tx.oncomplete = function () { resolve(); };
          tx.onerror = function (e) { reject(e.target.error); };
        });
      });
    },

    clear: function () {
      if (this.backend === 'r2') return Promise.resolve();
      return this.openDB().then(function (db) {
        return new Promise(function (resolve, reject) {
          var tx = db.transaction(IDB_STORE, 'readwrite');
          tx.objectStore(IDB_STORE)['delete'](IDB_KEY);
          tx.oncomplete = function () { resolve(); };
          tx.onerror = function (e) { reject(e.target.error); };
        });
      });
    }
  };

  var saveTimer = null;
  function scheduleSave() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(persist, 400);
  }

  function persist() {
    if (!state.cryptoKey) return Promise.resolve();
    var json = JSON.stringify({ version: 1, cards: state.cards, savedAt: new Date().toISOString() });
    return encryptData(json, state.cryptoKey).then(function (enc) {
      return StorageAdapter.saveEncrypted(enc);
    }).then(function () {
      var el = $('ccdSyncLabel');
      if (el) el.textContent = 'Đồng bộ: ' + nowLabel();
    })['catch'](function (e) {
      console.warn('CCD save failed', e);
    });
  }

  function loadCards() {
    return StorageAdapter.loadEncrypted().then(function (enc) {
      if (!enc || !state.cryptoKey) {
        state.cards = [];
        return;
      }
      return decryptData(enc, state.cryptoKey).then(function (json) {
        var data = JSON.parse(json);
        state.cards = Array.isArray(data) ? data : (data.cards || []);
      });
    })['catch'](function (e) {
      console.warn('CCD load failed', e);
      state.cards = [];
    });
  }

  /* ───────────── Auth ───────────── */
  function showApp() {
    var gate = $('ccdGate');
    var app = $('ccdApp');
    if (gate) gate.style.display = 'none';
    if (app) {
      app.hidden = false;
      app.style.display = '';
    }
  }

  function hideApp() {
    var gate = $('ccdGate');
    var app = $('ccdApp');
    if (app) {
      app.hidden = true;
      app.style.display = 'none';
    }
    if (gate) gate.style.display = '';
  }

  function shakeGate() {
    var card = $('ccdGateCard');
    if (!card) return;
    card.classList.remove('ccd-gate__card--shake');
    void card.offsetWidth;
    card.classList.add('ccd-gate__card--shake');
  }

  function afterUnlock() {
    showApp();
    loadCards().then(function () {
      showView('home');
      renderAll();
    });
  }

  function initGate() {
    var input = $('ccdGateInput');
    var btn = $('ccdGateUnlock');
    var err = $('ccdGateError');
    var toggle = $('ccdGateToggle');
    var attempts = 0;
    var last = 0;

    // Session restore — never show app until hash verified path
    if (sessionStorage.getItem(SESSION_KEY) === '1') {
      var pin = sessionStorage.getItem(SESSION_PIN_KEY);
      if (pin) {
        deriveKey(pin).then(function (key) {
          state.cryptoKey = key;
          afterUnlock();
        });
      } else {
        sessionStorage.removeItem(SESSION_KEY);
      }
    }

    function doUnlock() {
      var code = (input.value || '').trim();
      if (!code || code.length !== 4) {
        err.textContent = 'Vui lòng nhập đủ 4 số.';
        shakeGate();
        return;
      }
      var now = Date.now();
      if (now - last < 1500) {
        err.textContent = 'Thử lại sau 1–2 giây.';
        return;
      }
      last = now;
      attempts++;
      if (attempts > 8) {
        err.textContent = 'Quá nhiều lần thử. Tải lại trang để tiếp tục.';
        btn.disabled = true;
        input.disabled = true;
        return;
      }
      sha256(code).then(function (h) {
        if (h === ACCESS_HASH) {
          err.textContent = '';
          sessionStorage.setItem(SESSION_KEY, '1');
          sessionStorage.setItem(SESSION_PIN_KEY, code);
          deriveKey(code).then(function (key) {
            state.cryptoKey = key;
            afterUnlock();
          });
        } else {
          err.textContent = 'Mã truy cập không đúng. Còn ' + Math.max(0, 8 - attempts) + ' lần thử.';
          input.value = '';
          input.focus();
          shakeGate();
        }
      })['catch'](function () {
        err.textContent = 'Không kiểm tra được mã (trình duyệt thiếu Web Crypto).';
      });
    }

    on(btn, 'click', doUnlock);
    on(input, 'keydown', function (e) {
      if (e.key === 'Enter') doUnlock();
    });
    on(toggle, 'click', function () {
      if (!input) return;
      if (input.type === 'password') {
        input.type = 'text';
        toggle.textContent = '🙈';
      } else {
        input.type = 'password';
        toggle.textContent = '👁';
      }
    });
    if (input && sessionStorage.getItem(SESSION_KEY) !== '1') input.focus();

    on($('ccdLogoutBtn'), 'click', logout);
  }

  function logout() {
    try {
      sessionStorage.removeItem(SESSION_KEY);
      sessionStorage.removeItem(SESSION_PIN_KEY);
    } catch (e) {}
    state.cryptoKey = null;
    state.cards = [];
    destroyCharts();
    hideApp();
    var input = $('ccdGateInput');
    var err = $('ccdGateError');
    if (err) err.textContent = '';
    if (input) {
      input.disabled = false;
      input.value = '';
      input.type = 'password';
      input.focus();
    }
    var btn = $('ccdGateUnlock');
    if (btn) btn.disabled = false;
  }

  /* ───────────── Navigation ───────────── */
  function showView(name) {
    state.view = name;
    var home = $('ccdHome');
    var input = $('ccdInput');
    var dash = $('ccdDashboard');
    var title = $('ccdHeaderTitle');
    function setVis(el, on) {
      if (!el) return;
      el.hidden = !on;
      el.style.display = on ? '' : 'none';
    }
    setVis(home, name === 'home');
    setVis(input, name === 'input');
    setVis(dash, name === 'dashboard');
    if (title) {
      title.textContent = name === 'input' ? 'Input Data' : name === 'dashboard' ? 'Credit Card Detail' : 'Credit Card Hub';
    }
    if (name === 'input') renderCardTable();
    if (name === 'dashboard') {
      populateFilters();
      renderDashboard();
    }
  }

  function initNav() {
    on($('ccdOpenInput'), 'click', function () { showView('input'); });
    on($('ccdOpenDashboard'), 'click', function () { showView('dashboard'); });
    on($('ccdNavHome'), 'click', function () { showView('home'); });
    on($('ccdActionInput'), 'click', function () { showView('input'); });
    on($('ccdActionLock'), 'click', logout);
  }

  /* ───────────── Card CRUD ───────────── */
  function emptyCard() {
    return {
      id: genId(),
      cardName: '',
      bank: '',
      cardType: '',
      creditLimit: 0,
      outstandingBalance: 0,
      statementDate: '',
      dueDate: '',
      minimumPayment: 0,
      interestRate: 0,
      annualFee: 0,
      rewardsType: '',
      cashbackPercent: 0,
      rewardPoints: 0,
      foreignTxnFee: 0,
      installmentBalance: 0,
      monthlyInstallment: 0,
      cardStatus: 'Active',
      notes: '',
      archived: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
  }

  function readForm() {
    return {
      id: $('ccdFieldId').value || genId(),
      cardName: ($('ccdFieldCardName').value || '').trim(),
      bank: ($('ccdFieldBank').value || '').trim(),
      cardType: $('ccdFieldCardType').value || '',
      creditLimit: parseMoney($('ccdFieldCreditLimit').value),
      outstandingBalance: parseMoney($('ccdFieldOutstanding').value),
      statementDate: $('ccdFieldStatementDate').value || '',
      dueDate: $('ccdFieldDueDate').value || '',
      minimumPayment: parseMoney($('ccdFieldMinPayment').value),
      interestRate: parseFloat($('ccdFieldInterest').value) || 0,
      annualFee: parseMoney($('ccdFieldAnnualFee').value),
      rewardsType: $('ccdFieldRewardsType').value || '',
      cashbackPercent: parseFloat($('ccdFieldCashback').value) || 0,
      rewardPoints: parseInt($('ccdFieldPoints').value, 10) || 0,
      foreignTxnFee: parseFloat($('ccdFieldFxFee').value) || 0,
      installmentBalance: parseMoney($('ccdFieldInstallBal').value),
      monthlyInstallment: parseMoney($('ccdFieldInstallMonthly').value),
      cardStatus: $('ccdFieldStatus').value || 'Active',
      notes: ($('ccdFieldNotes').value || '').trim(),
      archived: false
    };
  }

  function fillForm(card) {
    $('ccdFieldId').value = card.id || '';
    $('ccdFieldCardName').value = card.cardName || '';
    $('ccdFieldBank').value = card.bank || '';
    $('ccdFieldCardType').value = card.cardType || '';
    $('ccdFieldCreditLimit').value = card.creditLimit != null ? String(card.creditLimit) : '';
    $('ccdFieldOutstanding').value = card.outstandingBalance != null ? String(card.outstandingBalance) : '';
    $('ccdFieldStatementDate').value = card.statementDate || '';
    $('ccdFieldDueDate').value = card.dueDate || '';
    $('ccdFieldMinPayment').value = card.minimumPayment != null ? String(card.minimumPayment) : '';
    $('ccdFieldInterest').value = card.interestRate != null ? String(card.interestRate) : '';
    $('ccdFieldAnnualFee').value = card.annualFee != null ? String(card.annualFee) : '';
    $('ccdFieldRewardsType').value = card.rewardsType || '';
    $('ccdFieldCashback').value = card.cashbackPercent != null ? String(card.cashbackPercent) : '';
    $('ccdFieldPoints').value = card.rewardPoints != null ? String(card.rewardPoints) : '';
    $('ccdFieldFxFee').value = card.foreignTxnFee != null ? String(card.foreignTxnFee) : '';
    $('ccdFieldInstallBal').value = card.installmentBalance != null ? String(card.installmentBalance) : '';
    $('ccdFieldInstallMonthly').value = card.monthlyInstallment != null ? String(card.monthlyInstallment) : '';
    $('ccdFieldStatus').value = card.cardStatus || 'Active';
    $('ccdFieldNotes').value = card.notes || '';
  }

  function validateCard(card, isEdit) {
    if (!card.cardName) return 'Card Name là bắt buộc.';
    if (card.creditLimit === null || card.creditLimit === undefined || isNaN(card.creditLimit)) return 'Credit Limit là bắt buộc.';
    if (card.outstandingBalance === null || card.outstandingBalance === undefined || isNaN(card.outstandingBalance)) return 'Outstanding Balance là bắt buộc.';
    if (!card.statementDate) return 'Statement Date là bắt buộc.';
    if (!card.dueDate) return 'Due Date là bắt buộc.';
    if (card.creditLimit < 0) return 'Credit Limit không được âm.';
    if (card.outstandingBalance < 0) return 'Outstanding Balance không được âm.';
    if (card.minimumPayment < 0 || card.annualFee < 0 || card.installmentBalance < 0 || card.monthlyInstallment < 0) {
      return 'Các số tiền không được âm.';
    }
    if (!isValidISODate(card.statementDate)) return 'Statement Date không hợp lệ.';
    if (!isValidISODate(card.dueDate)) return 'Due Date không hợp lệ.';
    var nameKey = card.cardName.toLowerCase();
    var bankKey = (card.bank || '').toLowerCase();
    var dup = state.cards.some(function (c) {
      if (c.archived) return false;
      if (isEdit && c.id === card.id) return false;
      return (c.cardName || '').toLowerCase() === nameKey && (c.bank || '').toLowerCase() === bankKey && (c.cardStatus || 'Active') !== 'Closed';
    });
    if (dup) return 'Đã có thẻ active trùng Bank + Card Name.';
    return '';
  }

  function openForm(card, title) {
    state.editingId = card ? card.id : null;
    var panel = $('ccdFormPanel');
    if (panel) {
      panel.hidden = false;
      panel.style.display = '';
    }
    $('ccdFormTitle').textContent = title || (card ? 'Sửa thẻ' : 'Thêm thẻ');
    $('ccdFormError').textContent = '';
    fillForm(card || emptyCard());
    if (!card) $('ccdFieldId').value = '';
    $('ccdFieldCardName').focus();
  }

  function closeForm() {
    state.editingId = null;
    var panel = $('ccdFormPanel');
    if (panel) {
      panel.hidden = true;
      panel.style.display = 'none';
    }
    $('ccdCardForm').reset();
    $('ccdFieldId').value = '';
    $('ccdFormError').textContent = '';
  }

  function saveCard(e) {
    if (e) e.preventDefault();
    var draft = readForm();
    var editing = !!$('ccdFieldId').value;
    if (editing) draft.id = $('ccdFieldId').value;
    else draft.id = genId();

    var existing = state.cards.find(function (c) { return c.id === draft.id; });
    if (existing) draft.archived = !!existing.archived;
    draft.createdAt = existing ? existing.createdAt : new Date().toISOString();
    draft.updatedAt = new Date().toISOString();

    var err = validateCard(draft, editing || !!existing);
    if (err) {
      $('ccdFormError').textContent = err;
      return;
    }

    if (existing) {
      var idx = state.cards.indexOf(existing);
      state.cards[idx] = draft;
    } else {
      state.cards.push(draft);
    }
    scheduleSave();
    closeForm();
    renderAll();
  }

  function findCard(id) {
    return state.cards.find(function (c) { return c.id === id; });
  }

  function deleteCard(id) {
    if (!confirm('Xoá thẻ này vĩnh viễn?')) return;
    state.cards = state.cards.filter(function (c) { return c.id !== id; });
    scheduleSave();
    renderAll();
  }

  function duplicateCard(id) {
    var c = findCard(id);
    if (!c) return;
    var copy = JSON.parse(JSON.stringify(c));
    copy.id = genId();
    copy.cardName = (c.cardName || 'Card') + ' (copy)';
    copy.createdAt = new Date().toISOString();
    copy.updatedAt = copy.createdAt;
    copy.archived = false;
    // avoid immediate duplicate name+bank validation by suffix
    state.cards.push(copy);
    scheduleSave();
    renderAll();
  }

  function archiveCard(id) {
    var c = findCard(id);
    if (!c) return;
    c.archived = !c.archived;
    c.updatedAt = new Date().toISOString();
    scheduleSave();
    renderAll();
  }

  function listVisibleCards() {
    var q = (state.search || '').toLowerCase();
    var rows = state.cards.filter(function (c) {
      if (!state.showArchived && c.archived) return false;
      if (!q) return true;
      return [c.cardName, c.bank, c.cardType, c.cardStatus, c.rewardsType, c.notes]
        .join(' ').toLowerCase().indexOf(q) !== -1;
    });
    var sort = state.sort;
    rows.sort(function (a, b) {
      var ua = utilization(a), ub = utilization(b);
      switch (sort) {
        case 'name-desc': return (b.cardName || '').localeCompare(a.cardName || '');
        case 'limit-desc': return (b.creditLimit || 0) - (a.creditLimit || 0);
        case 'balance-desc': return (b.outstandingBalance || 0) - (a.outstandingBalance || 0);
        case 'util-desc': return ub - ua;
        case 'due-asc': return String(a.dueDate || '').localeCompare(String(b.dueDate || ''));
        case 'bank-asc': return (a.bank || '').localeCompare(b.bank || '');
        default: return (a.cardName || '').localeCompare(b.cardName || '');
      }
    });
    return rows;
  }

  function renderCardTable() {
    var tbody = $('ccdCardsTableBody');
    var empty = $('ccdCardsEmpty');
    if (!tbody) return;
    var rows = listVisibleCards();
    tbody.innerHTML = '';
    if (empty) empty.hidden = rows.length > 0;
    rows.forEach(function (c) {
      var util = utilization(c);
      var tr = document.createElement('tr');
      if (c.archived) tr.style.opacity = '0.55';
      tr.innerHTML =
        '<td data-label="Card"><strong>' + esc(c.cardName) + '</strong>' + (c.cardType ? '<br><small>' + esc(c.cardType) + '</small>' : '') + '</td>' +
        '<td data-label="Bank">' + esc(c.bank || '—') + '</td>' +
        '<td data-label="Limit">' + esc(formatNum(c.creditLimit)) + '</td>' +
        '<td data-label="Outstanding">' + esc(formatNum(c.outstandingBalance)) + '</td>' +
        '<td data-label="Util %">' + util.toFixed(1) + '%</td>' +
        '<td data-label="Due">' + esc(c.dueDate || '—') + '</td>' +
        '<td data-label="Status">' + esc(c.cardStatus || 'Active') + (c.archived ? ' · archived' : '') + '</td>' +
        '<td data-label="Actions"><div class="ccd-input__row-actions"></div></td>';
      var actions = tr.querySelector('.ccd-input__row-actions');
      function mk(label, cls, fn) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'ccd-input__btn ccd-input__btn--small' + (cls ? ' ' + cls : '');
        b.textContent = label;
        b.addEventListener('click', fn);
        actions.appendChild(b);
      }
      mk('Edit', '', function () { openForm(c, 'Sửa thẻ'); });
      mk('Dup', '', function () { duplicateCard(c.id); });
      mk(c.archived ? 'Unarchive' : 'Archive', '', function () { archiveCard(c.id); });
      mk('Del', 'ccd-input__btn--danger', function () { deleteCard(c.id); });
      tbody.appendChild(tr);
    });
  }

  function initInputModule() {
    on($('ccdCardNew'), 'click', function () { openForm(null, 'Thêm thẻ'); });
    on($('ccdFormCancel'), 'click', closeForm);
    on($('ccdCardForm'), 'submit', saveCard);
    on($('ccdCardSearch'), 'input', function () {
      state.search = this.value || '';
      renderCardTable();
    });
    on($('ccdCardSort'), 'change', function () {
      state.sort = this.value;
      renderCardTable();
    });
    on($('ccdShowArchived'), 'change', function () {
      state.showArchived = !!this.checked;
      renderCardTable();
    });
    on($('ccdExportCsv'), 'click', function () { exportCSV(listVisibleCards(), 'credit-cards'); });
    on($('ccdExportXlsx'), 'click', function () { exportXLSX(listVisibleCards(), 'credit-cards'); });
    on($('ccdExportPdf'), 'click', function () { exportPDF(listVisibleCards(), 'Credit Cards'); });
  }

  /* ───────────── Metrics & filters ───────────── */
  function activeCards(base) {
    return (base || state.cards).filter(function (c) { return !c.archived; });
  }

  function applyDashFilters(cards) {
    var f = state.filters;
    return cards.filter(function (c) {
      if (f.bank && (c.bank || '') !== f.bank) return false;
      if (f.status && (c.cardStatus || 'Active') !== f.status) return false;
      if (f.reward && (c.rewardsType || '') !== f.reward) return false;
      var u = utilization(c);
      if (f.util === 'low' && u >= 30) return false;
      if (f.util === 'mid' && (u < 30 || u > 80)) return false;
      if (f.util === 'high' && u <= 80) return false;
      if (f.due) {
        var d = daysUntil(c.dueDate);
        if (d === null) return false;
        if (f.due === 'overdue' && d >= 0) return false;
        if (f.due === '7' && (d < 0 || d > 7)) return false;
        if (f.due === '14' && (d < 0 || d > 14)) return false;
      }
      return true;
    });
  }

  function getDashboardCards() {
    var cards = applyDashFilters(activeCards());
    if (state.selectedCardId && state.selectedCardId !== '__all__') {
      cards = cards.filter(function (c) { return c.id === state.selectedCardId; });
    }
    return cards;
  }

  function computeMetrics(cards) {
    var totalLimit = 0, totalOut = 0, totalMin = 0, totalFee = 0, totalInstall = 0;
    var totalInterestWeighted = 0, points = 0;
    var nearDue = 0, over30 = 0, over80 = 0;
    var highestInterest = null, highestCb = null, highestLimit = null;
    var bankDist = {}, rewardDist = {};

    cards.forEach(function (c) {
      totalLimit += Number(c.creditLimit) || 0;
      totalOut += Number(c.outstandingBalance) || 0;
      totalMin += Number(c.minimumPayment) || 0;
      totalFee += Number(c.annualFee) || 0;
      totalInstall += Number(c.monthlyInstallment) || 0;
      points += Number(c.rewardPoints) || 0;
      totalInterestWeighted += (Number(c.interestRate) || 0) * (Number(c.outstandingBalance) || 0);

      var u = utilization(c);
      if (u > 30) over30++;
      if (u > 80) over80++;
      var d = daysUntil(c.dueDate);
      if (d !== null && d >= 0 && d <= 7) nearDue++;

      if (!highestInterest || (Number(c.interestRate) || 0) > (Number(highestInterest.interestRate) || 0)) highestInterest = c;
      if (!highestCb || (Number(c.cashbackPercent) || 0) > (Number(highestCb.cashbackPercent) || 0)) highestCb = c;
      if (!highestLimit || (Number(c.creditLimit) || 0) > (Number(highestLimit.creditLimit) || 0)) highestLimit = c;

      var b = c.bank || 'Other';
      if (!bankDist[b]) bankDist[b] = { outstanding: 0, limit: 0, count: 0 };
      bankDist[b].outstanding += Number(c.outstandingBalance) || 0;
      bankDist[b].limit += Number(c.creditLimit) || 0;
      bankDist[b].count++;

      var r = c.rewardsType || 'None';
      rewardDist[r] = (rewardDist[r] || 0) + 1;
    });

    var available = Math.max(0, totalLimit - totalOut);
    var util = totalLimit > 0 ? (totalOut / totalLimit) * 100 : 0;
    var avgUtil = cards.length ? cards.reduce(function (s, c) { return s + utilization(c); }, 0) / cards.length : 0;
    var avgInterest = totalOut > 0 ? totalInterestWeighted / totalOut : (cards.length ? cards.reduce(function (s, c) { return s + (Number(c.interestRate) || 0); }, 0) / cards.length : 0);
    // Estimated interest next cycle ≈ monthly rate on revolving balance
    var estInterest = totalOut * (avgInterest / 100) / 12;

    return {
      totalLimit: totalLimit,
      totalOut: totalOut,
      available: available,
      util: util,
      totalMin: totalMin,
      totalFee: totalFee,
      totalInstall: totalInstall,
      nearDue: nearDue,
      over30: over30,
      over80: over80,
      highestInterest: highestInterest,
      highestCb: highestCb,
      highestLimit: highestLimit,
      bankDist: bankDist,
      rewardDist: rewardDist,
      avgUtil: avgUtil,
      avgInterest: avgInterest,
      estInterest: estInterest,
      points: points,
      count: cards.length
    };
  }

  /* ───────────── Dashboard render ───────────── */
  function populateFilters() {
    var cards = activeCards();
    var bankSel = $('ccdFilterBank');
    var picker = $('ccdCardPicker');
    if (bankSel) {
      var cur = bankSel.value;
      var banks = {};
      cards.forEach(function (c) { if (c.bank) banks[c.bank] = true; });
      bankSel.innerHTML = '<option value="">Bank: All</option>';
      Object.keys(banks).sort().forEach(function (b) {
        var o = document.createElement('option');
        o.value = b; o.textContent = b;
        bankSel.appendChild(o);
      });
      bankSel.value = cur || '';
    }
    if (picker) {
      var curP = state.selectedCardId;
      picker.innerHTML = '<option value="__all__">Tất cả thẻ (portfolio)</option>';
      cards.forEach(function (c) {
        var o = document.createElement('option');
        o.value = c.id;
        o.textContent = (c.cardName || 'Card') + (c.bank ? ' · ' + c.bank : '');
        picker.appendChild(o);
      });
      picker.value = curP;
      if (picker.value !== curP) {
        state.selectedCardId = '__all__';
        picker.value = '__all__';
      }
    }
  }

  function renderSummary(cards, m) {
    var single = cards.length === 1 ? cards[0] : null;
    $('ccdSumBank').textContent = single ? (single.bank || '—') : (m.count + ' cards');
    $('ccdSumType').textContent = single ? (single.cardType || '—') : 'Portfolio';
    $('ccdSumNetwork').textContent = single ? (single.cardStatus || 'Credit Card') : 'Credit Cards';
    $('ccdSumName').textContent = single ? (single.cardName || '—') : 'All active cards';
    $('ccdSumStatement').textContent = single && single.statementDate ? single.statementDate : '—';
    $('ccdSumDue').textContent = single && single.dueDate ? single.dueDate : (m.nearDue ? m.nearDue + ' near due' : '—');
    $('ccdSumAvailable').textContent = formatVND(m.available);
    $('ccdSumBalance').textContent = formatVND(m.totalOut);

    var tags = $('ccdSumTags');
    if (tags) {
      tags.innerHTML = '';
      var reward = single ? single.rewardsType : '';
      if (reward) {
        var t = document.createElement('span');
        t.className = 'ccd-card-summary__tag ccd-card-summary__tag--reward';
        t.textContent = reward;
        tags.appendChild(t);
      }
      if (single && (single.cashbackPercent || 0) > 0) {
        var t2 = document.createElement('span');
        t2.className = 'ccd-card-summary__tag ccd-card-summary__tag--cashback';
        t2.textContent = 'Cashback ' + single.cashbackPercent + '%';
        tags.appendChild(t2);
      }
      if (!single && m.count) {
        var t3 = document.createElement('span');
        t3.className = 'ccd-card-summary__tag ccd-card-summary__tag--reward';
        t3.textContent = 'Portfolio';
        tags.appendChild(t3);
      }
    }
  }

  function renderKpis(m) {
    $('kpiTotalLimit').textContent = formatNum(m.totalLimit);
    $('kpiTotalOut').textContent = formatNum(m.totalOut);
    $('kpiAvailable').textContent = formatNum(m.available);
    $('kpiUtil').textContent = m.util.toFixed(1) + '%';
    $('kpiMinPay').textContent = formatNum(m.totalMin);
    $('kpiAnnualFees').textContent = formatNum(m.totalFee);
    $('kpiInstall').textContent = formatNum(m.totalInstall);
    $('kpiNearDue').textContent = String(m.nearDue);

    var utilEl = $('kpiUtil');
    var wrap = utilEl && utilEl.closest('.ccd-kpi');
    if (wrap) {
      wrap.dataset.severity = m.util > 80 ? 'critical' : m.util > 30 ? 'warning' : 'good';
    }
  }

  function renderProgress(m) {
    var pct = clamp(m.util, 0, 100);
    var fill = $('ccd-progress-fill');
    var pctEl = $('ccd-progress-percent');
    var section = $('ccdPaymentProgress');
    if (fill) fill.style.width = pct + '%';
    if (pctEl) pctEl.textContent = pct.toFixed(1) + '%';
    if ($('ccdProgressMeta')) $('ccdProgressMeta').textContent = formatNum(m.totalOut) + ' / ' + formatNum(m.totalLimit) + ' VND used';
    if ($('ccdProgressRemain')) {
      $('ccdProgressRemain').textContent = pct > 80 ? 'Critical: above 80%' : pct > 30 ? 'Warning: above 30%' : 'Healthy: under 30%';
    }
    if (section) {
      section.dataset.status = pct > 80 ? 'overdue' : pct > 30 ? 'warning' : 'normal';
    }
  }

  function renderBankBars(m) {
    var wrap = $('ccdBankBreakdown');
    if (!wrap) return;
    var entries = Object.keys(m.bankDist).map(function (k) {
      return { bank: k, out: m.bankDist[k].outstanding, limit: m.bankDist[k].limit };
    }).sort(function (a, b) { return b.out - a.out; });
    var max = entries.reduce(function (s, e) { return Math.max(s, e.out); }, 0) || 1;
    var colors = ['#ff4d4d', '#2196f3', '#ff8a00', '#7c4dff', '#00c853', '#3b82f6'];
    var html = '<h3 class="ccd-spending__subtitle">Outstanding by Bank</h3>';
    if (!entries.length) {
      html += '<p style="color:var(--muted);font-size:.85rem">Chưa có dữ liệu thẻ.</p>';
    } else {
      entries.forEach(function (e, i) {
        var pct = Math.round((e.out / max) * 100);
        var share = m.totalOut > 0 ? Math.round((e.out / m.totalOut) * 100) : 0;
        html += '<div class="ccd-spending__category" data-color="' + colors[i % colors.length] + '">' +
          '<div class="ccd-spending__category-label"><span>' + esc(e.bank) + '</span><span class="ccd-spending__category-pct">' + share + '%</span></div>' +
          '<div class="ccd-spending__category-bar"><span style="width:' + pct + '%;background:' + colors[i % colors.length] + '"></span></div>' +
          '</div>';
      });
    }
    wrap.innerHTML = html;

    // Limit by bank trend bars
    var chart = $('ccd-trend-chart');
    var totalEl = $('ccdTrendTotal');
    if (totalEl) totalEl.textContent = formatNum(m.totalLimit);
    if (chart) {
      chart.innerHTML = '';
      var maxL = entries.reduce(function (s, e) { return Math.max(s, e.limit); }, 0) || 1;
      (entries.length ? entries : [{ bank: '—', limit: 0 }]).forEach(function (e) {
        var h = Math.max(8, Math.round((e.limit / maxL) * 100));
        var bar = document.createElement('div');
        bar.className = 'ccd-spending__trend-bar';
        bar.innerHTML = '<span style="height:' + h + '%"><span>' + esc((e.bank || '—').slice(0, 6)) + '</span></span>';
        chart.appendChild(bar);
      });
    }
  }

  function destroyCharts() {
    Object.keys(state.charts).forEach(function (k) {
      try { state.charts[k].destroy(); } catch (e) {}
      delete state.charts[k];
    });
  }

  function ensureChart(id, cfg) {
    if (typeof Chart === 'undefined') return;
    var canvas = $(id);
    if (!canvas) return;
    if (state.charts[id]) {
      try { state.charts[id].destroy(); } catch (e) {}
    }
    state.charts[id] = new Chart(canvas.getContext('2d'), cfg);
  }

  function renderCharts(cards, m) {
    if (typeof Chart === 'undefined') {
      var tries = 0;
      var t = setInterval(function () {
        tries++;
        if (typeof Chart !== 'undefined') {
          clearInterval(t);
          renderCharts(cards, m);
        } else if (tries > 20) clearInterval(t);
      }, 200);
      return;
    }

    var labels = cards.map(function (c) { return c.cardName || 'Card'; });
    var utils = cards.map(function (c) { return +utilization(c).toFixed(1); });
    var interests = cards.map(function (c) { return Number(c.interestRate) || 0; });
    var rewards = cards.map(function (c) {
      return (Number(c.cashbackPercent) || 0) * 10 + (Number(c.rewardPoints) || 0) / 1000;
    });
    var pays = cards.map(function (c) {
      return (Number(c.minimumPayment) || 0) + (Number(c.monthlyInstallment) || 0);
    });

    var baseOpts = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { font: { size: 9 }, maxRotation: 45, minRotation: 0 } },
        y: { beginAtZero: true, ticks: { font: { size: 9 } } }
      }
    };

    ensureChart('ccdChartUtil', {
      type: 'bar',
      data: {
        labels: labels.length ? labels : ['—'],
        datasets: [{ data: labels.length ? utils : [0], backgroundColor: CHART_COLORS, borderRadius: 4 }]
      },
      options: baseOpts
    });

    ensureChart('ccdChartInterest', {
      type: 'bar',
      data: {
        labels: labels.length ? labels : ['—'],
        datasets: [{ data: labels.length ? interests : [0], backgroundColor: 'rgba(239,68,68,0.7)', borderRadius: 4 }]
      },
      options: baseOpts
    });

    ensureChart('ccdChartRewards', {
      type: 'bar',
      data: {
        labels: labels.length ? labels : ['—'],
        datasets: [{ data: labels.length ? rewards : [0], backgroundColor: 'rgba(0,200,83,0.7)', borderRadius: 4 }]
      },
      options: baseOpts
    });

    ensureChart('ccdChartPayments', {
      type: 'doughnut',
      data: {
        labels: labels.length ? labels : ['—'],
        datasets: [{ data: labels.length ? pays : [1], backgroundColor: CHART_COLORS }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { font: { size: 10 }, boxWidth: 10 } } }
      }
    });
  }

  function renderRewards(m) {
    var estCb = 0;
    getDashboardCards().forEach(function (c) {
      // rough estimate: cashback% of outstanding (illustrative)
      estCb += (Number(c.outstandingBalance) || 0) * ((Number(c.cashbackPercent) || 0) / 100);
    });
    if ($('ccdRewardCashback')) $('ccdRewardCashback').textContent = formatVND(estCb);
    if ($('ccdRewardPoints')) $('ccdRewardPoints').textContent = formatNum(m.points);
    if ($('ccdRewardBestCb')) {
      $('ccdRewardBestCb').textContent = m.highestCb ? (m.highestCb.cardName || '—') : '—';
    }
    if ($('ccdRewardBestCbRate')) {
      $('ccdRewardBestCbRate').textContent = m.highestCb ? ((m.highestCb.cashbackPercent || 0) + '%') : '';
    }
    if ($('ccdRewardHighLimit')) {
      $('ccdRewardHighLimit').textContent = m.highestLimit ? (m.highestLimit.cardName || '—') : '—';
    }
    if ($('ccdRewardHighLimitVal')) {
      $('ccdRewardHighLimitVal').textContent = m.highestLimit ? formatVND(m.highestLimit.creditLimit) : '';
    }
  }

  function renderTimeline(cards) {
    var flow = $('ccd-timeline-flow');
    if (!flow) return;
    var items = cards.slice().filter(function (c) { return c.dueDate; })
      .sort(function (a, b) { return String(a.dueDate).localeCompare(String(b.dueDate)); })
      .slice(0, 6);
    if (!items.length) {
      flow.innerHTML = '<div class="ccd-timeline__step ccd-timeline__step--pending"><span class="ccd-timeline__step-icon">○</span><span class="ccd-timeline__step-label">No due dates</span><span class="ccd-timeline__step-date">—</span></div>';
      return;
    }
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    flow.innerHTML = items.map(function (c) {
      var d = daysUntil(c.dueDate);
      var cls = 'ccd-timeline__step--pending';
      var icon = '○';
      if (d !== null && d < 0) { cls = 'ccd-timeline__step--done'; icon = '⚠'; }
      else if (d !== null && d <= 3) { cls = 'ccd-timeline__step--active'; icon = '●'; }
      else if (d !== null && d <= 7) { cls = 'ccd-timeline__step--upcoming'; icon = '○'; }
      var label = (c.cardName || 'Card').slice(0, 14);
      var dateLabel = (c.dueDate || '').slice(5);
      return '<div class="ccd-timeline__step ' + cls + '">' +
        '<span class="ccd-timeline__step-icon">' + icon + '</span>' +
        '<span class="ccd-timeline__step-label">' + esc(label) + '</span>' +
        '<span class="ccd-timeline__step-date">' + esc(dateLabel) + '</span></div>';
    }).join('');
  }

  function renderSchedule(cards) {
    var body = $('ccdScheduleBody');
    if (!body) return;
    body.innerHTML = '';
    if (!cards.length) {
      body.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:1rem">Chưa có thẻ. Vào Input Data để thêm.</td></tr>';
      return;
    }
    cards.slice().sort(function (a, b) {
      return String(a.dueDate || '9999').localeCompare(String(b.dueDate || '9999'));
    }).forEach(function (c) {
      var u = utilization(c);
      var tr = document.createElement('tr');
      var statusClass = u > 80 ? 'ccd-badge--overdue' : (u > 30 ? 'ccd-badge' : 'ccd-badge--paid');
      // reuse badge classes if present; fallback text
      tr.innerHTML =
        '<td>' + esc(c.cardName) + '</td>' +
        '<td>' + esc(c.bank || '—') + '</td>' +
        '<td>' + esc(c.dueDate || '—') + '</td>' +
        '<td>' + esc(formatNum(c.minimumPayment)) + '</td>' +
        '<td>' + esc(formatNum(c.monthlyInstallment)) + '</td>' +
        '<td>' + u.toFixed(1) + '%</td>' +
        '<td><span class="ccd-badge ' + statusClass + '">' + esc(c.cardStatus || 'Active') + '</span></td>';
      body.appendChild(tr);
    });
  }

  function severityClass(level) {
    if (level === 'critical') return 'ccd-insight-card--critical ccd-insight-card--alert';
    if (level === 'warning') return 'ccd-insight-card--warning ccd-insight-card--alert';
    return 'ccd-insight-card--good ccd-insight-card--opportunity';
  }

  function severityIcon(level) {
    if (level === 'critical') return '🚨';
    if (level === 'warning') return '⚠️';
    return '✅';
  }

  function buildInsights(cards, m) {
    var list = [];
    if (!cards.length) {
      list.push({ level: 'warning', title: 'No cards yet', text: 'Add cards in Input Data to unlock analytics and AI insights.' });
      return list;
    }

    var utilLevel = m.util > 80 ? 'critical' : m.util > 30 ? 'warning' : 'good';
    var utilLabel = m.util > 80 ? 'high' : m.util > 30 ? 'moderate' : 'healthy';
    list.push({
      level: utilLevel,
      title: 'Overall utilization is ' + utilLabel,
      text: 'Portfolio utilization is <strong>' + m.util.toFixed(1) + '%</strong> (avg card ' + m.avgUtil.toFixed(1) + '%). Recommended under 30% for credit score health.'
    });

    if (m.util > 30) {
      list.push({
        level: m.util > 80 ? 'critical' : 'warning',
        title: 'Credit utilization exceeds 30%',
        text: 'Keeping utilization under 30% can improve credit score. Available credit: <strong>' + formatVND(m.available) + '</strong>.'
      });
    } else {
      list.push({
        level: 'good',
        title: 'Opportunities to improve credit score',
        text: 'Utilization is healthy. Maintain on-time payments and avoid new maxed balances.'
      });
    }

    if (m.highestInterest) {
      list.push({
        level: (m.highestInterest.interestRate || 0) > 20 ? 'warning' : 'good',
        title: 'Pay highest interest first',
        text: 'Card <strong>' + esc(m.highestInterest.cardName) + '</strong> has the highest interest at <strong>' + (m.highestInterest.interestRate || 0) + '%/year</strong>. Prioritize this balance.'
      });
    }

    if (m.highestCb && (m.highestCb.cashbackPercent || 0) > 0) {
      list.push({
        level: 'good',
        title: 'Highest cashback card',
        text: '<strong>' + esc(m.highestCb.cardName) + '</strong> offers <strong>' + (m.highestCb.cashbackPercent || 0) + '%</strong> cashback — route bonus-category spend here when possible.'
      });
    }

    var upcoming = cards.filter(function (c) {
      var d = daysUntil(c.dueDate);
      return d !== null && d >= 0 && d <= 14;
    }).sort(function (a, b) { return daysUntil(a.dueDate) - daysUntil(b.dueDate); });
    if (upcoming.length) {
      list.push({
        level: daysUntil(upcoming[0].dueDate) <= 3 ? 'critical' : 'warning',
        title: 'Upcoming due dates',
        text: upcoming.slice(0, 3).map(function (c) {
          return esc(c.cardName) + ' (' + esc(c.dueDate) + ', ' + daysUntil(c.dueDate) + 'd)';
        }).join(' · ')
      });
    }

    list.push({
      level: m.estInterest > 500000 ? 'warning' : 'good',
      title: 'Estimated interest next cycle',
      text: 'If revolving balances stay similar and only minimums are paid, estimated interest ≈ <strong>' + formatVND(m.estInterest) + '</strong> next month (avg rate ' + m.avgInterest.toFixed(2) + '%/yr).'
    });

    list.push({
      level: 'good',
      title: 'Suggested payment priority',
      text: '1) Overdue / due ≤3 days · 2) Highest interest · 3) Utilization &gt;80% · 4) Remaining balances. Min payments total: <strong>' + formatVND(m.totalMin) + '</strong>.'
    });

    if (m.over80 > 0) {
      list.push({
        level: 'critical',
        title: 'Cards over 80% utilization',
        text: '<strong>' + m.over80 + '</strong> card(s) above 80%. Consider pay-down or limit increase to reduce score impact.'
      });
    } else if (m.over30 > 0) {
      list.push({
        level: 'warning',
        title: 'Cards over 30% utilization',
        text: '<strong>' + m.over30 + '</strong> card(s) above the 30% guideline.'
      });
    }

    return list;
  }

  function renderInsights(cards, m) {
    var box = $('ccdInsightsList');
    if (!box) return;
    var insights = buildInsights(cards, m);
    box.innerHTML = insights.map(function (ins) {
      return '<div class="ccd-insight-card ' + severityClass(ins.level) + '">' +
        '<div class="ccd-insight-card__icon">' + severityIcon(ins.level) + '</div>' +
        '<div class="ccd-insight-card__body"><h3>' + esc(ins.title) + '</h3><p>' + ins.text + '</p></div></div>';
    }).join('');
  }

  function renderNotifications(cards, m) {
    var list = $('ccd-notifications');
    if (!list) return;
    var items = [];
    cards.forEach(function (c) {
      var d = daysUntil(c.dueDate);
      if (d !== null && d < 0) {
        items.push({ cls: 'ccd-notification--alert', icon: '🔔', text: esc(c.cardName) + ' overdue by ' + Math.abs(d) + ' day(s)', time: c.dueDate });
      } else if (d !== null && d <= 7) {
        items.push({ cls: 'ccd-notification--alert', icon: '🔔', text: 'Payment due in ' + d + ' day(s): ' + esc(c.cardName), time: c.dueDate });
      }
      if (utilization(c) > 80) {
        items.push({ cls: 'ccd-notification--warning', icon: '⚠️', text: esc(c.cardName) + ' utilization ' + utilization(c).toFixed(0) + '%', time: 'Now' });
      }
    });
    if (m.highestCb && (m.highestCb.cashbackPercent || 0) > 0) {
      items.push({ cls: 'ccd-notification--promo', icon: '🎉', text: 'Best cashback: ' + esc(m.highestCb.cardName) + ' (' + m.highestCb.cashbackPercent + '%)', time: 'Tip' });
    }
    if (m.points > 0) {
      items.push({ cls: 'ccd-notification--reward', icon: '📈', text: 'Portfolio points: ' + formatNum(m.points), time: 'Rewards' });
    }
    if (!items.length) {
      items.push({ cls: 'ccd-notification--promo', icon: '✨', text: 'No urgent alerts. Add or update cards anytime.', time: 'OK' });
    }
    list.innerHTML = items.slice(0, 8).map(function (it) {
      return '<div class="ccd-notification ' + it.cls + '"><span class="ccd-notification__icon">' + it.icon + '</span>' +
        '<div class="ccd-notification__body"><span class="ccd-notification__text">' + it.text + '</span>' +
        '<span class="ccd-notification__time">' + esc(it.time) + '</span></div></div>';
    }).join('');
  }

  function assistantAnswer(text, cards, m) {
    var lower = (text || '').toLowerCase();
    if (lower.indexOf('pay first') !== -1 || lower.indexOf('priority') !== -1) {
      if (!m.highestInterest) return 'Add cards first so I can rank payment priority.';
      return 'Pay first: ' + (m.highestInterest.cardName || 'highest interest card') +
        ' at ' + (m.highestInterest.interestRate || 0) + '%/year. Then clear near-due cards and any utilization above 80%.';
    }
    if (lower.indexOf('utilization') !== -1 || lower.indexOf('util') !== -1) {
      return 'Overall utilization is ' + m.util.toFixed(1) + '% (' +
        (m.util > 80 ? 'critical' : m.util > 30 ? 'moderate' : 'healthy') +
        '). Available credit: ' + formatVND(m.available) + '. Aim for under 30%.';
    }
    if (lower.indexOf('interest') !== -1) {
      return 'Estimated interest next cycle ≈ ' + formatVND(m.estInterest) +
        ' if balances revolve at avg ' + m.avgInterest.toFixed(2) + '%/year. Paying more than the minimum reduces this quickly.';
    }
    if (lower.indexOf('cashback') !== -1 || lower.indexOf('reward') !== -1) {
      if (!m.highestCb) return 'No cashback data yet.';
      return 'Highest cashback: ' + (m.highestCb.cardName || '—') + ' (' + (m.highestCb.cashbackPercent || 0) + '%). Total points: ' + formatNum(m.points) + '.';
    }
    if (lower.indexOf('due') !== -1 || lower.indexOf('late') !== -1) {
      return m.nearDue + ' card(s) due within 7 days. Total minimum payment: ' + formatVND(m.totalMin) + '. Enable calendar reminders for each due date.';
    }
    return 'I can help with payment priority, utilization, estimated interest, cashback, and due dates based on your saved cards. Try the suggested prompts.';
  }

  function initAssistant() {
    var input = $('ccd-assistant-input');
    var sendBtn = $('ccd-assistant-send');
    var messages = $('ccd-assistant-messages');
    var prompts = document.querySelectorAll('.ccd-assistant__prompt');
    if (!input || !sendBtn || !messages) return;
    var typing = false;

    function add(role, text) {
      var msg = document.createElement('div');
      msg.className = 'ccd-assistant__message ccd-assistant__message--' + role;
      msg.textContent = text;
      messages.appendChild(msg);
      messages.scrollTop = messages.scrollHeight;
    }

    function typeBot(text) {
      typing = true;
      var msg = document.createElement('div');
      msg.className = 'ccd-assistant__message ccd-assistant__message--bot';
      messages.appendChild(msg);
      var i = 0;
      function step() {
        if (i < text.length) {
          msg.textContent += text.charAt(i++);
          messages.scrollTop = messages.scrollHeight;
          setTimeout(step, 12 + Math.random() * 18);
        } else typing = false;
      }
      step();
    }

    function handle(text) {
      if (typing || !text) return;
      add('user', text);
      var cards = getDashboardCards();
      var m = computeMetrics(cards);
      typeBot(assistantAnswer(text, cards, m));
    }

    on(sendBtn, 'click', function () {
      var t = input.value.trim();
      input.value = '';
      handle(t);
    });
    on(input, 'keydown', function (e) {
      if (e.key === 'Enter') {
        var t = input.value.trim();
        input.value = '';
        handle(t);
      }
    });
    prompts.forEach(function (btn) {
      on(btn, 'click', function () {
        handle(btn.getAttribute('data-prompt') || btn.textContent.replace(/^"|"$/g, ''));
      });
    });
  }

  function initDashboardControls() {
    on($('ccdCardPicker'), 'change', function () {
      state.selectedCardId = this.value;
      renderDashboard();
    });
    ['ccdFilterBank', 'ccdFilterStatus', 'ccdFilterReward', 'ccdFilterUtil', 'ccdFilterDue'].forEach(function (id) {
      on($(id), 'change', function () {
        state.filters.bank = $('ccdFilterBank').value;
        state.filters.status = $('ccdFilterStatus').value;
        state.filters.reward = $('ccdFilterReward').value;
        state.filters.util = $('ccdFilterUtil').value;
        state.filters.due = $('ccdFilterDue').value;
        renderDashboard();
      });
    });
    on($('ccdHistoryRefresh'), 'click', renderDashboard);
    on($('ccdDashExportCsv'), 'click', function () { exportCSV(getDashboardCards(), 'ccd-filtered'); });
    on($('ccdDashExportXlsx'), 'click', function () { exportXLSX(getDashboardCards(), 'ccd-filtered'); });
    on($('ccdDashExportPdf'), 'click', function () { exportPDF(getDashboardCards(), 'Credit Card Dashboard'); });
    on($('ccdActionStatement'), 'click', function () { exportPDF(getDashboardCards(), 'Credit Card Statement'); });
    on($('ccdActionPay'), 'click', function () {
      var m = computeMetrics(getDashboardCards());
      if (!m.highestInterest) { alert('Chưa có thẻ để ưu tiên thanh toán.'); return; }
      alert('Priority pay: ' + m.highestInterest.cardName + ' · Interest ' + (m.highestInterest.interestRate || 0) + '%/yr · Balance ' + formatVND(m.highestInterest.outstandingBalance));
    });
    on($('ccdActionCopy'), 'click', function () {
      var m = computeMetrics(getDashboardCards());
      var text = 'Credit portfolio\nLimit: ' + formatVND(m.totalLimit) +
        '\nOutstanding: ' + formatVND(m.totalOut) +
        '\nAvailable: ' + formatVND(m.available) +
        '\nUtilization: ' + m.util.toFixed(1) + '%' +
        '\nMin payment: ' + formatVND(m.totalMin);
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () {
          var btn = $('ccdActionCopy');
          var old = btn.textContent;
          btn.textContent = '✅ Copied!';
          setTimeout(function () { btn.textContent = old; }, 1600);
        });
      } else {
        alert(text);
      }
    });
  }

  function renderDashboard() {
    var cards = getDashboardCards();
    var m = computeMetrics(cards);
    renderSummary(cards, m);
    renderKpis(m);
    renderProgress(m);
    renderBankBars(m);
    renderCharts(cards, m);
    renderRewards(m);
    renderTimeline(cards);
    renderSchedule(cards);
    renderInsights(cards, m);
    renderNotifications(cards, m);
    var el = $('ccdSyncLabel');
    if (el && !el.textContent) el.textContent = 'Local · ' + nowLabel();
  }

  function renderAll() {
    if (state.view === 'input') renderCardTable();
    if (state.view === 'dashboard') {
      populateFilters();
      renderDashboard();
    }
  }

  /* ───────────── Export ───────────── */
  function rowsForExport(cards) {
    return cards.map(function (c) {
      return {
        'Card Name': c.cardName,
        Bank: c.bank,
        'Card Type': c.cardType,
        'Credit Limit': c.creditLimit,
        'Outstanding Balance': c.outstandingBalance,
        'Utilization %': +utilization(c).toFixed(2),
        'Statement Date': c.statementDate,
        'Due Date': c.dueDate,
        'Minimum Payment': c.minimumPayment,
        'Interest Rate': c.interestRate,
        'Annual Fee': c.annualFee,
        'Rewards Type': c.rewardsType,
        'Cashback %': c.cashbackPercent,
        'Reward Points': c.rewardPoints,
        'Foreign Txn Fee %': c.foreignTxnFee,
        'Installment Balance': c.installmentBalance,
        'Monthly Installment': c.monthlyInstallment,
        'Card Status': c.cardStatus,
        Notes: c.notes,
        Archived: c.archived ? 'yes' : 'no'
      };
    });
  }

  function downloadBlob(content, filename, mime) {
    var blob = new Blob([content], { type: mime });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 100);
  }

  function exportCSV(cards, name) {
    var rows = rowsForExport(cards);
    if (!rows.length) { alert('Không có dữ liệu để export.'); return; }
    var headers = Object.keys(rows[0]);
    var lines = ['\uFEFF' + headers.join(',')];
    rows.forEach(function (r) {
      lines.push(headers.map(function (h) {
        var v = r[h] == null ? '' : String(r[h]);
        if (/[",\n]/.test(v)) v = '"' + v.replace(/"/g, '""') + '"';
        return v;
      }).join(','));
    });
    downloadBlob(lines.join('\n'), (name || 'credit-cards') + '.csv', 'text/csv;charset=utf-8');
  }

  function exportXLSX(cards, name) {
    if (typeof XLSX === 'undefined') {
      alert('Thư viện Excel chưa sẵn sàng. Thử lại sau giây lát hoặc dùng CSV.');
      return;
    }
    var rows = rowsForExport(cards);
    if (!rows.length) { alert('Không có dữ liệu để export.'); return; }
    var wb = XLSX.utils.book_new();
    var ws = XLSX.utils.json_to_sheet(rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Cards');
    XLSX.writeFile(wb, (name || 'credit-cards') + '.xlsx');
  }

  function exportPDF(cards, title) {
    if (typeof jspdf === 'undefined' && !(window.jspdf && window.jspdf.jsPDF)) {
      // fallback: print dashboard
      window.print();
      return;
    }
    var JsPDF = (window.jspdf && window.jspdf.jsPDF) || (jspdf && jspdf.jsPDF);
    var doc = new JsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' });
    var m = computeMetrics(cards);
    doc.setFontSize(14);
    doc.text(title || 'Credit Card Dashboard', 40, 40);
    doc.setFontSize(10);
    doc.text('Generated: ' + nowLabel(), 40, 58);
    doc.text('Cards: ' + cards.length + ' | Limit: ' + formatNum(m.totalLimit) +
      ' | Outstanding: ' + formatNum(m.totalOut) + ' | Util: ' + m.util.toFixed(1) + '%', 40, 74);

    var y = 100;
    doc.setFontSize(9);
    cards.forEach(function (c, i) {
      if (y > 520) { doc.addPage(); y = 40; }
      var line = (i + 1) + '. ' + (c.cardName || '') + ' | ' + (c.bank || '') +
        ' | Limit ' + formatNum(c.creditLimit) +
        ' | Out ' + formatNum(c.outstandingBalance) +
        ' | Util ' + utilization(c).toFixed(1) + '%' +
        ' | Due ' + (c.dueDate || '—') +
        ' | Min ' + formatNum(c.minimumPayment);
      doc.text(line.substring(0, 140), 40, y);
      y += 16;
    });
    doc.save((title || 'credit-card-dashboard').replace(/\s+/g, '-').toLowerCase() + '.pdf');
  }

  /* ───────────── Reveal animation (existing) ───────────── */
  function initReveal() {
    var cards = document.querySelectorAll('#ccdDashboard .ccd-card');
    if (!('IntersectionObserver' in window)) return;
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }
      });
    }, { threshold: 0.08 });
    cards.forEach(function (card, i) {
      card.style.opacity = '0';
      card.style.transform = 'translateY(16px)';
      card.style.transition = 'opacity .5s ease, transform .5s ease';
      card.style.transitionDelay = (i * 0.04) + 's';
      observer.observe(card);
    });
  }

  /* ───────────── Boot ───────────── */
  function init() {
    var app = $('ccd-app');
    if (!app) return;
    // Ensure app shell is hidden until auth (defense in depth)
    hideApp();
    initGate();
    initNav();
    initInputModule();
    initDashboardControls();
    initAssistant();
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) persist();
    });
    // reveal after first dashboard show
    var origShow = showView;
    // mild enhancement once dashboard opens
    on($('ccdOpenDashboard'), 'click', function () {
      setTimeout(initReveal, 120);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
