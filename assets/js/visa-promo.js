/**
 * Visa Promo Center
 * Auth: SHA-256 PIN (same as Movie Calendar / Credit Card = 0512)
 * Persistence: GitHub Contents API via personal token (localStorage) — NO Cloudflare R2
 */
(function () {
  'use strict';

  var ACCESS_HASH = '78c72f67941a420cd4e5ee9fdabcaeaba6d72f16160915085f9802220fd83799';
  var SESSION_KEY = 'vp_unlocked';
  var TOKEN_KEY = 'vp_gh_token';
  var GH_OWNER = 'banhang-chogao';
  var GH_REPO = 'reviewchanthat';
  var GH_PATH = 'data/visa-promo.json';
  var GH_BRANCH = 'main';
  var CACHE_KEY = 'vp_local_cache_v1';

  var HEADERS = [
    'PromotionID', 'Bank', 'Card', 'CardLevel', 'Merchant', 'MerchantCategory', 'PromotionType',
    'OfferTitle', 'ShortDescription', 'DiscountType', 'DiscountValue', 'CashbackCap', 'MinimumSpend',
    'InstallmentMonths', 'EligibleCards', 'Country', 'City', 'StartDate', 'EndDate', 'PromoCode',
    'ApplyURL', 'OfficialSource', 'Terms', 'Priority', 'Featured', 'Status', 'Logo', 'Banner', 'UpdatedAt'
  ];

  var OFFICIAL_HOSTS = [
    'visa.com', 'visa.com.vn', 'hsbc.com.vn', 'hsbc.com', 'vietcombank.com.vn', 'techcombank.com.vn',
    'vpbank.com.vn', 'tpb.vn', 'mbbank.com.vn', 'sacombank.com.vn', 'bidv.com.vn', 'acb.com.vn'
  ];

  var CHART_COLORS = [
    'rgba(0,167,160,0.8)', 'rgba(26,35,126,0.8)', 'rgba(59,130,246,0.75)',
    'rgba(245,158,11,0.8)', 'rgba(239,68,68,0.75)', 'rgba(124,77,255,0.75)',
    'rgba(16,185,129,0.75)', 'rgba(255,138,0,0.75)'
  ];

  var S = {
    promotions: [],
    auditLog: [],
    lastSyncAt: null,
    filtered: [],
    charts: {},
    filters: {
      q: '', bank: '', merchant: '', category: '', country: '', card: '',
      cardLevel: '', type: '', status: '', from: '', to: ''
    },
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
    return 'vp_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }
  function sha256(str) {
    return crypto.subtle.digest('SHA-256', new TextEncoder().encode(str)).then(function (buf) {
      var hex = '', b = new Uint8Array(buf);
      for (var i = 0; i < b.length; i++) hex += b[i].toString(16).padStart(2, '0');
      return hex;
    });
  }
  function todayISO() {
    var d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function isValidDate(s) {
    if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
    var p = s.split('-').map(Number);
    var d = new Date(p[0], p[1] - 1, p[2]);
    return d.getFullYear() === p[0] && d.getMonth() === p[1] - 1 && d.getDate() === p[2];
  }
  function daysUntil(iso) {
    if (!isValidDate(iso)) return null;
    var t = new Date(); t.setHours(0, 0, 0, 0);
    var d = new Date(iso + 'T00:00:00');
    return Math.round((d - t) / 86400000);
  }
  function parseMoney(v) {
    if (typeof v === 'number') return isNaN(v) ? 0 : v;
    if (v == null || v === '') return 0;
    var s = String(v).replace(/[^\d\-.,]/g, '');
    if ((s.match(/\./g) || []).length > 1) s = s.replace(/\./g, '');
    s = s.replace(',', '.');
    var n = parseFloat(s);
    return isNaN(n) ? 0 : n;
  }
  function yesNo(v) {
    if (v === true || v === 1) return true;
    var s = String(v == null ? '' : v).trim().toLowerCase();
    return s === 'yes' || s === 'y' || s === 'true' || s === '1';
  }
  function isHttpsOfficial(url) {
    if (!url) return true;
    try {
      var u = new URL(String(url).trim());
      if (u.protocol !== 'https:') return false;
      if (/example\.com|localhost|dummy|placeholder/i.test(u.hostname)) return false;
      var host = u.hostname.toLowerCase();
      return OFFICIAL_HOSTS.some(function (suf) {
        return host === suf || host.slice(-(suf.length + 1)) === '.' + suf;
      });
    } catch (e) { return false; }
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
      promotions: S.promotions,
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
      S.promotions = [];
      S.auditLog = [];
      return;
    }
    S.promotions = Array.isArray(d.promotions) ? d.promotions.map(normalizePromo) : [];
    S.auditLog = Array.isArray(d.auditLog) ? d.auditLog : [];
    S.lastSyncAt = d.lastSyncAt || null;
    S.promotions.forEach(function (p) {
      if (isExpired(p) && p.Status === 'Active') p.Status = 'Expired';
    });
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
    var el = $('vpSyncLabel');
    if (el) el.textContent = text;
  }
  function setProgress(show, pct, text, sha, isErr) {
    var pb = $('vpProgress'), pf = $('vpProgressFill'), pt = $('vpProgressText'), ps = $('vpProgressSha');
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
    var el = $('vpIoStatus');
    if (!el) return;
    el.hidden = false;
    el.className = 'vp-status vp-status--' + (kind === 'ok' ? 'ok' : kind === 'warn' ? 'warn' : 'err');
    el.textContent = msg;
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
        setProgress(true, 55, '📤 Committing ' + S.promotions.length + ' promotions…');
        var body = {
          message: 'visa-promo: save ' + S.promotions.length + ' promotions',
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
        cacheLocal();
        setProgress(true, 100, '✅ Saved to GitHub', short ? 'Commit: ' + short : '');
        setSync('GitHub · ' + (short || nowLabel()));
        audit('save', 'GitHub commit ' + short + ' · ' + S.promotions.length + ' promos');
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

  function nowLabel() {
    return new Date().toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' });
  }
  function promptToken() {
    var t = prompt('GitHub Personal Access Token (contents:write) — lưu trên trình duyệt, không hardcode:', getToken() || '');
    if (t !== null) {
      setToken(String(t).trim());
      if (t.trim()) alert('Token đã lưu local.');
    }
  }

  function emptyPromo() {
    var t = todayISO();
    return {
      id: gId(),
      PromotionID: '',
      Bank: 'HSBC',
      Card: '',
      CardLevel: '',
      Merchant: '',
      MerchantCategory: 'Dining',
      PromotionType: 'Cashback',
      OfferTitle: '',
      ShortDescription: '',
      DiscountType: 'Percent',
      DiscountValue: 0,
      CashbackCap: 0,
      MinimumSpend: 0,
      InstallmentMonths: 0,
      EligibleCards: '',
      Country: 'Vietnam',
      City: '',
      StartDate: t,
      EndDate: t,
      PromoCode: '',
      ApplyURL: '',
      OfficialSource: '',
      Terms: '',
      Priority: 50,
      Featured: false,
      Status: 'Pending',
      Logo: '',
      Banner: '',
      UpdatedAt: new Date().toISOString(),
      Verified: 'Pending',
      LastVerified: '',
      VerifiedBy: '',
      SourceURL: ''
    };
  }

  function normalizePromo(p) {
    var base = emptyPromo();
    Object.keys(base).forEach(function (k) {
      if (p[k] !== undefined && p[k] !== null) base[k] = p[k];
    });
    // accept snake/camel aliases
    if (p.promotionId && !p.PromotionID) base.PromotionID = p.promotionId;
    if (p.offerTitle && !p.OfferTitle) base.OfferTitle = p.offerTitle;
    base.Featured = !!base.Featured || yesNo(base.Featured);
    base.DiscountValue = Number(base.DiscountValue) || 0;
    base.CashbackCap = parseMoney(base.CashbackCap);
    base.MinimumSpend = parseMoney(base.MinimumSpend);
    base.InstallmentMonths = parseInt(base.InstallmentMonths, 10) || 0;
    base.Priority = parseInt(base.Priority, 10) || 0;
    if (!base.PromotionID) base.PromotionID = base.id || gId();
    if (!base.id) base.id = gId();
    if (!base.Verified) base.Verified = base.Status === 'Verified' ? 'Verified' : 'Pending';
    if (isExpired(base) && base.Status !== 'Draft') base.Status = 'Expired';
    return base;
  }

  function isExpired(p) {
    if (!p) return true;
    if (p.Status === 'Expired') return true;
    if (p.EndDate && isValidDate(p.EndDate) && p.EndDate < todayISO()) return true;
    return false;
  }
  function isActive(p) {
    if (!p || isExpired(p)) return false;
    if (p.Status === 'Draft' || p.Status === 'Expired') return false;
    if (p.StartDate && isValidDate(p.StartDate) && p.StartDate > todayISO()) return false;
    return true;
  }

  function validatePromo(p, opts) {
    opts = opts || {};
    var err = [];
    if (!p.Bank) err.push('Bank required');
    if (!p.Merchant) err.push('Merchant required');
    if (!p.OfferTitle) err.push('OfferTitle required');
    if (!isValidDate(p.StartDate)) err.push('StartDate invalid');
    if (!isValidDate(p.EndDate)) err.push('EndDate invalid');
    if (p.StartDate && p.EndDate && p.EndDate < p.StartDate) err.push('EndDate < StartDate');
    if (p.DiscountValue < 0) err.push('DiscountValue invalid');
    if (p.ApplyURL && !isHttpsOfficial(p.ApplyURL)) err.push('ApplyURL must be HTTPS official domain');
    if (p.SourceURL && !isHttpsOfficial(p.SourceURL)) err.push('SourceURL invalid');
    if (opts.checkDup) {
      var id = String(p.PromotionID || '').toLowerCase();
      var dup = S.promotions.some(function (x) {
        if (opts.ignoreId && x.id === opts.ignoreId) return false;
        return String(x.PromotionID || '').toLowerCase() === id;
      });
      if (dup) err.push('Duplicate PromotionID');
    }
    return err;
  }

  /* ── Auth ── */
  function showApp() {
    var g = $('vpGate'), a = $('vpApp');
    if (g) g.style.display = 'none';
    if (a) { a.hidden = false; a.style.display = ''; }
  }
  function hideApp() {
    var g = $('vpGate'), a = $('vpApp');
    if (a) { a.hidden = true; a.style.display = 'none'; }
    if (g) g.style.display = '';
  }
  function afterUnlock() {
    showApp();
    loadFromGitHub()
      .then(function (ok) {
        if (!ok) loadLocalCache();
        setSync(ok ? 'GitHub · loaded' : (S.promotions.length ? 'Local cache' : 'Empty'));
        renderAll();
      })
      ['catch'](function () {
        loadLocalCache();
        setSync('Offline / local');
        renderAll();
      });
  }
  function initGate() {
    if (sessionStorage.getItem(SESSION_KEY) === '1') {
      afterUnlock();
      return;
    }
    var input = $('vpGateInput'), btn = $('vpGateUnlock'), err = $('vpGateError');
    var attempts = 0, last = 0;
    function unlock() {
      var code = (input.value || '').trim();
      if (!code || code.length !== 4) { err.textContent = 'Enter 4 digits.'; return; }
      var n = Date.now();
      if (n - last < 1500) { err.textContent = 'Too fast.'; return; }
      last = n;
      attempts++;
      if (attempts > 5) { err.textContent = 'Too many attempts.'; btn.disabled = true; return; }
      sha256(code).then(function (h) {
        if (h === ACCESS_HASH) {
          sessionStorage.setItem(SESSION_KEY, '1');
          afterUnlock();
        } else {
          err.textContent = 'Wrong code. ' + (5 - attempts) + ' left.';
          input.value = '';
          input.focus();
        }
      });
    }
    on(btn, 'click', unlock);
    on(input, 'keydown', function (e) { if (e.key === 'Enter') unlock(); });
    if (input) input.focus();
  }

  /* ── Filters & metrics ── */
  function applyFilters() {
    var f = S.filters;
    var q = (f.q || '').toLowerCase();
    S.filtered = S.promotions.filter(function (p) {
      if (f.bank && p.Bank !== f.bank) return false;
      if (f.merchant && p.Merchant !== f.merchant) return false;
      if (f.category && p.MerchantCategory !== f.category) return false;
      if (f.country && p.Country !== f.country) return false;
      if (f.card && String(p.Card || '').indexOf(f.card) === -1 && String(p.EligibleCards || '').indexOf(f.card) === -1) return false;
      if (f.cardLevel && p.CardLevel !== f.cardLevel) return false;
      if (f.type && p.PromotionType !== f.type) return false;
      if (f.status === 'Featured' && !p.Featured) return false;
      else if (f.status === 'Verified' && p.Verified !== 'Verified') return false;
      else if (f.status === 'Pending' && p.Verified !== 'Pending' && p.Status !== 'Pending') return false;
      else if (f.status === 'Expired' && !isExpired(p)) return false;
      else if (f.status === 'Active' && !isActive(p)) return false;
      if (f.from && p.EndDate && p.EndDate < f.from) return false;
      if (f.to && p.StartDate && p.StartDate > f.to) return false;
      if (!q) return true;
      return [p.Merchant, p.Bank, p.OfferTitle, p.PromoCode, p.ShortDescription, p.PromotionID]
        .join(' ').toLowerCase().indexOf(q) !== -1;
    }).sort(function (a, b) {
      var fa = a.Featured ? 1 : 0, fb = b.Featured ? 1 : 0;
      if (fb !== fa) return fb - fa;
      if ((b.Priority || 0) !== (a.Priority || 0)) return (b.Priority || 0) - (a.Priority || 0);
      return String(a.EndDate || '').localeCompare(String(b.EndDate || ''));
    });
  }

  function computeKpis(list) {
    list = list || S.promotions;
    var today = todayISO();
    var endWeek = new Date(); endWeek.setDate(endWeek.getDate() + 7);
    var endWeekISO = endWeek.toISOString().slice(0, 10);
    var k = {
      active: 0, featured: 0, endToday: 0, endWeek: 0, expired: 0,
      dining: 0, travel: 0, shopping: 0, entertainment: 0, installment: 0, cashback: 0,
      maxDisc: 0, sumDisc: 0, nDisc: 0
    };
    list.forEach(function (p) {
      if (isActive(p)) k.active++;
      if (p.Featured) k.featured++;
      if (isExpired(p)) k.expired++;
      if (p.EndDate === today) k.endToday++;
      if (p.EndDate && p.EndDate >= today && p.EndDate <= endWeekISO) k.endWeek++;
      var cat = p.MerchantCategory || '';
      if (cat === 'Dining' || cat === 'Coffee') k.dining++;
      if (cat === 'Travel' || cat === 'Hotel') k.travel++;
      if (cat === 'Shopping' || cat === 'Electronics') k.shopping++;
      if (cat === 'Entertainment') k.entertainment++;
      if (p.PromotionType === 'Installment' || (p.InstallmentMonths || 0) > 0) k.installment++;
      if (p.PromotionType === 'Cashback') k.cashback++;
      if (p.DiscountType === 'Percent' && p.DiscountValue > 0) {
        k.maxDisc = Math.max(k.maxDisc, p.DiscountValue);
        k.sumDisc += p.DiscountValue;
        k.nDisc++;
      }
    });
    k.avgDisc = k.nDisc ? (k.sumDisc / k.nDisc) : 0;
    return k;
  }

  function renderKpis() {
    var host = $('vpKpis');
    if (!host) return;
    var k = computeKpis(S.promotions);
    var items = [
      ['Active', k.active], ['Featured', k.featured], ['Ending Today', k.endToday],
      ['Ending This Week', k.endWeek], ['Expired', k.expired], ['Dining', k.dining],
      ['Travel', k.travel], ['Shopping', k.shopping], ['Entertainment', k.entertainment],
      ['Installment', k.installment], ['Cashback', k.cashback],
      ['Highest Discount', k.maxDisc ? k.maxDisc + '%' : '—'],
      ['Average Discount', k.avgDisc ? k.avgDisc.toFixed(1) + '%' : '—']
    ];
    host.innerHTML = items.map(function (it) {
      return '<div class="vp-kpi"><span class="vp-kpi__label">' + esc(it[0]) + '</span><span class="vp-kpi__value">' + esc(String(it[1])) + '</span></div>';
    }).join('');
  }

  function formatDeal(p) {
    if (p.DiscountType === 'Percent') return (p.DiscountValue || 0) + '%';
    if (p.DiscountType === 'Fixed') return (p.DiscountValue || 0).toLocaleString('vi-VN') + '₫';
    return String(p.DiscountValue || '—');
  }

  function renderCards() {
    applyFilters();
    var host = $('vpCards');
    var empty = $('vpCardsEmpty');
    if (!host) return;
    host.innerHTML = '';
    if (empty) empty.hidden = S.filtered.length > 0;
    S.filtered.forEach(function (p) {
      var d = daysUntil(p.EndDate);
      var countdown = d === null ? '' : (d < 0 ? 'Expired' : d === 0 ? 'Ends today' : 'D-' + d);
      var logo = p.Logo
        ? '<img src="' + esc(p.Logo) + '" alt="">'
        : esc((p.Merchant || 'V').slice(0, 2).toUpperCase());
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'vp-card';
      btn.innerHTML =
        '<div class="vp-card__top"><div class="vp-card__logo">' + logo + '</div><div>' +
        '<div class="vp-card__merchant">' + esc(p.Merchant || '—') + '</div>' +
        '<div class="vp-card__discount">' + esc(formatDeal(p)) + '</div></div></div>' +
        '<h3 class="vp-card__title">' + esc(p.OfferTitle || 'Untitled') + '</h3>' +
        '<div class="vp-card__meta">' + esc(p.Bank || '') + (p.Card ? ' · ' + esc(p.Card) : '') +
        (countdown ? ' · ' + esc(countdown) : '') + '</div>' +
        '<div class="vp-card__row">' +
        (p.Featured ? '<span class="vp-badge vp-badge--featured">Featured</span>' : '') +
        '<span class="vp-badge vp-badge--' + (p.Verified === 'Verified' ? 'verified' : 'pending') + '">' + esc(p.Verified || 'Pending') + '</span>' +
        '<span class="vp-badge vp-badge--' + (isExpired(p) ? 'expired' : 'active') + '">' + esc(isExpired(p) ? 'Expired' : (p.Status || 'Active')) + '</span>' +
        '<span class="vp-badge vp-badge--type">' + esc(p.PromotionType || '') + '</span>' +
        '</div>';
      btn.addEventListener('click', function () { openDrawer(p); });
      host.appendChild(btn);
    });
  }

  function openDrawer(p) {
    var drawer = $('vpDrawer');
    if (!drawer) return;
    drawer.hidden = false;
    var ban = $('vpDrawerBanner');
    if (ban) {
      ban.style.background = p.Banner
        ? 'center/cover url(' + JSON.stringify(p.Banner) + '), linear-gradient(135deg,#0f3460,#00a7a0)'
        : '';
      ban.textContent = p.Merchant || 'Visa Offer';
    }
    $('vpDrawerTitle').textContent = p.OfferTitle || '';
    $('vpDrawerDesc').textContent = p.ShortDescription || '';
    $('vpDrawerTerms').textContent = p.Terms || '';
    var d = daysUntil(p.EndDate);
    var cd = $('vpDrawerCountdown');
    if (cd) cd.textContent = d === null ? '' : (d < 0 ? 'Expired' : d === 0 ? '🔥 Ends today' : 'Còn ' + d + ' ngày');
    var badges = $('vpDrawerBadges');
    if (badges) {
      badges.innerHTML =
        (p.Featured ? '<span class="vp-badge vp-badge--featured">Featured</span> ' : '') +
        '<span class="vp-badge vp-badge--' + (p.Verified === 'Verified' ? 'verified' : 'pending') + '">' + esc(p.Verified || 'Pending') + '</span> ' +
        '<span class="vp-badge vp-badge--type">' + esc(p.PromotionType || '') + '</span>';
    }
    var meta = $('vpDrawerMeta');
    if (meta) {
      var rows = [
        ['Merchant', p.Merchant], ['Bank / Card', [p.Bank, p.Card].filter(Boolean).join(' · ')],
        ['Eligible Cards', p.EligibleCards || p.Card || '—'],
        ['Promo Code', p.PromoCode || '—'], ['Min Spend', p.MinimumSpend || '—'],
        ['Cashback Cap', p.CashbackCap || '—'], ['Installment', (p.InstallmentMonths || 0) + ' months'],
        ['Valid', (p.StartDate || '') + ' → ' + (p.EndDate || '')],
        ['Last Verified', p.LastVerified || '—'], ['Verified By', p.VerifiedBy || '—'],
        ['Official Source', p.OfficialSource || '—'], ['Discount', formatDeal(p)]
      ];
      meta.innerHTML = rows.map(function (r) {
        return '<div><span>' + esc(r[0]) + '</span><strong>' + esc(String(r[1])) + '</strong></div>';
      }).join('');
    }
    var link = $('vpDrawerLink');
    if (link) {
      if (p.ApplyURL && isHttpsOfficial(p.ApplyURL)) {
        link.href = p.ApplyURL;
        link.style.display = '';
        link.textContent = 'Open official link';
      } else {
        link.removeAttribute('href');
        link.style.display = 'none';
      }
    }
  }
  function closeDrawer() {
    var d = $('vpDrawer');
    if (d) d.hidden = true;
  }

  function fillFilterSelects() {
    function fill(id, values, label) {
      var sel = $(id);
      if (!sel) return;
      var cur = sel.value;
      var html = '<option value="">' + label + '</option>';
      values.forEach(function (v) { if (v) html += '<option value="' + esc(v) + '">' + esc(v) + '</option>'; });
      sel.innerHTML = html;
      if (cur) sel.value = cur;
    }
    var banks = {}, merchants = {}, cats = {}, countries = {}, cards = {}, levels = {}, types = {};
    S.promotions.forEach(function (p) {
      if (p.Bank) banks[p.Bank] = 1;
      if (p.Merchant) merchants[p.Merchant] = 1;
      if (p.MerchantCategory) cats[p.MerchantCategory] = 1;
      if (p.Country) countries[p.Country] = 1;
      if (p.Card) cards[p.Card] = 1;
      if (p.CardLevel) levels[p.CardLevel] = 1;
      if (p.PromotionType) types[p.PromotionType] = 1;
    });
    fill('vpFilterBank', Object.keys(banks).sort(), 'Bank: All');
    fill('vpFilterMerchant', Object.keys(merchants).sort(), 'Merchant: All');
    fill('vpFilterCategory', Object.keys(cats).sort(), 'Category: All');
    fill('vpFilterCountry', Object.keys(countries).sort(), 'Country: All');
    fill('vpFilterCard', Object.keys(cards).sort(), 'Card: All');
    fill('vpFilterCardLevel', Object.keys(levels).sort(), 'Card Level: All');
    fill('vpFilterType', Object.keys(types).sort(), 'Type: All');
  }

  function renderReco() {
    var host = $('vpReco');
    if (!host) return;
    var themes = [
      { t: 'Weekend Dining', cat: ['Dining', 'Coffee'] },
      { t: 'Travel Booking', cat: ['Travel', 'Hotel'] },
      { t: 'Coffee', cat: ['Coffee', 'Dining'] },
      { t: 'Movie', cat: ['Entertainment'] },
      { t: 'Electronics', cat: ['Electronics', 'Shopping'] },
      { t: 'Hotel', cat: ['Hotel', 'Travel'] }
    ];
    host.innerHTML = themes.map(function (th) {
      var list = S.promotions.filter(function (p) {
        return isActive(p) && th.cat.indexOf(p.MerchantCategory) !== -1;
      }).sort(function (a, b) { return (b.DiscountValue || 0) - (a.DiscountValue || 0); });
      var best = list[0];
      if (!best) {
        return '<div class="vp-reco-card"><h4>' + esc(th.t) + '</h4><p class="vp-muted">No matching active promotions in dataset.</p></div>';
      }
      return '<div class="vp-reco-card"><h4>' + esc(th.t) + '</h4><p><strong>' + esc(best.OfferTitle) + '</strong></p>' +
        '<p class="vp-muted">' + esc(best.Bank) + (best.Card ? ' · ' + esc(best.Card) : '') + ' · ' + esc(formatDeal(best)) +
        ' @ ' + esc(best.Merchant) + '</p></div>';
    }).join('');
  }

  function renderInsights() {
    var host = $('vpInsights');
    if (!host) return;
    var list = S.promotions;
    if (!list.length) {
      host.innerHTML = '<div class="vp-insight vp-insight--info">No promotions imported yet. Insights are inferred only from your dataset.</div>';
      return;
    }
    var k = computeKpis(list);
    var cats = {};
    var banks = {};
    list.forEach(function (p) {
      cats[p.MerchantCategory || 'Other'] = (cats[p.MerchantCategory || 'Other'] || 0) + 1;
      banks[p.Bank || 'Other'] = (banks[p.Bank || 'Other'] || 0) + 1;
    });
    var topCat = Object.keys(cats).sort(function (a, b) { return cats[b] - cats[a]; })[0];
    var topBank = Object.keys(banks).sort(function (a, b) { return banks[b] - banks[a]; })[0];
    var verified = list.filter(function (p) { return p.Verified === 'Verified'; }).length;
    var lines = [
      { c: 'info', t: 'Most promotions are in category “' + topCat + '” (' + cats[topCat] + ' records).' },
      { c: 'info', t: 'Bank with most offers: ' + topBank + ' (' + banks[topBank] + ').' },
      { c: 'ok', t: verified + ' / ' + list.length + ' promotions marked Verified.' },
      { c: k.endToday ? 'warn' : 'ok', t: k.endToday + ' promotion(s) expire today; ' + k.endWeek + ' expire this week.' },
      { c: 'info', t: 'Average percent discount (where available): ' + (k.avgDisc ? k.avgDisc.toFixed(1) + '%' : 'n/a') + '; highest: ' + (k.maxDisc ? k.maxDisc + '%' : 'n/a') + '.' },
      { c: 'info', t: 'Active: ' + k.active + ' · Featured: ' + k.featured + ' · Cashback: ' + k.cashback + ' · Installment: ' + k.installment + '.' },
      { c: 'info', t: 'Best dining card (by active dining offers): ' + bestCardFor(['Dining', 'Coffee']) + '.' },
      { c: 'info', t: 'Best travel card: ' + bestCardFor(['Travel', 'Hotel']) + '.' },
      { c: 'info', t: 'Best shopping/electronics card: ' + bestCardFor(['Shopping', 'Electronics']) + '.' }
    ];
    host.innerHTML = lines.map(function (l) {
      return '<div class="vp-insight vp-insight--' + l.c + '">' + esc(l.t) + '</div>';
    }).join('');
  }

  function bestCardFor(cats) {
    var scores = {};
    S.promotions.filter(function (p) {
      return isActive(p) && cats.indexOf(p.MerchantCategory) !== -1;
    }).forEach(function (p) {
      var key = [p.Bank, p.Card || p.CardLevel || 'Card'].filter(Boolean).join(' ');
      scores[key] = (scores[key] || 0) + 1 + (p.DiscountValue || 0) / 100;
    });
    var keys = Object.keys(scores).sort(function (a, b) { return scores[b] - scores[a]; });
    return keys[0] || 'insufficient data';
  }

  function renderReport() {
    var host = $('vpReport');
    if (!host) return;
    var list = S.promotions;
    var k = computeKpis(list);
    var banks = {};
    var merchants = {};
    var cats = {};
    list.forEach(function (p) {
      if (p.Bank) banks[p.Bank] = 1;
      if (p.Merchant) merchants[p.Merchant] = 1;
      if (p.MerchantCategory) cats[p.MerchantCategory] = 1;
    });
    var verified = list.filter(function (p) { return p.Verified === 'Verified'; }).length;
    var pending = list.filter(function (p) { return p.Verified === 'Pending' || p.Status === 'Pending'; }).length;
    var items = [
      ['Total Promotions', list.length],
      ['Verified', verified],
      ['Pending', pending],
      ['Expired', k.expired],
      ['Banks Covered', Object.keys(banks).length],
      ['Merchants Covered', Object.keys(merchants).length],
      ['Categories Covered', Object.keys(cats).length],
      ['Average Discount', k.avgDisc ? k.avgDisc.toFixed(1) + '%' : '—'],
      ['Highest Discount', k.maxDisc ? k.maxDisc + '%' : '—'],
      ['Latest Sync Time', S.lastSyncAt || '—']
    ];
    host.innerHTML = items.map(function (it) {
      return '<div class="vp-report-card"><strong>' + esc(it[0]) + '</strong><div>' + esc(String(it[1])) + '</div></div>';
    }).join('');
  }

  function renderTimeline() {
    var today = todayISO();
    var soon = new Date(); soon.setDate(soon.getDate() + 14);
    var soonISO = soon.toISOString().slice(0, 10);
    var start = [], end = [], exp = [];
    S.promotions.forEach(function (p) {
      if (isExpired(p)) exp.push(p);
      else {
        if (p.StartDate && p.StartDate >= today && p.StartDate <= soonISO) start.push(p);
        if (p.EndDate && p.EndDate >= today && p.EndDate <= soonISO) end.push(p);
      }
    });
    function fill(id, arr) {
      var el = $(id);
      if (!el) return;
      if (!arr.length) { el.innerHTML = '<p class="vp-muted">None</p>'; return; }
      el.innerHTML = arr.slice(0, 40).map(function (p) {
        return '<div class="vp-tl-item" data-id="' + esc(p.id) + '"><strong>' + esc(p.OfferTitle) + '</strong>' +
          esc(p.Merchant) + ' · ' + esc(p.StartDate) + ' → ' + esc(p.EndDate) + '</div>';
      }).join('');
      el.querySelectorAll('.vp-tl-item').forEach(function (node) {
        node.addEventListener('click', function () {
          var p = S.promotions.find(function (x) { return x.id === node.getAttribute('data-id'); });
          if (p) openDrawer(p);
        });
      });
    }
    fill('vpTlStart', start.sort(function (a, b) { return String(a.StartDate).localeCompare(b.StartDate); }));
    fill('vpTlEnd', end.sort(function (a, b) { return String(a.EndDate).localeCompare(b.EndDate); }));
    fill('vpTlExpired', exp.sort(function (a, b) { return String(b.EndDate).localeCompare(a.EndDate); }).slice(0, 40));
  }

  function destroyCharts() {
    Object.keys(S.charts).forEach(function (k) {
      try { S.charts[k].destroy(); } catch (e) {}
      delete S.charts[k];
    });
  }
  function ensureChart(id, cfg) {
    if (typeof Chart === 'undefined') return;
    var canvas = $(id);
    if (!canvas) return;
    if (S.charts[id]) { try { S.charts[id].destroy(); } catch (e) {} }
    S.charts[id] = new Chart(canvas.getContext('2d'), cfg);
  }
  function renderStats() {
    var cats = {}, banks = {}, months = {};
    S.promotions.forEach(function (p) {
      cats[p.MerchantCategory || 'Other'] = (cats[p.MerchantCategory || 'Other'] || 0) + 1;
      banks[p.Bank || 'Other'] = (banks[p.Bank || 'Other'] || 0) + 1;
      if (p.StartDate && p.StartDate.length >= 7) {
        var m = p.StartDate.slice(0, 7);
        months[m] = (months[m] || 0) + 1;
      }
    });
    var catL = Object.keys(cats);
    ensureChart('vpChartCat', {
      type: 'pie',
      data: { labels: catL.length ? catL : ['No data'], datasets: [{ data: catL.length ? catL.map(function (k) { return cats[k]; }) : [1], backgroundColor: CHART_COLORS }] },
      options: { plugins: { legend: { position: 'bottom', labels: { boxWidth: 10 } } }, maintainAspectRatio: false }
    });
    var bankL = Object.keys(banks);
    ensureChart('vpChartBank', {
      type: 'bar',
      data: { labels: bankL.length ? bankL : ['—'], datasets: [{ label: 'Offers', data: bankL.length ? bankL.map(function (k) { return banks[k]; }) : [0], backgroundColor: 'rgba(0,167,160,.75)' }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }, maintainAspectRatio: false }
    });
    var mL = Object.keys(months).sort();
    ensureChart('vpChartTrend', {
      type: 'line',
      data: {
        labels: mL.length ? mL : ['—'],
        datasets: [{ label: 'Started', data: mL.length ? mL.map(function (k) { return months[k]; }) : [0], borderColor: '#00a7a0', backgroundColor: 'rgba(0,167,160,.15)', fill: true, tension: 0.3 }]
      },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }, maintainAspectRatio: false }
    });
    var heat = $('vpHeatmap');
    if (heat) {
      var year = new Date().getFullYear();
      heat.innerHTML = '';
      for (var mo = 1; mo <= 12; mo++) {
        var key = year + '-' + String(mo).padStart(2, '0');
        var n = months[key] || 0;
        var intensity = Math.min(1, n / 8);
        var cell = document.createElement('div');
        cell.className = 'vp-heat';
        cell.style.background = 'rgba(0,167,160,' + (0.08 + intensity * 0.55) + ')';
        cell.innerHTML = key.slice(5) + '<span>' + n + '</span>';
        heat.appendChild(cell);
      }
    }
  }

  function renderVerify() {
    var body = $('vpVerifyBody');
    if (!body) return;
    body.innerHTML = S.promotions.map(function (p) {
      return '<tr><td><strong>' + esc(p.OfferTitle) + '</strong><br><small>' + esc(p.Merchant) + '</small></td>' +
        '<td>' + esc(p.OfficialSource || '—') + '</td>' +
        '<td><span class="vp-badge vp-badge--' + (p.Verified === 'Verified' ? 'verified' : 'pending') + '">' + esc(p.Verified || 'Pending') + '</span></td>' +
        '<td>' + esc(p.LastVerified || '—') + '</td>' +
        '<td>' + (p.SourceURL || p.ApplyURL
          ? '<a href="' + esc(p.SourceURL || p.ApplyURL) + '" target="_blank" rel="noopener noreferrer">Link</a>'
          : '—') + '</td>' +
        '<td><button type="button" class="vp-btn vp-btn--small" data-verify="' + esc(p.id) + '">Mark verified</button></td></tr>';
    }).join('') || '<tr><td colspan="6">No data</td></tr>';
    body.querySelectorAll('[data-verify]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var p = S.promotions.find(function (x) { return x.id === btn.getAttribute('data-verify'); });
        if (!p) return;
        if (p.ApplyURL && !isHttpsOfficial(p.ApplyURL)) {
          alert('Cannot verify: ApplyURL is not an allowed official HTTPS domain.');
          return;
        }
        p.Verified = 'Verified';
        p.Status = p.Status === 'Expired' ? 'Expired' : 'Verified';
        p.LastVerified = new Date().toISOString();
        p.VerifiedBy = 'local-user';
        p.SourceURL = p.SourceURL || p.ApplyURL || '';
        p.UpdatedAt = new Date().toISOString();
        audit('verify', p.PromotionID);
        cacheLocal();
        renderAll();
      });
    });
  }

  function renderAudit() {
    var el = $('vpAuditLog');
    if (!el) return;
    if (!S.auditLog.length) {
      el.innerHTML = '<p class="vp-muted">No audit entries yet.</p>';
      return;
    }
    el.innerHTML = S.auditLog.map(function (a) {
      return '<div class="vp-audit__row"><strong>' + esc(a.action) + '</strong> · ' + esc(a.at) +
        '<br>' + esc(a.detail) + ' <em>(' + esc(a.by || '') + ')</em></div>';
    }).join('');
  }

  function renderTable() {
    var body = $('vpTableBody');
    if (!body) return;
    body.innerHTML = S.promotions.map(function (p) {
      return '<tr><td>' + esc(p.PromotionID) + '</td><td>' + esc(p.Bank) + '</td><td>' + esc(p.Merchant) +
        '</td><td>' + esc(p.OfferTitle) + '</td><td>' + esc(p.PromotionType) + '</td><td>' + esc(p.StartDate) + ' → ' + esc(p.EndDate) +
        '</td><td>' + esc(p.Status) + '</td><td>' + esc(p.Verified) + '</td><td>' +
        '<button type="button" class="vp-btn vp-btn--small" data-edit="' + esc(p.id) + '">Edit</button> ' +
        '<button type="button" class="vp-btn vp-btn--small vp-btn--danger" data-del="' + esc(p.id) + '">Del</button></td></tr>';
    }).join('') || '<tr><td colspan="9">Empty</td></tr>';
    body.querySelectorAll('[data-edit]').forEach(function (b) {
      b.addEventListener('click', function () {
        var p = S.promotions.find(function (x) { return x.id === b.getAttribute('data-edit'); });
        if (p) openForm(p);
      });
    });
    body.querySelectorAll('[data-del]').forEach(function (b) {
      b.addEventListener('click', function () {
        if (!confirm('Delete this promotion?')) return;
        var id = b.getAttribute('data-del');
        S.promotions = S.promotions.filter(function (x) { return x.id !== id; });
        audit('delete', id);
        cacheLocal();
        renderAll();
      });
    });
  }

  function renderAll() {
    fillFilterSelects();
    renderKpis();
    renderCards();
    renderReco();
    renderReport();
    renderTimeline();
    renderInsights();
    renderVerify();
    renderAudit();
    renderTable();
    var active = document.querySelector('.vp-tabs__btn.is-active');
    if (active && active.getAttribute('data-tab') === 'stats') renderStats();
  }

  /* ── Form ── */
  function openForm(p) {
    var panel = $('vpFormPanel');
    if (panel) panel.hidden = false;
    S.editingId = p ? p.id : null;
    $('vpFormTitle').textContent = p ? 'Edit promotion' : 'Add promotion';
    $('vpFormError').textContent = '';
    var x = p || emptyPromo();
    $('vpFieldInternalId').value = x.id || '';
    $('vpFieldId').value = x.PromotionID || '';
    $('vpFieldBank').value = x.Bank || '';
    $('vpFieldCard').value = x.Card || '';
    $('vpFieldCardLevel').value = x.CardLevel || '';
    $('vpFieldMerchant').value = x.Merchant || '';
    $('vpFieldCategory').value = x.MerchantCategory || 'Dining';
    $('vpFieldType').value = x.PromotionType || 'Cashback';
    $('vpFieldTitle').value = x.OfferTitle || '';
    $('vpFieldDesc').value = x.ShortDescription || '';
    $('vpFieldDiscType').value = x.DiscountType || 'Percent';
    $('vpFieldDiscValue').value = x.DiscountValue != null ? x.DiscountValue : '';
    $('vpFieldCap').value = x.CashbackCap != null ? x.CashbackCap : '';
    $('vpFieldMinSpend').value = x.MinimumSpend != null ? x.MinimumSpend : '';
    $('vpFieldMonths').value = x.InstallmentMonths != null ? x.InstallmentMonths : '';
    $('vpFieldEligible').value = x.EligibleCards || '';
    $('vpFieldCountry').value = x.Country || 'Vietnam';
    $('vpFieldCity').value = x.City || '';
    $('vpFieldStart').value = x.StartDate || '';
    $('vpFieldEnd').value = x.EndDate || '';
    $('vpFieldCode').value = x.PromoCode || '';
    $('vpFieldUrl').value = x.ApplyURL || '';
    $('vpFieldSource').value = x.OfficialSource || '';
    $('vpFieldTerms').value = x.Terms || '';
    $('vpFieldPriority').value = x.Priority != null ? x.Priority : 50;
    $('vpFieldFeatured').value = x.Featured ? 'true' : 'false';
    $('vpFieldStatus').value = x.Status || 'Pending';
    $('vpFieldLogo').value = x.Logo || '';
    $('vpFieldBanner').value = x.Banner || '';
  }
  function closeForm() {
    var panel = $('vpFormPanel');
    if (panel) panel.hidden = true;
    S.editingId = null;
    $('vpForm').reset();
  }
  function readForm() {
    var id = $('vpFieldInternalId').value || gId();
    var pid = ($('vpFieldId').value || '').trim() || gId();
    return normalizePromo({
      id: id,
      PromotionID: pid,
      Bank: ($('vpFieldBank').value || '').trim(),
      Card: ($('vpFieldCard').value || '').trim(),
      CardLevel: $('vpFieldCardLevel').value || '',
      Merchant: ($('vpFieldMerchant').value || '').trim(),
      MerchantCategory: $('vpFieldCategory').value || 'Other',
      PromotionType: $('vpFieldType').value || 'Cashback',
      OfferTitle: ($('vpFieldTitle').value || '').trim(),
      ShortDescription: ($('vpFieldDesc').value || '').trim(),
      DiscountType: $('vpFieldDiscType').value || 'Percent',
      DiscountValue: parseFloat($('vpFieldDiscValue').value) || 0,
      CashbackCap: parseMoney($('vpFieldCap').value),
      MinimumSpend: parseMoney($('vpFieldMinSpend').value),
      InstallmentMonths: parseInt($('vpFieldMonths').value, 10) || 0,
      EligibleCards: ($('vpFieldEligible').value || '').trim(),
      Country: ($('vpFieldCountry').value || '').trim(),
      City: ($('vpFieldCity').value || '').trim(),
      StartDate: $('vpFieldStart').value || '',
      EndDate: $('vpFieldEnd').value || '',
      PromoCode: ($('vpFieldCode').value || '').trim(),
      ApplyURL: ($('vpFieldUrl').value || '').trim(),
      OfficialSource: ($('vpFieldSource').value || '').trim(),
      Terms: ($('vpFieldTerms').value || '').trim(),
      Priority: parseInt($('vpFieldPriority').value, 10) || 0,
      Featured: $('vpFieldFeatured').value === 'true',
      Status: $('vpFieldStatus').value || 'Pending',
      Logo: ($('vpFieldLogo').value || '').trim(),
      Banner: ($('vpFieldBanner').value || '').trim(),
      UpdatedAt: new Date().toISOString()
    });
  }

  /* ── Excel ── */
  function ensureXLSX() {
    if (typeof XLSX === 'undefined') {
      alert('Excel library not ready.');
      return false;
    }
    return true;
  }
  function headerStyle() {
    return {
      font: { bold: true, color: { rgb: 'FFFFFFFF' } },
      fill: { fgColor: { rgb: '00A7A0' } },
      alignment: { horizontal: 'center', wrapText: true }
    };
  }
  function downloadTemplate() {
    if (!ensureXLSX()) return;
    var sample = [
      'VISA-HSBC-DINING-01', 'HSBC', 'Live+', 'Platinum', 'Partner F&B', 'Dining', 'Cashback',
      'Ưu đãi dining (điền title official)', 'Copy from official Visa/issuer page only', 'Percent', 10,
      200000, 500000, 0, 'Visa Platinum, Signature', 'Vietnam', 'HCM',
      todayISO(), todayISO(), '', 'https://www.visa.com.vn/vi_vn/visa-offers-and-perks/',
      'Visa Offers & Perks', 'See official terms', 80, 'Yes', 'Pending', '', '', new Date().toISOString()
    ];
    var ws = XLSX.utils.aoa_to_sheet([HEADERS, sample]);
    ws['!cols'] = HEADERS.map(function (h) { return { wch: Math.min(Math.max(h.length + 2, 12), 28) }; });
    ws['!views'] = [{ state: 'frozen', ySplit: 1 }];
    for (var c = 0; c < HEADERS.length; c++) {
      var addr = XLSX.utils.encode_cell({ r: 0, c: c });
      if (ws[addr]) ws[addr].s = headerStyle();
    }
    var wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Visa Promotions');
    XLSX.writeFile(wb, 'Visa_Promo_Template.xlsx');
    setIoStatus('ok', '✓ Template downloaded.');
  }
  function promoToRow(p) {
    return HEADERS.map(function (h) {
      if (h === 'Featured') return p.Featured ? 'Yes' : 'No';
      return p[h] != null ? p[h] : '';
    });
  }
  function exportData() {
    if (!ensureXLSX()) return;
    if (!S.promotions.length) { setIoStatus('warn', '⚠ No data.'); return; }
    var rows = S.promotions.map(promoToRow);
    var ws = XLSX.utils.aoa_to_sheet([HEADERS].concat(rows));
    for (var c = 0; c < HEADERS.length; c++) {
      var addr = XLSX.utils.encode_cell({ r: 0, c: c });
      if (ws[addr]) ws[addr].s = headerStyle();
    }
    var wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Visa Promotions');
    XLSX.writeFile(wb, 'Visa_Promo_Export.xlsx');
    setIoStatus('ok', '✓ Exported ' + S.promotions.length + ' rows.');
  }
  function exportCSV() {
    if (!S.promotions.length) { alert('No data'); return; }
    var lines = [HEADERS.join(',')];
    S.promotions.forEach(function (p) {
      lines.push(promoToRow(p).map(function (v) {
        var s = String(v == null ? '' : v);
        if (/[",\n]/.test(s)) s = '"' + s.replace(/"/g, '""') + '"';
        return s;
      }).join(','));
    });
    var blob = new Blob(['\uFEFF' + lines.join('\n')], { type: 'text/csv;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'visa-promo.csv';
    a.click();
  }
  function exportPdf() {
    window.print();
  }

  function parseImportFile(file) {
    return new Promise(function (resolve, reject) {
      if (!ensureXLSX()) { reject(new Error('XLSX missing')); return; }
      var reader = new FileReader();
      reader.onload = function (ev) {
        try {
          var name = (file.name || '').toLowerCase();
          var rows;
          if (name.endsWith('.csv')) {
            var text = new TextDecoder().decode(new Uint8Array(ev.target.result));
            var wb0 = XLSX.read(text, { type: 'string' });
            rows = XLSX.utils.sheet_to_json(wb0.Sheets[wb0.SheetNames[0]], { header: 1, defval: '' });
          } else {
            var wb = XLSX.read(new Uint8Array(ev.target.result), { type: 'array', cellDates: true });
            var sheet = wb.Sheets[wb.SheetNames[0]];
            rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '', raw: true });
          }
          if (!rows.length) throw new Error('Empty file');
          var header = rows[0].map(function (h) { return String(h || '').trim(); });
          var col = {};
          header.forEach(function (h, i) {
            var key = HEADERS.find(function (H) { return H.toLowerCase() === h.toLowerCase(); });
            if (key) col[key] = i;
          });
          if (col.OfferTitle === undefined && col.Bank === undefined) throw new Error('Schema mismatch — use template headers');
          var valid = [], invalid = [], seen = {};
          for (var r = 1; r < Math.min(rows.length, 20001); r++) {
            var row = rows[r];
            if (!row || !row.length) continue;
            function cell(k) {
              var i = col[k];
              return i === undefined ? '' : row[i];
            }
            function excelDate(v) {
              if (v instanceof Date) return v.toISOString().slice(0, 10);
              if (typeof v === 'number') {
                var epoch = Date.UTC(1899, 11, 30);
                return new Date(epoch + v * 86400000).toISOString().slice(0, 10);
              }
              var s = String(v || '').trim();
              return s.slice(0, 10);
            }
            var pid = String(cell('PromotionID') || '').trim() || gId();
            var p = normalizePromo({
              id: gId(),
              PromotionID: pid,
              Bank: String(cell('Bank') || '').trim(),
              Card: String(cell('Card') || '').trim(),
              CardLevel: String(cell('CardLevel') || '').trim(),
              Merchant: String(cell('Merchant') || '').trim(),
              MerchantCategory: String(cell('MerchantCategory') || 'Other').trim(),
              PromotionType: String(cell('PromotionType') || 'Cashback').trim(),
              OfferTitle: String(cell('OfferTitle') || '').trim(),
              ShortDescription: String(cell('ShortDescription') || '').trim(),
              DiscountType: String(cell('DiscountType') || 'Percent').trim(),
              DiscountValue: parseFloat(String(cell('DiscountValue')).replace(',', '.')) || 0,
              CashbackCap: parseMoney(cell('CashbackCap')),
              MinimumSpend: parseMoney(cell('MinimumSpend')),
              InstallmentMonths: parseInt(cell('InstallmentMonths'), 10) || 0,
              EligibleCards: String(cell('EligibleCards') || '').trim(),
              Country: String(cell('Country') || 'Vietnam').trim(),
              City: String(cell('City') || '').trim(),
              StartDate: excelDate(cell('StartDate')),
              EndDate: excelDate(cell('EndDate')),
              PromoCode: String(cell('PromoCode') || '').trim(),
              ApplyURL: String(cell('ApplyURL') || '').trim(),
              OfficialSource: String(cell('OfficialSource') || '').trim(),
              Terms: String(cell('Terms') || '').trim(),
              Priority: parseInt(cell('Priority'), 10) || 0,
              Featured: yesNo(cell('Featured')),
              Status: String(cell('Status') || 'Pending').trim(),
              Logo: String(cell('Logo') || '').trim(),
              Banner: String(cell('Banner') || '').trim(),
              UpdatedAt: String(cell('UpdatedAt') || new Date().toISOString()),
              Verified: 'Pending',
              _row: r + 1
            });
            var errs = validatePromo(p, {});
            var key = pid.toLowerCase();
            if (seen[key]) errs.push('Duplicate PromotionID in file');
            if (S.promotions.some(function (x) { return String(x.PromotionID).toLowerCase() === key; })) {
              errs.push('Duplicate PromotionID exists');
            }
            if (!p.Bank && !p.Merchant && !p.OfferTitle) continue;
            if (errs.length) invalid.push({ row: r + 1, errors: errs, p: p });
            else { seen[key] = 1; valid.push(p); }
          }
          resolve({ valid: valid, invalid: invalid, total: valid.length + invalid.length });
        } catch (e) { reject(e); }
      };
      reader.onerror = function () { reject(new Error('Read failed')); };
      reader.readAsArrayBuffer(file);
    });
  }

  function openImportModal(result) {
    pendingImport = result;
    var modal = $('vpImportModal');
    if (modal) modal.hidden = false;
    $('vpImportSummary').innerHTML = 'Valid: <strong>' + result.valid.length + '</strong> · Skipped: <strong>' + result.invalid.length + '</strong>';
    $('vpImportHead').innerHTML = '<tr><th>#</th><th>OK</th><th>ID</th><th>Bank</th><th>Merchant</th><th>Title</th><th>Errors</th></tr>';
    var body = $('vpImportBody');
    body.innerHTML = '';
    result.invalid.concat(result.valid.slice(0, 40)).slice(0, 80).forEach(function (item) {
      var ok = !item.errors;
      var p = ok ? item : item.p;
      var tr = document.createElement('tr');
      tr.className = ok ? '' : 'is-invalid';
      tr.innerHTML = '<td>' + (item.row || p._row || '') + '</td><td>' + (ok ? '✓' : '✗') + '</td><td>' +
        esc(p.PromotionID) + '</td><td>' + esc(p.Bank) + '</td><td>' + esc(p.Merchant) + '</td><td>' +
        esc(p.OfferTitle) + '</td><td>' + esc((item.errors || []).join('; ')) + '</td>';
      body.appendChild(tr);
    });
    $('vpImportReport').textContent = result.invalid.length
      ? result.invalid.slice(0, 30).map(function (i) { return 'Row ' + i.row + ': ' + i.errors.join('; '); }).join('\n')
      : 'All valid.';
    $('vpImportConfirm').disabled = !result.valid.length;
  }

  function confirmImport() {
    if (!pendingImport || !pendingImport.valid.length) return;
    var mode = (document.querySelector('input[name="vpImportMode"]:checked') || {}).value || 'append';
    if (mode === 'replace') S.promotions = pendingImport.valid.map(function (p) {
      delete p._row; return p;
    });
    else {
      pendingImport.valid.forEach(function (p) {
        delete p._row;
        S.promotions.push(p);
      });
    }
    audit('import', pendingImport.valid.length + ' rows · mode ' + mode);
    cacheLocal();
    pendingImport = null;
    $('vpImportModal').hidden = true;
    setIoStatus('ok', '✓ Imported. Remember 💾 Save to GitHub.');
    renderAll();
  }

  function syncOfficial() {
    // Does NOT fabricate offers. Only re-checks existing records' URLs / expiry and stamps sync time.
    var fixed = 0, expired = 0, badUrl = 0;
    S.promotions.forEach(function (p) {
      if (isExpired(p)) { p.Status = 'Expired'; expired++; }
      if (p.ApplyURL && !isHttpsOfficial(p.ApplyURL)) {
        p.Verified = 'Pending';
        badUrl++;
      } else if (p.ApplyURL && p.Verified !== 'Verified') {
        // leave pending until human marks verified
      }
      p.UpdatedAt = new Date().toISOString();
      fixed++;
    });
    S.lastSyncAt = new Date().toISOString();
    audit('sync-official', 'metadata pass · expired ' + expired + ' · bad URL ' + badUrl + ' · touched ' + fixed + ' · no fabricated offers');
    cacheLocal();
    setIoStatus('ok', '✓ Sync metadata complete (no fabricated promotions). Expired: ' + expired + ', bad URLs: ' + badUrl + '. Save to GitHub to persist.');
    renderAll();
  }

  /* ── Tabs & events ── */
  function switchTab(name) {
    document.querySelectorAll('.vp-tabs__btn').forEach(function (b) {
      b.classList.toggle('is-active', b.getAttribute('data-tab') === name);
    });
    document.querySelectorAll('.vp-panel').forEach(function (p) {
      var on = p.getAttribute('data-panel') === name;
      p.hidden = !on;
      p.classList.toggle('is-active', on);
    });
    if (name === 'stats') renderStats();
  }

  function debounce(fn, ms) {
    var t;
    return function () {
      var args = arguments, self = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(self, args); }, ms);
    };
  }

  function initEvents() {
    document.querySelectorAll('.vp-tabs__btn').forEach(function (b) {
      b.addEventListener('click', function () { switchTab(b.getAttribute('data-tab')); });
    });
    on($('vpTokenBtn'), 'click', promptToken);
    on($('vpSaveBtn'), 'click', function () {
      saveToGitHub()['catch'](function (e) { alert('Save failed: ' + e.message); });
    });
    on($('vpLogoutBtn'), 'click', function () {
      sessionStorage.removeItem(SESSION_KEY);
      hideApp();
      var input = $('vpGateInput');
      if (input) { input.value = ''; input.focus(); }
    });
    on($('vpDownloadTemplate'), 'click', downloadTemplate);
    on($('vpExportDataBtn'), 'click', exportData);
    on($('vpExportCsv'), 'click', exportCSV);
    on($('vpExportXlsx'), 'click', exportData);
    on($('vpExportPdf'), 'click', exportPdf);
    on($('vpSyncOfficialBtn'), 'click', syncOfficial);
    on($('vpAddPromoBtn'), 'click', function () { openForm(null); });
    on($('vpFormCancel'), 'click', closeForm);
    on($('vpForm'), 'submit', function (e) {
      e.preventDefault();
      var p = readForm();
      var errs = validatePromo(p, { checkDup: !S.editingId, ignoreId: S.editingId });
      if (S.editingId) {
        errs = validatePromo(p, {});
        var other = S.promotions.some(function (x) {
          return x.id !== S.editingId && String(x.PromotionID).toLowerCase() === String(p.PromotionID).toLowerCase();
        });
        if (other) errs.push('Duplicate PromotionID');
      }
      if (errs.length) { $('vpFormError').textContent = errs.join(' · '); return; }
      if (S.editingId) {
        var idx = S.promotions.findIndex(function (x) { return x.id === S.editingId; });
        if (idx >= 0) {
          p.Verified = S.promotions[idx].Verified;
          p.LastVerified = S.promotions[idx].LastVerified;
          p.VerifiedBy = S.promotions[idx].VerifiedBy;
          p.SourceURL = S.promotions[idx].SourceURL || p.ApplyURL;
          S.promotions[idx] = p;
        }
        audit('update', p.PromotionID);
      } else {
        p.SourceURL = p.ApplyURL || '';
        S.promotions.push(p);
        audit('create', p.PromotionID);
      }
      cacheLocal();
      closeForm();
      renderAll();
      setIoStatus('ok', '✓ Saved locally. Click 💾 Save to GitHub to persist permanently.');
    });

    var search = debounce(function () {
      S.filters.q = $('vpSearch').value || '';
      renderCards();
    }, 200);
    on($('vpSearch'), 'input', search);
    ['Bank', 'Merchant', 'Category', 'Country', 'Card', 'CardLevel', 'Type', 'Status'].forEach(function (name) {
      var id = 'vpFilter' + name;
      on($(id), 'change', function () {
        var key = name === 'CardLevel' ? 'cardLevel' : name.toLowerCase();
        S.filters[key] = this.value || '';
        renderCards();
      });
    });
    on($('vpFilterFrom'), 'change', function () { S.filters.from = this.value || ''; renderCards(); });
    on($('vpFilterTo'), 'change', function () { S.filters.to = this.value || ''; renderCards(); });

    on($('vpImportBtn'), 'click', function () { $('vpImportFile').click(); });
    on($('vpImportFile'), 'change', function () {
      var f = this.files && this.files[0];
      if (!f) return;
      setIoStatus('ok', 'Parsing…');
      parseImportFile(f).then(openImportModal)['catch'](function (e) {
        setIoStatus('err', '✗ ' + e.message);
      });
      this.value = '';
    });
    var drop = $('vpDrop');
    if (drop) {
      on(drop, 'click', function () { $('vpImportFile').click(); });
      ['dragenter', 'dragover'].forEach(function (ev) {
        on(drop, ev, function (e) { e.preventDefault(); drop.classList.add('is-dragover'); });
      });
      ['dragleave', 'drop'].forEach(function (ev) {
        on(drop, ev, function (e) { e.preventDefault(); drop.classList.remove('is-dragover'); });
      });
      on(drop, 'drop', function (e) {
        var f = e.dataTransfer && e.dataTransfer.files[0];
        if (f) parseImportFile(f).then(openImportModal)['catch'](function (err) { setIoStatus('err', err.message); });
      });
    }
    on($('vpImportCancel'), 'click', function () { $('vpImportModal').hidden = true; pendingImport = null; });
    on($('vpImportClose'), 'click', function () { $('vpImportModal').hidden = true; pendingImport = null; });
    on($('vpImportBackdrop'), 'click', function () { $('vpImportModal').hidden = true; pendingImport = null; });
    on($('vpImportConfirm'), 'click', confirmImport);

    on($('vpBackupBtn'), 'click', function () {
      var blob = new Blob([JSON.stringify(payload(), null, 2)], { type: 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'visa-promo-backup.json';
      a.click();
    });
    on($('vpRestoreBtn'), 'click', function () { $('vpRestoreFile').click(); });
    on($('vpRestoreFile'), 'change', function () {
      var f = this.files && this.files[0];
      if (!f) return;
      var reader = new FileReader();
      reader.onload = function () {
        try {
          applyData(JSON.parse(reader.result));
          audit('restore', 'from backup file');
          cacheLocal();
          renderAll();
          setIoStatus('ok', '✓ Restored. Save to GitHub to sync.');
        } catch (e) { setIoStatus('err', 'Invalid backup'); }
      };
      reader.readAsText(f);
      this.value = '';
    });

    on($('vpDrawerClose'), 'click', closeDrawer);
    on($('vpDrawerBackdrop'), 'click', closeDrawer);
  }

  function init() {
    if (!$('vpAppRoot')) return;
    hideApp();
    // gate visible by default
    var gate = $('vpGate');
    if (gate) gate.style.display = '';
    initGate();
    initEvents();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
