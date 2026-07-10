(function () {
  'use strict';

  var DATA_URL = '/reviewchanthat/data/topik-bank.json';
  var STORAGE_KEY = 'topik_l6_state';

  var defaultState = {
    listening: { score: 70, max: 100 },
    reading: { score: 74, max: 100 },
    writing: { score: 39, max: 100 },
    errors: [],
    logs: [],
    planChecked: [],
    mockResults: []
  };

  var state, data;

  function loadState() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        state = JSON.parse(raw);
        state.errors = state.errors || [];
        state.logs = state.logs || [];
        state.planChecked = state.planChecked || [];
        state.mockResults = state.mockResults || [];
        return;
      }
    } catch (_) {}
    state = JSON.parse(JSON.stringify(defaultState));
  }

  function saveState() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (_) {}
  }

  function totalScore() {
    return (state.listening.score || 0) + (state.reading.score || 0) + (state.writing.score || 0);
  }

  function targetProgress() {
    var t = 230;
    var c = totalScore();
    return Math.min(100, Math.round((c / t) * 100));
  }

  function getColor(val, min, max) {
    if (val >= max) return 'green';
    if (val >= min) return 'amber';
    return 'red';
  }

  /* Navigation */
  function initNav() {
    var btns = document.querySelectorAll('.topik__nav-btn');
    var mods = document.querySelectorAll('.topik__module');
    btns.forEach(function (b) {
      b.addEventListener('click', function () {
        var mod = b.getAttribute('data-module');
        btns.forEach(function (x) { x.classList.remove('is-active'); });
        b.classList.add('is-active');
        mods.forEach(function (m) {
          m.classList.toggle('is-active', m.getAttribute('data-module') === mod);
        });
        renderModule(mod);
      });
    });
  }

  function renderModule(name) {
    switch (name) {
      case 'dashboard': renderDashboard(); break;
      case 'strategy': renderStrategy(); break;
      case 'listening': renderQuiz('listening'); break;
      case 'reading': renderQuiz('reading'); break;
      case 'writing': renderWriting(); break;
      case 'vocab': renderVocab(); break;
      case 'diagnostic': renderDiagnostic(); break;
      case 'errors': renderErrors(); break;
      case 'plan': renderPlan(); break;
    }
  }

  /* Score inputs */
  function renderScoreInputs(container) {
    container.innerHTML =
      '<div class="topik-score-inputs">' +
        '<div class="topik-score-input-group"><label>Listening</label><input class="topik-input" type="number" id="topikScoreL" value="' + (state.listening.score || 70) + '" min="0" max="100"></div>' +
        '<div class="topik-score-input-group"><label>Reading</label><input class="topik-input" type="number" id="topikScoreR" value="' + (state.reading.score || 74) + '" min="0" max="100"></div>' +
        '<div class="topik-score-input-group"><label>Writing</label><input class="topik-input" type="number" id="topikScoreW" value="' + (state.writing.score || 39) + '" min="0" max="100"></div>' +
      '</div>' +
      '<button class="topik-btn topik-btn--primary" id="topikScoreUpdate">Cập nhật điểm</button>';
    document.getElementById('topikScoreUpdate').addEventListener('click', function () {
      state.listening.score = Math.min(100, Math.max(0, parseInt(document.getElementById('topikScoreL').value) || 0));
      state.reading.score = Math.min(100, Math.max(0, parseInt(document.getElementById('topikScoreR').value) || 0));
      state.writing.score = Math.min(100, Math.max(0, parseInt(document.getElementById('topikScoreW').value) || 0));
      saveState();
      renderModule(document.querySelector('.topik__nav-btn.is-active').getAttribute('data-module'));
    });
  }

  /* Dashboard */
  function renderDashboard() {
    var el = document.getElementById('topikDashboard');
    var t = totalScore();
    var p = targetProgress();
    var li = state.listening.score || 0;
    var re = state.reading.score || 0;
    var wr = state.writing.score || 0;

    el.innerHTML =
      '<div class="topik-dash-grid">' +
        '<div class="topik-dash-total">' +
          '<span class="topik-score topik-score--accent">' +
            '<span class="topik-score__value">' + t + '</span>' +
            '<span class="topik-score__max">/ 230</span>' +
          '</span>' +
          '<span class="topik-score__label">Tổng điểm</span>' +
          '<div class="topik-progress-bar"><div class="topik-progress-bar__fill" style="width:' + p + '%"></div></div>' +
        '</div>' +
      '</div>' +
      '<div class="topik-dash-breakdown">' +
        dashItem('Nghe', li, 85, 100, 'topik-score--' + getColor(li, 85, 100)) +
        dashItem('Đọc', re, 85, 100, 'topik-score--' + getColor(re, 85, 100)) +
        dashItem('Viết', wr, 60, 100, 'topik-score--' + getColor(wr, 60, 100)) +
      '</div>';

    renderScoreInputs(el);
    el.innerHTML +=
      '<div class="topik-card topik-card--accent" style="margin-top:1rem">' +
        '<div class="topik-card__title">📈 Mục tiêu 230</div>' +
        '<div class="topik-card__text">Listening 85+ / Reading 85+ / Writing 60+</div>' +
        '<div style="display:flex;gap:.75rem;flex-wrap:wrap;margin-top:.5rem">' +
          miniBar('Nghe', li, 85) +
          miniBar('Đọc', re, 85) +
          miniBar('Viết', wr, 60) +
        '</div>' +
      '</div>' +
      (state.logs.length > 0 ? '<div class="topik-card" style="margin-top:.75rem"><div class="topik-card__title">📋 Lịch sử</div>' + state.logs.slice(-5).reverse().map(function (l) { return '<div class="topik-card__text" style="font-size:.8rem;margin-bottom:.25rem">' + l + '</div>'; }).join('') + '</div>' : '');
  }

  function dashItem(label, val, minTarget, max, cls) {
    return '<div class="topik-dash-item">' +
      '<span class="topik-score ' + cls + '">' +
        '<span class="topik-score__value">' + val + '</span>' +
        '<span class="topik-score__max">/ ' + max + '</span>' +
      '</span>' +
      '<span class="topik-dash-item__label">' + label + '</span>' +
    '</div>';
  }

  function miniBar(label, current, target) {
    var pct = Math.min(100, Math.round((current / target) * 100));
    var color = current >= target ? 'var(--topik-green)' : 'var(--topik-amber)';
    return '<div style="flex:1;min-width:80px"><div style="font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:var(--topik-muted);margin-bottom:.2rem">' + label + ' ' + current + '/' + target + '</div><div class="topik-strat-bar"><div class="topik-strat-bar__fill" style="width:' + pct + '%;background:' + color + '"></div></div></div>';
  }

  /* Strategy */
  function renderStrategy() {
    var el = document.getElementById('topikStrategy');
    var li = state.listening.score || 0;
    var re = state.reading.score || 0;
    var wr = state.writing.score || 0;

    var strat = [
      { icon: '🎧', title: 'Listening — ' + (li >= 85 ? 'Ổn định' : 'Cần cải thiện'), desc: li >= 85 ? 'Duy trì phong độ. Tập trung vào câu hỏi 7 điểm (Q14,15,24). Luyện đề thật kỳ 83.' : 'Mục tiêu 85+. Luyện nghe chủ đề học thuật, ghi chú từ khóa, làm quen giọng đọc nhanh.' },
      { icon: '📖', title: 'Reading — ' + (re >= 85 ? 'Ổn định' : 'Cần cải thiện'), desc: re >= 85 ? 'Duy trì. Chú ý câu hỏi luận điểm chính (Q35-38) và câu điền chỗ trống.' : 'Mục tiêu 85+. Đọc nhiều bài báo học thuật, luyện kỹ năng skimming/scanning.' },
      { icon: '✍️', title: 'Writing — ' + (wr >= 60 ? 'Ổn định' : 'Cần cải thiện'), desc: wr >= 60 ? 'Duy trì. Tập trung Q54 (50 điểm) — lập luận chặt chẽ, từ nối học thuật.' : 'Mục tiêu 60+. Học cấu trúc câu, từ nối, luyện viết Q51-Q52 trước.' },
      { icon: '🎯', title: 'Tổng điểm: ' + totalScore() + '/230', desc: totalScore() >= 230 ? 'Bạn đang ở Level 6! Tiếp tục ôn luyện để duy trì và cải thiện.' : 'Cần thêm ' + (230 - totalScore()) + ' điểm. ' + (230 - totalScore() <= 30 ? 'Rất gần rồi! Tập trung vào kỹ năng yếu nhất.' : 'Hãy tập trung vào Writing trước — đây là kỹ năng dễ cải thiện điểm nhất.') }
    ];

    el.innerHTML = '<div class="topik-strat-grid">' + strat.map(function (s) {
      return '<div class="topik-strat-card">' +
        '<div class="topik-strat-card__icon">' + s.icon + '</div>' +
        '<div class="topik-strat-card__title">' + s.title + '</div>' +
        '<div class="topik-strat-card__desc">' + s.desc + '</div>' +
      '</div>';
    }).join('') + '</div>';

    el.innerHTML +=
      '<div class="topik-card topik-card--accent">' +
        '<div class="topik-card__title">💡 Chiến thuật làm bài</div>' +
        '<div class="topik-card__text"><strong>Listening:</strong> Đọc trước câu hỏi — ghi chú từ khóa — tập trung đoạn cuối (thường chứa đáp án).<br><strong>Reading:</strong> Skimming ý chính trước — đọc câu hỏi — scanning thông tin.<br><strong>Writing:</strong> Q51-52: đúng ngữ pháp + từ vựng. Q53: phân tích số liệu. Q54: luận điểm rõ ràng + dẫn chứng.</div>' +
      '</div>';
  }

  /* Quiz engine */
  var quizState = {};
  function renderQuiz(type) {
    var el = document.getElementById('topik' + type.charAt(0).toUpperCase() + type.slice(1));
    var items = (data && data[type]) || [];
    if (!items.length) { el.innerHTML = '<p>Đang tải dữ liệu...</p>'; return; }

    var key = type + 'Index';
    if (!quizState[key]) quizState[key] = 0;
    var idx = quizState[key];
    if (idx >= items.length) { idx = 0; quizState[key] = 0; }

    var item = items[idx];
    var answered = quizState[type + '_ans_' + idx];

    var html = '<div class="topik-quiz-progress">' + type.charAt(0).toUpperCase() + type.slice(1) + ' — Câu ' + (idx + 1) + '/' + items.length + '</div>';

    if (item.passage) {
      html += '<div class="topik-quiz-passage">' + item.passage + '</div>';
    }
    if (item.transcript) {
      html += '<div class="topik-quiz-transcript">🎧 ' + item.transcript + '</div>';
    }

    html += '<div class="topik-quiz-question">' + item.question + '</div>';
    html += '<div class="topik-quiz-choices" data-type="' + type + '" data-idx="' + idx + '">';

    item.choices.forEach(function (c, ci) {
      var cls = 'topik-quiz-choice';
      if (answered !== undefined) {
        if (ci === item.answer) cls += ' is-correct';
        if (ci === answered && ci !== item.answer) cls += ' is-wrong';
        if (ci === answered) cls += ' is-selected';
      }
      html += '<button class="' + cls + '" data-ci="' + ci + '"' + (answered !== undefined ? ' disabled' : '') + '>' + c + '</button>';
    });
    html += '</div>';

    if (answered !== undefined) {
      html += '<div class="topik-quiz-explain"><strong>Giải thích:</strong> ' + (item.explanation || '') + '</div>';
      html += '<div class="topik-quiz-actions"><button class="topik-btn topik-btn--primary topik-quiz-next" data-type="' + type + '">Câu tiếp →</button></div>';
    }

    el.innerHTML = html;

    el.querySelectorAll('.topik-quiz-choice:not(.is-correct):not(.is-wrong)').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var ci = parseInt(btn.getAttribute('data-ci'));
        var container = btn.closest('.topik-quiz-choices');
        var t = container.getAttribute('data-type');
        var i = parseInt(container.getAttribute('data-idx'));
        quizState[t + '_ans_' + i] = ci;
        var it = data[t][i];

        if (ci !== it.answer) {
          state.errors.push({
            type: t,
            id: it.id,
            question: it.question,
            yourAnswer: it.choices[ci],
            correctAnswer: it.choices[it.answer],
            explanation: it.explanation || ''
          });
          if (state.errors.length > 200) state.errors = state.errors.slice(-200);
          saveState();
        }
        renderQuiz(t);
      });
    });

    var nextBtn = el.querySelector('.topik-quiz-next');
    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        var t = nextBtn.getAttribute('data-type');
        quizState[t + 'Index'] = (quizState[t + 'Index'] || 0) + 1;
        renderQuiz(t);
      });
    }
  }

  /* Writing */
  function renderWriting() {
    var el = document.getElementById('topikWriting');
    var items = (data && data.writing) || [];
    if (!items.length) { el.innerHTML = '<p>Đang tải dữ liệu...</p>'; return; }

    var html = '<div class="topik-card topik-card--accent"><div class="topik-card__title">✍️ Writing Booster</div><div class="topik-card__text">12 đề viết theo đúng format TOPIK II — Q51 (10đ), Q52 (10đ), Q53 (30đ), Q54 (50đ). Click vào đề để xem dàn ý và biểu đạt gợi ý.</div></div>';
    html += '<div class="topik-writing-grid">';

    items.forEach(function (w) {
      var typeLabel = w.type || 'Q51';
      html += '<div class="topik-writing-card">' +
        '<div class="topik-writing-card__badge">' + typeLabel + '</div>' +
        '<div class="topik-writing-card__prompt">' + w.prompt.slice(0, 120) + (w.prompt.length > 120 ? '...' : '') + '</div>' +
        '<div class="topik-writing-card__rubric">' + (w.rubric ? w.rubric.split('|').map(function (r) { return '<span>' + r + '</span>'; }).join('') : '') + '</div>' +
        '<button class="topik-btn topik-btn--secondary topik-btn--sm topik-writing-toggle" style="margin-top:.5rem" data-idx="' + itemIndex('writing', w.id) + '">Xem chi tiết</button>' +
        '<div class="topik-writing-detail" style="display:none;margin-top:.75rem;padding-top:.75rem;border-top:1px solid var(--topik-border)">' +
          '<div class="topik-card__text" style="font-size:.85rem"><strong>Đề bài:</strong> ' + w.prompt + '</div>' +
          (w.outline ? '<div class="topik-card__text" style="font-size:.82rem;margin-top:.4rem"><strong>Dàn ý:</strong> ' + w.outline + '</div>' : '') +
          (w.expressions ? '<div class="topik-card__text" style="font-size:.82rem;margin-top:.4rem"><strong>Biểu đạt gợi ý:</strong> ' + (Array.isArray(w.expressions) ? w.expressions.join(' · ') : w.expressions) + '</div>' : '') +
        '</div>' +
      '</div>';
    });

    html += '</div>';
    el.innerHTML = html;

    el.querySelectorAll('.topik-writing-toggle').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var detail = btn.parentElement.querySelector('.topik-writing-detail');
        if (detail.style.display === 'none') {
          detail.style.display = 'block';
          btn.textContent = 'Thu gọn';
        } else {
          detail.style.display = 'none';
          btn.textContent = 'Xem chi tiết';
        }
      });
    });
  }

  function itemIndex(type, id) {
    if (!data || !data[type]) return -1;
    for (var i = 0; i < data[type].length; i++) {
      if (data[type][i].id === id) return i;
    }
    return -1;
  }

  /* Vocabulary */
  function renderVocab(catId) {
    var el = document.getElementById('topikVocab');
    var cats = (data && data.vocab_categories) || [];
    var glossary = (data && data.glossary) || [];
    if (!cats.length) { el.innerHTML = '<p>Đang tải dữ liệu...</p>'; return; }

    var activeCat = catId || el.getAttribute('data-active') || 'all';
    el.setAttribute('data-active', activeCat);

    var html = '<div class="topik-vocab-tabs">' +
      '<button class="topik-vocab-tab' + (activeCat === 'all' ? ' is-active' : '') + '" data-cat="all">Tất cả (' + glossary.length + ')</button>';
    cats.forEach(function (c) {
      html += '<button class="topik-vocab-tab' + (activeCat === c.id ? ' is-active' : '') + '" data-cat="' + c.id + '">' + c.label + ' (' + c.items.length + ')</button>';
    });
    html += '</div>';

    var filtered = (activeCat === 'all') ? glossary : glossary.filter(function (g) { return g.category === activeCat; });

    if (!filtered.length) {
      html += '<p style="color:var(--topik-muted);padding:1rem">Không có từ vựng nào trong danh mục này.</p>';
    } else {
      html += '<div class="topik-vocab-grid">';
      filtered.forEach(function (g) {
        html += '<div class="topik-vocab-item">' +
          '<div class="topik-vocab-item__ko">' + g.korean + '</div>' +
          '<div class="topik-vocab-item__vi">' + g.vi + '</div>' +
          (g.sample ? '<div class="topik-vocab-item__sample">' + g.sample + '</div>' : '') +
        '</div>';
      });
      html += '</div>';
    }

    el.innerHTML = html;

    el.querySelectorAll('.topik-vocab-tab').forEach(function (tab) {
      tab.addEventListener('click', function () {
        renderVocab(tab.getAttribute('data-cat'));
      });
    });
  }

  /* Diagnostic */
  var diagState = {};
  function renderDiagnostic() {
    var el = document.getElementById('topikDiagnostic');
    if (!diagState.active) {
      el.innerHTML =
        '<div class="topik-diag-intro">' +
          '<div class="topik-diag-intro__title">🧪 Thi thử TOPIK II</div>' +
          '<div class="topik-diag-intro__desc">10 câu hỏi ngẫu nhiên (5 nghe + 5 đọc). Giới hạn 15 phút. Kết quả được lưu lại để theo dõi tiến độ.</div>' +
          '<button class="topik-btn topik-btn--primary topik-btn--lg" id="topikDiagStart">Bắt đầu thi</button>' +
        '</div>';
      document.getElementById('topikDiagStart').addEventListener('click', startDiagnostic);
      return;
    }

    var items = diagState.items;
    var idx = diagState.idx || 0;
    if (idx >= items.length) {
      finishDiagnostic();
      return;
    }

    var remaining = diagState.endTime - Date.now();
    if (remaining <= 0) { finishDiagnostic(); return; }
    var mins = Math.floor(remaining / 60000);
    var secs = Math.floor((remaining % 60000) / 1000);

    var item = items[idx];
    var answered = diagState.answers[idx];

    var html = '<div class="topik-diag-timer' + (remaining < 120000 ? ' is-warning' : '') + '" id="topikDiagTimer">⏱ ' + pad(mins) + ':' + pad(secs) + '</div>';
    html += '<div class="topik-quiz-progress">Thi thử — Câu ' + (idx + 1) + '/' + items.length + '</div>';

    if (item.passage) html += '<div class="topik-quiz-passage">' + item.passage + '</div>';
    if (item.transcript) html += '<div class="topik-quiz-transcript">🎧 ' + item.transcript + '</div>';

    html += '<div class="topik-quiz-question">' + item.question + '</div>';
    html += '<div class="topik-quiz-choices">';

    item.choices.forEach(function (c, ci) {
      var cls = 'topik-quiz-choice';
      if (answered !== undefined) {
        if (ci === item.answer) cls += ' is-correct';
        if (ci === answered && ci !== item.answer) cls += ' is-wrong';
        if (ci === answered) cls += ' is-selected';
      }
      html += '<button class="' + cls + '" data-ci="' + ci + '"' + (answered !== undefined ? ' disabled' : '') + '>' + c + '</button>';
    });
    html += '</div>';

    if (answered !== undefined) {
      html += '<div class="topik-quiz-explain"><strong>Giải thích:</strong> ' + (item.explanation || '') + '</div>';
      html += '<div class="topik-quiz-actions"><button class="topik-btn topik-btn--primary topik-diag-next">Câu tiếp →</button></div>';
    }

    el.innerHTML = html;

    el.querySelectorAll('.topik-quiz-choice:not(.is-correct):not(.is-wrong)').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var ci = parseInt(btn.getAttribute('data-ci'));
        diagState.answers[idx] = ci;
        renderDiagnostic();
      });
    });

    var nextBtn = el.querySelector('.topik-diag-next');
    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        diagState.idx = (diagState.idx || 0) + 1;
        renderDiagnostic();
      });
    }

    if (diagState._timer) clearTimeout(diagState._timer);
    diagState._timer = setTimeout(function () { renderDiagnostic(); }, 1000);
  }

  function startDiagnostic() {
    var listeningItems = (data && data.listening) || [];
    var readingItems = (data && data.reading) || [];
    var pool = [];

    function shuffle(a) {
      for (var i = a.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var t = a[i]; a[i] = a[j]; a[j] = t;
      }
      return a;
    }

    var lPool = shuffle(listeningItems.slice()).slice(0, 5);
    var rPool = shuffle(readingItems.slice()).slice(0, 5);
    pool = shuffle(lPool.concat(rPool));

    diagState = {
      active: true,
      items: pool,
      answers: [],
      idx: 0,
      endTime: Date.now() + 15 * 60 * 1000,
      _timer: null
    };
    renderDiagnostic();
  }

  function finishDiagnostic() {
    if (diagState._timer) clearTimeout(diagState._timer);
    var el = document.getElementById('topikDiagnostic');
    var items = diagState.items || [];
    var answers = diagState.answers || [];
    var correct = 0;
    items.forEach(function (item, i) {
      if (answers[i] === item.answer) correct++;
    });
    var pct = Math.round((correct / items.length) * 100);

    state.mockResults.push({
      date: new Date().toISOString(),
      correct: correct,
      total: items.length,
      pct: pct
    });
    if (state.mockResults.length > 20) state.mockResults = state.mockResults.slice(-20);
    saveState();

    el.innerHTML =
      '<div class="topik-card topik-card--' + (pct >= 70 ? 'green' : pct >= 50 ? 'amber' : 'red') + '" style="text-align:center;padding:2rem">' +
        '<div style="font-size:2rem;font-weight:800;color:var(--topik-' + (pct >= 70 ? 'green' : pct >= 50 ? 'amber' : 'red') + ')">' + correct + '/' + items.length + '</div>' +
        '<div style="font-size:1rem;color:var(--topik-muted);margin:.3rem 0 1rem">' + pct + '% đúng</div>' +
        '<div style="font-size:.85rem;color:var(--topik-muted);margin-bottom:1rem">' + (pct >= 70 ? 'Tốt! Tiếp tục duy trì.' : pct >= 50 ? 'Khá. Cần ôn thêm.' : 'Cần ôn luyện nhiều hơn.') + '</div>' +
        '<button class="topik-btn topik-btn--primary topik-btn--sm" id="topikDiagReset">Làm lại</button>' +
      '</div>' +
      (state.mockResults.length > 1 ? (
        '<div class="topik-card" style="margin-top:.75rem"><div class="topik-card__title">Kết quả các lần trước</div>' +
        state.mockResults.slice(-5).reverse().map(function (r) {
          return '<div class="topik-card__text" style="font-size:.82rem;margin-bottom:.15rem">' + new Date(r.date).toLocaleDateString('vi-VN') + ' — ' + r.correct + '/' + r.total + ' (' + r.pct + '%)</div>';
        }).join('') + '</div>'
      ) : '');

    document.getElementById('topikDiagReset').addEventListener('click', function () {
      diagState = {};
      renderDiagnostic();
    });
  }

  function pad(n) { return n < 10 ? '0' + n : '' + n; }

  /* Error notebook */
  function renderErrors() {
    var el = document.getElementById('topikErrors');
    var errors = state.errors || [];

    if (!errors.length) {
      el.innerHTML = '<div class="topik-error-empty"><div class="topik-error-empty__icon">🎉</div><div class="topik-card__text">Chưa có câu sai nào! Tiếp tục học tập nhé.</div></div>';
      return;
    }

    var html = '<div class="topik-card topik-card--red"><div class="topik-card__title">📓 Sổ tay lỗi (' + errors.length + ' câu)</div><div class="topik-card__text">Các câu trả lời sai được lưu lại để ôn tập. Click "Xóa" để loại bỏ câu đã hiểu.</div></div>';
    html += '<div class="topik-error-list">';

    errors.slice().reverse().forEach(function (e, i) {
      html += '<div class="topik-error-item">' +
        '<div class="topik-error-item__meta">' + (e.type || '') + ' — ' + (e.id || '') + '</div>' +
        '<div class="topik-error-item__q">' + (e.question || '') + '</div>' +
        '<div class="topik-error-item__your">✗ Bạn chọn: ' + (e.yourAnswer || '') + '</div>' +
        '<div class="topik-error-item__correct">✓ Đáp án: ' + (e.correctAnswer || '') + '</div>' +
        (e.explanation ? '<div class="topik-error-item__explain">' + e.explanation + '</div>' : '') +
        '<button class="topik-btn topik-btn--outline topik-btn--sm topik-error-del" data-i="' + (errors.length - 1 - i) + '" style="margin-top:.5rem">Xóa</button>' +
      '</div>';
    });

    html += '</div>';
    if (errors.length > 0) {
      html += '<button class="topik-btn topik-btn--outline topik-btn--sm" id="topikErrorClearAll" style="margin-top:.75rem">Xóa tất cả</button>';
    }

    el.innerHTML = html;

    el.querySelectorAll('.topik-error-del').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var i = parseInt(btn.getAttribute('data-i'));
        state.errors.splice(i, 1);
        saveState();
        renderErrors();
      });
    });

    var clearBtn = document.getElementById('topikErrorClearAll');
    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        state.errors = [];
        saveState();
        renderErrors();
      });
    }
  }

  /* 30-Day Plan */
  function renderPlan() {
    var el = document.getElementById('topikPlan');
    var plan = generate30DayPlan();
    var checked = state.planChecked || [];
    var done = checked.filter(function (c) { return c; }).length;

    var html = '<div class="topik-plan-header">' +
      '<div class="topik-plan-header__title">📅 Kế hoạch 30 ngày — ' + done + '/30</div>' +
      '<div class="topik-plan-header__desc">Lộ trình cá nhân hóa dựa trên điểm hiện tại. Đánh dấu hoàn thành mỗi ngày.</div>' +
      '<div class="topik-progress-bar" style="max-width:400px;margin:.75rem auto 0"><div class="topik-progress-bar__fill" style="width:' + Math.round((done / 30) * 100) + '%"></div></div>' +
    '</div>';

    html += '<div class="topik-plan-timeline">';
    plan.forEach(function (day, i) {
      var isDone = checked[i] || false;
      html += '<div class="topik-plan-day' + (isDone ? ' is-done' : '') + '">' +
        '<div style="display:flex;flex-direction:column;align-items:center;gap:2px">' +
          '<div class="topik-plan-day__num">' + (i + 1) + '</div>' +
          '<button class="topik-plan-day__check topik-plan-check" data-i="' + i + '" aria-label="Day ' + (i + 1) + '">' + (isDone ? '✓' : '') + '</button>' +
        '</div>' +
        '<div class="topik-plan-day__content"><strong>' + day.title + '</strong>' + day.desc + '</div>' +
      '</div>';
    });
    html += '</div>';

    el.innerHTML = html;

    el.querySelectorAll('.topik-plan-check').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var i = parseInt(btn.getAttribute('data-i'));
        state.planChecked[i] = !state.planChecked[i];
        saveState();
        renderPlan();
      });
    });
  }

  function generate30DayPlan() {
    var plan = [];
    var li = state.listening.score || 0;
    var re = state.reading.score || 0;
    var wr = state.writing.score || 0;
    var weak = li < 85 ? 'listening' : (re < 85 ? 'reading' : 'writing');
    var mid = li < 85 || re < 85 ? 14 : 10;

    for (var i = 0; i < 30; i++) {
      var day = i + 1;
      var phase = day <= 10 ? 'Nền tảng' : (day <= 20 ? 'Tăng tốc' : 'Tổng lực');
      var focus = '';
      var task = '';

      if (day <= 10) {
        if (day % 3 === 1) { focus = 'Từ vựng'; task = 'Học 10 từ học thuật + 5 connector. Làm flashcards.'; }
        else if (day % 3 === 2) { focus = 'Nghe'; task = 'Luyện 3-5 câu listening. Ghi chú từ khóa. Nghe lại script.'; }
        else { focus = 'Đọc'; task = 'Luyện 3-5 câu reading. Skimming + scanning. Phân tích đáp án.'; }
      } else if (day <= 20) {
        if (day % 3 === 1) { focus = 'Viết'; task = 'Luyện 1 đề viết (Q51-52). Tập trung ngữ pháp + từ nối.'; }
        else if (day % 3 === 2) { focus = 'Nghe + Đọc'; task = 'Luyện 5 câu nghe + 5 câu đọc. Canh thời gian.'; }
        else { focus = 'Viết'; task = 'Luyện 1 đề Q53-Q54. Dàn ý + luận điểm + kết luận.'; }
      } else {
        if (day % 2 === 1) { focus = 'Thi thử'; task = 'Mock test 10 câu (5 nghe + 5 đọc). Giới hạn 15 phút.'; }
        else { focus = 'Sửa lỗi'; task = 'Xem sổ tay lỗi. Ôn lại câu sai. Viết 1 đoạn văn ngắn.'; }
      }

      var desc = '<span style="font-size:.78rem;color:var(--topik-muted);display:block;margin-top:.15rem">Giai đoạn ' + phase + ' · Trọng tâm: ' + focus + '</span>' +
        '<span style="font-size:.82rem">' + task + '</span>';

      plan.push({
        title: 'Ngày ' + day + ' — ' + focus,
        desc: desc
      });
    }
    return plan;
  }

  /* Init */
  function init() {
    loadState();

    fetch(DATA_URL)
      .then(function (r) { return r.json(); })
      .then(function (d) {
        data = d;
        initNav();
        renderDashboard();
      })
      .catch(function (err) {
        console.error('TOPIK: Failed to load data', err);
        document.getElementById('topikDashboard').innerHTML = '<div class="topik-card topik-card--red"><div class="topik-card__title">Lỗi tải dữ liệu</div><div class="topik-card__text">Không thể tải dữ liệu TOPIK. Vui lòng tải lại trang sau.</div></div>';
      });
  }

  if (document.getElementById('topikApp')) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  }
})();
