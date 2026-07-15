/**
 * MCC DB — Merchant Category Code & Vietnam BIN Intelligence Center
 * Data: static/data/mcc-db.json (built by scripts/sync_mcc_db.py)
 * Never fabricates MCC/BIN; Unknown stays Unknown.
 */
(function () {
  'use strict';

  var PAGE_SIZE = 50;
  var DATA_URL = 'data/mcc-db.json';

  var S = {
    mccs: [],
    bins: [],
    meta: {},
    loadedAt: null,
    tab: 'mcc',
    q: '',
    mccFilters: { industry: '', parent: '', cashback: '', status: '' },
    binFilters: { bank: '', brand: '', type: '', active: '' },
    mccPage: 0,
    binPage: 0,
    filteredMcc: [],
    filteredBin: [],
    globalHits: null // null | { mccs, bins, q }
  };

  function $(id) { return document.getElementById(id); }
  function on(el, ev, fn) { if (el) el.addEventListener(ev, fn); }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function baseURL() {
    var b = document.body && document.body.getAttribute('data-site-base');
    if (!b || b === '/') return '';
    return b.replace(/\/?$/, '/');
  }
  function dataUrl() {
    return baseURL() + DATA_URL + '?_=' + Date.now();
  }
  function setStatus(msg, isErr) {
    var el = $('mccSyncStatus');
    if (!el) return;
    el.textContent = msg || '';
    el.style.color = isErr ? '#be123c' : '';
  }
  function badgeClass(status) {
    if (status === 'verified') return 'mcc-badge mcc-badge--ok';
    if (status === 'needs-review') return 'mcc-badge mcc-badge--warn';
    if (status === 'community-sourced') return 'mcc-badge mcc-badge--muted';
    return 'mcc-badge';
  }
  function unknown(v) {
    if (v == null || v === '' || v === false && arguments.length > 1) return 'Unknown';
    return v;
  }

  /* ── Load ── */
  function loadData() {
    setStatus('Đang tải dữ liệu…');
    return fetch(dataUrl(), { cache: 'no-cache', credentials: 'omit' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        S.mccs = Array.isArray(data.mccs) ? data.mccs : [];
        S.bins = Array.isArray(data.bins) ? data.bins : [];
        S.meta = data.meta || {};
        S.loadedAt = new Date().toISOString();
        S.mccPage = 0;
        S.binPage = 0;
        populateFilterOptions();
        applyFilters();
        renderKpis();
        renderInsights();
        renderReport();
        setStatus('Synced · MCC ' + S.mccs.length + ' · BIN ' + S.bins.length + ' · ' + (S.meta.lastSync || S.loadedAt));
      })
      .catch(function (err) {
        setStatus('Lỗi tải dữ liệu: ' + err.message, true);
        var tb = $('mccTableBody');
        if (tb) tb.innerHTML = '<tr><td colspan="6">Không tải được data/mcc-db.json. Chạy <code>python3 scripts/sync_mcc_db.py</code>.</td></tr>';
      });
  }

  /* ── Filters ── */
  function uniqueSorted(arr) {
    return Array.from(new Set(arr.filter(Boolean))).sort(function (a, b) {
      return String(a).localeCompare(String(b), 'vi');
    });
  }
  function fillSelect(sel, values, allLabel) {
    if (!sel) return;
    var cur = sel.value;
    var html = '<option value="">' + esc(allLabel) + '</option>';
    values.forEach(function (v) {
      html += '<option value="' + esc(v) + '">' + esc(v) + '</option>';
    });
    sel.innerHTML = html;
    if (cur && values.indexOf(cur) >= 0) sel.value = cur;
  }
  function populateFilterOptions() {
    fillSelect($('fMccIndustry'), uniqueSorted(S.mccs.map(function (m) { return m.industry; })), 'All industries');
    fillSelect($('fMccParent'), uniqueSorted(S.mccs.map(function (m) { return m.parentCategory; })), 'All categories');
    fillSelect($('fMccCashback'), uniqueSorted(S.mccs.map(function (m) { return m.cashbackCategory; })), 'All cashback');
    fillSelect($('fBinBank'), uniqueSorted(S.bins.map(function (b) { return b.bank; })), 'All banks');
  }

  function norm(s) { return String(s || '').toLowerCase().trim(); }

  function matchQuery(haystack, q) {
    if (!q) return true;
    return haystack.indexOf(q) >= 0;
  }

  function mccSearchBlob(m) {
    return norm([
      m.mcc, m.name, m.nameVi, m.nameViExact, m.industry, m.industryVi,
      m.parentCategory, m.description, m.cashbackCategory, m.cashbackCategoryVi,
      m.visaCategory, m.mastercardCategory, m.scope, m.verificationStatus,
      (m.typicalMerchants || []).join(' '),
      (m.keywords || []).join(' '),
      m.notes, m.source
    ].join(' '));
  }

  function binSearchBlob(b) {
    return norm([
      b.bin, b.bank, b.bankCode, b.cardBrand, b.network, b.cardType,
      b.product, b.level, b.consumerBusiness, b.notes, b.source,
      b.verificationStatus
    ].join(' '));
  }

  function filterMccs() {
    var q = norm(S.q);
    var f = S.mccFilters;
    return S.mccs.filter(function (m) {
      if (f.industry && m.industry !== f.industry) return false;
      if (f.parent && m.parentCategory !== f.parent) return false;
      if (f.cashback && m.cashbackCategory !== f.cashback) return false;
      if (f.status && m.verificationStatus !== f.status) return false;
      if (q && !matchQuery(mccSearchBlob(m), q)) return false;
      return true;
    });
  }

  function filterBins() {
    var q = norm(S.q);
    var f = S.binFilters;
    return S.bins.filter(function (b) {
      if (f.bank && b.bank !== f.bank) return false;
      if (f.brand && b.cardBrand !== f.brand) return false;
      if (f.type && b.cardType !== f.type) return false;
      if (f.active === 'true' && !b.active) return false;
      if (f.active === 'false' && b.active) return false;
      if (q && !matchQuery(binSearchBlob(b), q)) return false;
      return true;
    });
  }

  function applyFilters() {
    S.filteredMcc = filterMccs();
    S.filteredBin = filterBins();
    // Clamp pages
    var mccMax = Math.max(0, Math.ceil(S.filteredMcc.length / PAGE_SIZE) - 1);
    var binMax = Math.max(0, Math.ceil(S.filteredBin.length / PAGE_SIZE) - 1);
    if (S.mccPage > mccMax) S.mccPage = mccMax;
    if (S.binPage > binMax) S.binPage = binMax;
    renderMccTable();
    renderBinTable();
  }

  /* ── Render tables ── */
  function pageSlice(arr, page) {
    var start = page * PAGE_SIZE;
    return arr.slice(start, start + PAGE_SIZE);
  }

  function renderMccTable() {
    var tb = $('mccTableBody');
    var info = $('mccPageInfo');
    if (!tb) return;
    var rows = pageSlice(S.filteredMcc, S.mccPage);
    if (!rows.length) {
      tb.innerHTML = '<tr class="mcc-skeleton-row"><td colspan="6">Không có MCC khớp bộ lọc.</td></tr>';
    } else {
      tb.innerHTML = rows.map(function (m) {
        return (
          '<tr data-kind="mcc" data-id="' + esc(m.mcc) + '" tabindex="0">' +
          '<td><span class="mcc-code">' + esc(m.mcc) + '</span></td>' +
          '<td><strong>' + esc(m.nameVi || m.name) + '</strong><br><span class="mcc-muted" style="font-size:.78rem">' + esc(m.name) + '</span></td>' +
          '<td><span class="mcc-badge">' + esc(m.parentCategory || '—') + '</span></td>' +
          '<td>' + esc(m.industry || '—') + '</td>' +
          '<td>' + esc(m.cashbackCategory || 'General') + '</td>' +
          '<td><span class="' + badgeClass(m.verificationStatus) + '">' + esc(m.verificationStatus || 'Unknown') + '</span></td>' +
          '</tr>'
        );
      }).join('');
    }
    if (info) {
      var total = S.filteredMcc.length;
      var from = total ? S.mccPage * PAGE_SIZE + 1 : 0;
      var to = Math.min(total, (S.mccPage + 1) * PAGE_SIZE);
      info.textContent = from + '–' + to + ' / ' + total + ' MCC';
    }
    $('mccPrev') && ($('mccPrev').disabled = S.mccPage <= 0);
    $('mccNext') && ($('mccNext').disabled = (S.mccPage + 1) * PAGE_SIZE >= S.filteredMcc.length);
  }

  function renderBinTable() {
    var tb = $('binTableBody');
    var info = $('binPageInfo');
    if (!tb) return;
    var rows = pageSlice(S.filteredBin, S.binPage);
    if (!rows.length) {
      tb.innerHTML = '<tr class="mcc-skeleton-row"><td colspan="7">Không có BIN khớp bộ lọc.</td></tr>';
    } else {
      tb.innerHTML = rows.map(function (b) {
        return (
          '<tr data-kind="bin" data-id="' + esc(b.bin + '|' + b.bank) + '" tabindex="0">' +
          '<td><span class="mcc-code">' + esc(b.bin) + '</span></td>' +
          '<td><strong>' + esc(b.bank) + '</strong></td>' +
          '<td>' + esc(b.cardBrand || 'Unknown') + '</td>' +
          '<td>' + esc(b.cardType || 'Unknown') + '</td>' +
          '<td>' + esc(b.level || 'Unknown') + '</td>' +
          '<td><span class="mcc-badge ' + (b.active ? 'mcc-badge--ok' : 'mcc-badge--danger') + '">' + (b.active ? 'Active' : 'Inactive') + '</span></td>' +
          '<td><span class="' + badgeClass(b.verificationStatus) + '">' + esc(b.verificationStatus || 'Unknown') + '</span></td>' +
          '</tr>'
        );
      }).join('');
    }
    if (info) {
      var total = S.filteredBin.length;
      var from = total ? S.binPage * PAGE_SIZE + 1 : 0;
      var to = Math.min(total, (S.binPage + 1) * PAGE_SIZE);
      info.textContent = from + '–' + to + ' / ' + total + ' BIN';
    }
    $('binPrev') && ($('binPrev').disabled = S.binPage <= 0);
    $('binNext') && ($('binNext').disabled = (S.binPage + 1) * PAGE_SIZE >= S.filteredBin.length);
  }

  function renderKpis() {
    var m = S.meta || {};
    setText('kpiMcc', m.totalMcc != null ? m.totalMcc : S.mccs.length);
    setText('kpiBin', m.totalBin != null ? m.totalBin : S.bins.length);
    setText('kpiBanks', m.totalBanks != null ? m.totalBanks : uniqueSorted(S.bins.map(function (b) { return b.bank; })).length);
    setText('kpiSync', formatSync(m.lastSync || S.loadedAt));
    var failed = (m.failedSources && m.failedSources.length) || 0;
    setText('kpiFailed', failed);
    setText('kpiCoverage', failed ? 'Partial' : 'MCC + VN BIN');
  }
  function setText(id, v) {
    var el = $(id);
    if (el) el.textContent = v == null ? '—' : String(v);
  }
  function formatSync(iso) {
    if (!iso) return '—';
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso).slice(0, 16);
      return d.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour12: false });
    } catch (e) {
      return String(iso).slice(0, 16);
    }
  }

  /* ── Insights ── */
  function countBy(arr, keyFn) {
    var o = {};
    arr.forEach(function (x) {
      var k = keyFn(x) || 'Unknown';
      o[k] = (o[k] || 0) + 1;
    });
    return o;
  }
  function topN(obj, n) {
    return Object.keys(obj).map(function (k) { return { k: k, n: obj[k] }; })
      .sort(function (a, b) { return b.n - a.n; })
      .slice(0, n);
  }
  function mccsInCategory(cat) {
    return S.mccs.filter(function (m) {
      return m.cashbackCategory === cat || m.parentCategory === cat;
    });
  }
  function renderInsights() {
    var grid = $('mccInsightGrid');
    if (!grid) return;
    var dining = mccsInCategory('Dining');
    var coffeeish = S.mccs.filter(function (m) {
      return /coffee|cafe|fast food|5814|5812/i.test(mccSearchBlob(m));
    });
    var airline = S.mccs.filter(function (m) { return m.industry === 'Airlines' || m.parentCategory === 'Travel' && /airline|4511/i.test(mccSearchBlob(m)); });
    var hotel = S.mccs.filter(function (m) { return m.industry === 'Lodging / Hotels' || m.mcc === '7011'; });
    var grocery = mccsInCategory('Grocery');
    var gas = mccsInCategory('Gas');
    var hospital = S.mccs.filter(function (m) { return /8062|hospital|medical|8011|healthcare/i.test(mccSearchBlob(m)); });
    var ecom = S.mccs.filter(function (m) { return /596[0-9]|direct marketing|catalog|e-?commerce|online/i.test(mccSearchBlob(m)); });

    var binBrand = countBy(S.bins, function (b) { return b.cardBrand; });
    var binType = countBy(S.bins, function (b) { return b.cardType; });
    var binBank = countBy(S.bins, function (b) { return b.bank; });
    var topBanks = topN(binBank, 5);
    var largest = topBanks[0];

    var cards = [
      { icon: '🍜', title: 'Dining MCCs', body: dining.length + ' mã thuộc cashback/parent Dining. Phổ biến: 5812 (nhà hàng), 5814 (fast food), 5813 (bar).', meta: 'Nguồn: dataset local' },
      { icon: '☕', title: 'Coffee / F&B liên quan', body: coffeeish.length + ' mã khớp coffee/cafe/fast food/restaurant trong từ khóa & mô tả.', meta: 'Heuristic keyword' },
      { icon: '✈️', title: 'Airline MCCs', body: airline.length + ' mã industry Airlines hoặc travel-airline. Lưu ý: nhiều mã 3000–3299 là brand-specific.', meta: 'ISO range 3000–3299' },
      { icon: '🏨', title: 'Hotel MCCs', body: hotel.length + ' mã lodging/hotels + 7011. Range 3500–3999 thường là brand hotel.', meta: 'ISO range 3500–3999' },
      { icon: '🛒', title: 'Grocery MCCs', body: grocery.length + ' mã Grocery (vd 5411 siêu thị). Hữu ích khi map cashback “siêu thị”.', meta: cashbackSample(grocery) },
      { icon: '⛽', title: 'Gas station MCCs', body: gas.length + ' mã xăng dầu (5541/5542…).', meta: cashbackSample(gas) },
      { icon: '🏥', title: 'Hospital / Health MCCs', body: hospital.length + ' mã y tế/bệnh viện/bác sĩ khớp keyword hoặc Healthcare.', meta: 'Healthcare bucket' },
      { icon: '📦', title: 'E-commerce / Direct marketing', body: ecom.length + ' mã direct marketing / catalog (596x). MCC e-com thực tế phụ thuộc acquirer.', meta: 'Không gán brand nếu Unknown' },
      { icon: '🏦', title: 'BIN theo ngân hàng', body: topBanks.map(function (x) { return x.k + ': ' + x.n; }).join(' · ') || 'Chưa có BIN', meta: largest ? ('Largest issuer in set: ' + largest.k) : '—' },
      { icon: '💳', title: 'Visa vs Mastercard (BIN set)', body: Object.keys(binBrand).map(function (k) { return k + ': ' + binBrand[k]; }).join(' · ') || '—', meta: 'Vietnam curated only' },
      { icon: '↕️', title: 'Debit vs Credit', body: Object.keys(binType).map(function (k) { return k + ': ' + binType[k]; }).join(' · ') || '—', meta: 'Active+inactive' },
      { icon: '🆕', title: 'Latest sync', body: 'Last sync: ' + (S.meta.lastSync || 'Unknown') + '. Failed sources: ' + ((S.meta.failedSources && S.meta.failedSources.length) || 0) + '.', meta: 'scripts/sync_mcc_db.py' }
    ];

    grid.innerHTML = cards.map(function (c) {
      return (
        '<article class="mcc-insight">' +
        '<div class="mcc-insight__icon">' + c.icon + '</div>' +
        '<h3 class="mcc-insight__title">' + esc(c.title) + '</h3>' +
        '<p class="mcc-insight__body">' + esc(c.body) + '</p>' +
        '<div class="mcc-insight__meta">' + esc(c.meta) + '</div>' +
        '</article>'
      );
    }).join('');
  }
  function cashbackSample(list) {
    return list.slice(0, 4).map(function (m) { return m.mcc; }).join(', ') || '—';
  }

  function renderReport() {
    var el = $('mccReportBody');
    if (!el) return;
    var m = S.meta || {};
    var notes = (m.coverageNotes || []).map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('');
    var failed = (m.failedSources || []).map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('') || '<li>None</li>';
    var brands = m.binByBrand || countBy(S.bins, function (b) { return b.cardBrand; });
    var brandLi = Object.keys(brands).map(function (k) {
      return '<li>' + esc(k) + ': <strong>' + brands[k] + '</strong></li>';
    }).join('');
    var cb = m.mccByCashback || countBy(S.mccs, function (x) { return x.cashbackCategory; });
    var cbLi = topN(cb, 12).map(function (x) {
      return '<li>' + esc(x.k) + ': <strong>' + x.n + '</strong></li>';
    }).join('');

    el.innerHTML =
      '<h3>Tổng quan</h3>' +
      '<ul>' +
      '<li>Total MCC: <strong>' + esc(m.totalMcc != null ? m.totalMcc : S.mccs.length) + '</strong></li>' +
      '<li>Total BIN: <strong>' + esc(m.totalBin != null ? m.totalBin : S.bins.length) + '</strong></li>' +
      '<li>Total Banks: <strong>' + esc(m.totalBanks != null ? m.totalBanks : '—') + '</strong></li>' +
      '<li>Last Sync: <code>' + esc(m.lastSync || 'Unknown') + '</code></li>' +
      '<li>BIN scope: <strong>' + esc(m.binScope || 'Vietnam only') + '</strong></li>' +
      '</ul>' +
      '<h3>MCC source</h3><p>' + esc(m.mccSource || 'Unknown') + '</p>' +
      '<h3>Failed sources</h3><ul>' + failed + '</ul>' +
      '<h3>BIN by brand</h3><ul>' + (brandLi || '<li>Unknown</li>') + '</ul>' +
      '<h3>MCC by cashback category (top)</h3><ul>' + (cbLi || '<li>Unknown</li>') + '</ul>' +
      '<h3>Coverage notes</h3><ul>' + (notes || '<li>Unknown</li>') + '</ul>' +
      '<h3>Missing / gaps</h3>' +
      '<ul>' +
      '<li>BIN list is curated, not a full national registry — many international product BINs remain Unknown until verified.</li>' +
      '<li>Card level (Gold/Platinum/Infinite…) is Unknown unless documented publicly.</li>' +
      '<li>Vietnamese MCC names only curated for high-frequency codes; others display English source description.</li>' +
      '</ul>';
  }

  /* ── Drawer ── */
  function openDrawer(html) {
    var body = $('mccDrawerBody');
    var drawer = $('mccDrawer');
    if (!body || !drawer) return;
    body.innerHTML = html;
    drawer.hidden = false;
    document.body.style.overflow = 'hidden';
  }
  function closeDrawer() {
    var drawer = $('mccDrawer');
    if (drawer) drawer.hidden = true;
    document.body.style.overflow = '';
  }
  function findMcc(code) {
    return S.mccs.find(function (m) { return m.mcc === code; });
  }
  function findBin(id) {
    var parts = String(id).split('|');
    var bin = parts[0];
    var bank = parts.slice(1).join('|');
    return S.bins.find(function (b) { return b.bin === bin && b.bank === bank; })
      || S.bins.find(function (b) { return b.bin === bin; });
  }
  function showMccDetail(code) {
    var m = findMcc(code);
    if (!m) return;
    var merchants = (m.typicalMerchants || []).map(function (x) {
      return '<span class="mcc-badge">' + esc(x) + '</span>';
    }).join('') || '<span class="mcc-badge mcc-badge--muted">Unknown</span>';
    var related = (m.relatedMccs || []).map(function (c) {
      return '<button type="button" class="mcc-badge" data-related-mcc="' + esc(c) + '">' + esc(c) + '</button>';
    }).join('') || '<span class="mcc-badge mcc-badge--muted">—</span>';

    openDrawer(
      '<p class="mcc-drawer__kicker">Merchant Category Code</p>' +
      '<h2 class="mcc-drawer__title" id="mccDrawerTitle">' + esc(m.mcc) + ' · ' + esc(m.nameVi || m.name) + '</h2>' +
      '<p class="mcc-muted">' + esc(m.name) + '</p>' +
      '<dl class="mcc-drawer__dl">' +
      row('MCC', m.mcc) +
      row('Vietnamese', m.nameViExact && m.nameViExact !== 'Unknown' ? m.nameViExact : (m.nameVi || 'Unknown')) +
      row('Industry', m.industry) +
      row('Parent', m.parentCategory) +
      row('Description', m.description) +
      row('Cashback', (m.cashbackCategory || 'General') + (m.cashbackCategoryVi ? ' · ' + m.cashbackCategoryVi : '')) +
      row('Visa map', m.visaCategory || 'Unknown') +
      row('Mastercard map', m.mastercardCategory || 'Unknown') +
      row('Scope', m.scope || 'Unknown') +
      row('Status', m.verificationStatus || 'Unknown') +
      row('Last verified', m.lastVerified || 'Unknown') +
      row('Source', m.source || 'Unknown') +
      '</dl>' +
      '<h3 class="mcc-section-title" style="font-size:.95rem">Typical merchants</h3>' +
      '<div class="mcc-drawer__chips">' + merchants + '</div>' +
      '<h3 class="mcc-section-title" style="font-size:.95rem;margin-top:1rem">Related MCCs</h3>' +
      '<div class="mcc-drawer__chips">' + related + '</div>' +
      (m.notes ? '<div class="mcc-drawer__notes">' + esc(m.notes) + '</div>' : '') +
      (m.sourceUrl ? '<a class="mcc-drawer__link" href="' + esc(m.sourceUrl) + '" target="_blank" rel="noopener">Open source ↗</a>' : '')
    );
  }
  function showBinDetail(id) {
    var b = findBin(id);
    if (!b) return;
    openDrawer(
      '<p class="mcc-drawer__kicker">Vietnam BIN / IIN</p>' +
      '<h2 class="mcc-drawer__title" id="mccDrawerTitle">' + esc(b.bin) + ' · ' + esc(b.bank) + '</h2>' +
      '<dl class="mcc-drawer__dl">' +
      row('BIN', b.bin + ' (' + (b.binLength || b.bin.length) + ' digits)') +
      row('Bank', b.bank) +
      row('Bank code', b.bankCode || 'Unknown') +
      row('Brand', b.cardBrand || 'Unknown') +
      row('Network', b.network || 'Unknown') +
      row('Card type', b.cardType || 'Unknown') +
      row('Product', b.product || 'Unknown') +
      row('Level', b.level || 'Unknown') +
      row('Consumer/Business', b.consumerBusiness || 'Unknown') +
      row('Country', b.issuerCountry || 'VN') +
      row('Currency', b.currency || 'VND') +
      row('Active', b.active ? 'Yes' : 'No') +
      row('Cashback fit', b.cashbackCompatibility || 'Unknown') +
      row('Typical promos', b.typicalPromotions || 'Unknown') +
      row('Status', b.verificationStatus || 'Unknown') +
      row('Last verified', b.lastVerified || 'Unknown') +
      row('Source', b.source || 'Unknown') +
      '</dl>' +
      (b.notes ? '<div class="mcc-drawer__notes">' + esc(b.notes) + '</div>' : '') +
      (b.sourceUrl ? '<a class="mcc-drawer__link" href="' + esc(b.sourceUrl) + '" target="_blank" rel="noopener">Open bank / source ↗</a>' : '')
    );
  }
  function row(label, value) {
    return '<dt>' + esc(label) + '</dt><dd>' + esc(value == null || value === '' ? 'Unknown' : value) + '</dd>';
  }

  /* ── Tabs ── */
  function setTab(name) {
    S.tab = name;
    document.querySelectorAll('.mcc-tabs__btn').forEach(function (btn) {
      var onn = btn.getAttribute('data-tab') === name;
      btn.classList.toggle('is-active', onn);
      btn.setAttribute('aria-selected', onn ? 'true' : 'false');
    });
    document.querySelectorAll('.mcc-panel').forEach(function (p) {
      var onn = p.getAttribute('data-panel') === name;
      p.classList.toggle('is-active', onn);
      p.hidden = !onn;
    });
  }

  /* ── Export ── */
  function exportRows() {
    if (S.tab === 'bin') {
      return {
        sheet: 'BIN',
        rows: S.filteredBin.map(function (b) {
          return {
            BIN: b.bin,
            Bank: b.bank,
            Brand: b.cardBrand,
            Network: b.network,
            Type: b.cardType,
            Product: b.product,
            Level: b.level,
            Active: b.active ? 'Yes' : 'No',
            Status: b.verificationStatus,
            Source: b.source,
            LastVerified: b.lastVerified
          };
        })
      };
    }
    return {
      sheet: 'MCC',
      rows: S.filteredMcc.map(function (m) {
        return {
          MCC: m.mcc,
          Name: m.name,
          NameVi: m.nameVi,
          Category: m.parentCategory,
          Industry: m.industry,
          Cashback: m.cashbackCategory,
          Status: m.verificationStatus,
          Source: m.source,
          LastVerified: m.lastVerified
        };
      })
    };
  }

  function exportCsv() {
    var pack = exportRows();
    if (!pack.rows.length) { setStatus('Không có dòng để export', true); return; }
    var keys = Object.keys(pack.rows[0]);
    var lines = [keys.join(',')];
    pack.rows.forEach(function (r) {
      lines.push(keys.map(function (k) {
        var v = r[k] == null ? '' : String(r[k]);
        if (/[",\n]/.test(v)) v = '"' + v.replace(/"/g, '""') + '"';
        return v;
      }).join(','));
    });
    downloadBlob(new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' }), 'mcc-db-' + pack.sheet.toLowerCase() + '.csv');
    setStatus('Exported CSV · ' + pack.rows.length + ' rows');
  }

  function exportExcel() {
    if (typeof XLSX === 'undefined') { setStatus('SheetJS chưa load', true); return; }
    var pack = exportRows();
    if (!pack.rows.length) { setStatus('Không có dòng để export', true); return; }
    var ws = XLSX.utils.json_to_sheet(pack.rows);
    var wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, pack.sheet);
    XLSX.writeFile(wb, 'mcc-db-' + pack.sheet.toLowerCase() + '.xlsx');
    setStatus('Exported Excel · ' + pack.rows.length + ' rows');
  }

  function exportPdf() {
    var JSPDF = window.jspdf && window.jspdf.jsPDF;
    if (!JSPDF) { setStatus('jsPDF chưa load', true); return; }
    var pack = exportRows();
    if (!pack.rows.length) { setStatus('Không có dòng để export', true); return; }
    var doc = new JSPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' });
    doc.setFontSize(14);
    doc.text('MCC DB — ' + pack.sheet + ' export', 40, 40);
    doc.setFontSize(9);
    doc.text('Generated: ' + new Date().toISOString() + ' · rows: ' + pack.rows.length + ' (first 80 shown)', 40, 56);
    var y = 78;
    var sample = pack.rows.slice(0, 80);
    var keys = Object.keys(sample[0]).slice(0, 8);
    sample.forEach(function (r, i) {
      if (y > 540) { doc.addPage(); y = 40; }
      var line = keys.map(function (k) { return String(r[k] == null ? '' : r[k]).slice(0, 28); }).join(' | ');
      doc.text((i + 1) + '. ' + line, 40, y);
      y += 12;
    });
    doc.save('mcc-db-' + pack.sheet.toLowerCase() + '.pdf');
    setStatus('Exported PDF · preview first 80 of ' + pack.rows.length);
  }

  function downloadBlob(blob, name) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () {
      URL.revokeObjectURL(a.href);
      a.remove();
    }, 500);
  }

  /* ── Version badge ── */
  function loadVersion() {
    var el = $('mccVersionBadge');
    if (!el) return;
    fetch(baseURL() + 'build-info.json?_=' + Date.now(), { cache: 'no-cache' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (info) {
        if (!info) {
          el.textContent = 'Phiên bản dịch vụ: local / unknown';
          return;
        }
        var sha = info.commit || info.sha || info.github_sha || info.version || 'unknown';
        if (typeof sha === 'string' && sha.length > 7) sha = sha.slice(0, 7);
        el.textContent = 'Phiên bản dịch vụ: ' + sha + (info.built_at ? ' · ' + info.built_at : '');
      })
      .catch(function () {
        el.textContent = 'Phiên bản dịch vụ: unknown';
      });
  }

  /* ── Wire ── */
  function wire() {
    document.querySelectorAll('.mcc-tabs__btn').forEach(function (btn) {
      on(btn, 'click', function () { setTab(btn.getAttribute('data-tab')); });
    });

    var search = $('mccGlobalSearch');
    var searchTimer = null;
    on(search, 'input', function () {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(function () {
        S.q = search.value || '';
        S.mccPage = 0;
        S.binPage = 0;
        applyFilters();
      }, 180);
    });

    on($('fMccIndustry'), 'change', function (e) { S.mccFilters.industry = e.target.value; S.mccPage = 0; applyFilters(); });
    on($('fMccParent'), 'change', function (e) { S.mccFilters.parent = e.target.value; S.mccPage = 0; applyFilters(); });
    on($('fMccCashback'), 'change', function (e) { S.mccFilters.cashback = e.target.value; S.mccPage = 0; applyFilters(); });
    on($('fMccStatus'), 'change', function (e) { S.mccFilters.status = e.target.value; S.mccPage = 0; applyFilters(); });
    on($('mccClearFilters'), 'click', function () {
      S.mccFilters = { industry: '', parent: '', cashback: '', status: '' };
      ['fMccIndustry', 'fMccParent', 'fMccCashback', 'fMccStatus'].forEach(function (id) { if ($(id)) $(id).value = ''; });
      S.mccPage = 0;
      applyFilters();
    });

    on($('fBinBank'), 'change', function (e) { S.binFilters.bank = e.target.value; S.binPage = 0; applyFilters(); });
    on($('fBinBrand'), 'change', function (e) { S.binFilters.brand = e.target.value; S.binPage = 0; applyFilters(); });
    on($('fBinType'), 'change', function (e) { S.binFilters.type = e.target.value; S.binPage = 0; applyFilters(); });
    on($('fBinActive'), 'change', function (e) { S.binFilters.active = e.target.value; S.binPage = 0; applyFilters(); });
    on($('binClearFilters'), 'click', function () {
      S.binFilters = { bank: '', brand: '', type: '', active: '' };
      ['fBinBank', 'fBinBrand', 'fBinType', 'fBinActive'].forEach(function (id) { if ($(id)) $(id).value = ''; });
      S.binPage = 0;
      applyFilters();
    });

    on($('mccPrev'), 'click', function () { if (S.mccPage > 0) { S.mccPage--; renderMccTable(); } });
    on($('mccNext'), 'click', function () { if ((S.mccPage + 1) * PAGE_SIZE < S.filteredMcc.length) { S.mccPage++; renderMccTable(); } });
    on($('binPrev'), 'click', function () { if (S.binPage > 0) { S.binPage--; renderBinTable(); } });
    on($('binNext'), 'click', function () { if ((S.binPage + 1) * PAGE_SIZE < S.filteredBin.length) { S.binPage++; renderBinTable(); } });

    on($('mccTableBody'), 'click', function (e) {
      var tr = e.target.closest('tr[data-kind="mcc"]');
      if (tr) showMccDetail(tr.getAttribute('data-id'));
    });
    on($('mccTableBody'), 'keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      var tr = e.target.closest('tr[data-kind="mcc"]');
      if (tr) { e.preventDefault(); showMccDetail(tr.getAttribute('data-id')); }
    });
    on($('binTableBody'), 'click', function (e) {
      var tr = e.target.closest('tr[data-kind="bin"]');
      if (tr) showBinDetail(tr.getAttribute('data-id'));
    });
    on($('binTableBody'), 'keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      var tr = e.target.closest('tr[data-kind="bin"]');
      if (tr) { e.preventDefault(); showBinDetail(tr.getAttribute('data-id')); }
    });

    on($('mccDrawerBody'), 'click', function (e) {
      var rel = e.target.getAttribute('data-related-mcc');
      if (rel) showMccDetail(rel);
    });
    on($('mccDrawerClose'), 'click', closeDrawer);
    on($('mccDrawerBackdrop'), 'click', closeDrawer);
    on(document, 'keydown', function (e) { if (e.key === 'Escape') closeDrawer(); });

    on($('mccSyncMcc'), 'click', function () { loadData(); });
    on($('mccSyncBin'), 'click', function () { loadData(); });
    on($('mccSyncAll'), 'click', function () { loadData(); });

    on($('mccExportCsv'), 'click', exportCsv);
    on($('mccExportExcel'), 'click', exportExcel);
    on($('mccExportPdf'), 'click', exportPdf);
  }

  function init() {
    wire();
    loadVersion();
    loadData();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
