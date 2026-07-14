(function () {
  'use strict';

  var GITHUB_RAW = 'https://raw.githubusercontent.com/Banhang-Chogao/reviewchanthat/main/data/movie-history.json';
  var API_BASE = '';

  var state = {
    movies: [],
    filtered: [],
    weekOffset: 0,
    selectedDate: '',
    editingId: null
  };

  /* ─── Init ─────────────────────────────────────────── */

  function init() {
    var app = document.getElementById('mhApp');
    if (!app) return;
    API_BASE = app.getAttribute('data-api') || '';

    hideGate();
    loadMovies();
  }

  function hideGate() {
    var gate = document.getElementById('mhGate');
    if (gate) gate.style.display = 'none';
    var content = document.getElementById('mhAppContent');
    if (content) content.style.display = '';
  }

  /* ─── Data Loading ─────────────────────────────────── */

  function loadMovies() {
    showLoading(true);
    fetch(GITHUB_RAW)
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to load: ' + res.status);
        return res.json();
      })
      .then(function (data) {
        state.movies = data && Array.isArray(data.movies) ? data.movies : [];
        render();
      })
      .catch(function (err) {
        console.error('MovieHistory load error:', err);
        state.movies = [];
        render();
        showToast('Could not load movies. Using local data.', 'warning');
      })
      .finally(function () {
        showLoading(false);
      });
  }

  /* ─── Render ───────────────────────────────────────── */

  function render() {
    applyFilterAndSearch();
    renderCalendar();
    renderMovieList();
    updateWeekLabel();
  }

  function applyFilterAndSearch() {
    var filter = document.getElementById('mhFilter');
    var search = document.getElementById('mhSearch');
    var f = filter ? filter.value : 'all';
    var q = search ? (search.value || '').toLowerCase().trim() : '';

    state.filtered = state.movies.filter(function (m) {
      if (f !== 'all' && m.status !== f) return false;
      if (q && m.title.toLowerCase().indexOf(q) === -1) return false;
      return true;
    });

    state.filtered.sort(function (a, b) {
      return (b.releaseDate || '').localeCompare(a.releaseDate || '');
    });
  }

  /* ─── Calendar ─────────────────────────────────────── */

  function getMonday(date) {
    var d = new Date(date);
    var day = d.getDay();
    var diff = d.getDate() - day + (day === 0 ? -6 : 1);
    d.setDate(diff);
    d.setHours(0, 0, 0, 0);
    return d;
  }

  function renderCalendar() {
    var cal = document.getElementById('mhCalendar');
    if (!cal) return;

    var today = new Date();
    var ref = new Date(today);
    ref.setDate(ref.getDate() + state.weekOffset * 7);
    var monday = getMonday(ref);

    var headerCells = cal.querySelectorAll('.mh-calendar__header');
    var existingDays = cal.querySelectorAll('.mh-calendar__day, .mh-calendar__day--empty');
    existingDays.forEach(function (el) { el.remove(); });

    var movieMap = {};
    state.movies.forEach(function (m) {
      if (m.releaseDate) {
        if (!movieMap[m.releaseDate]) movieMap[m.releaseDate] = [];
        movieMap[m.releaseDate].push(m);
      }
    });

    for (var i = 0; i < 7; i++) {
      var dayDate = new Date(monday);
      dayDate.setDate(monday.getDate() + i);
      var dateStr = formatDate(dayDate);
      var dayNum = dayDate.getDate();
      var monthNum = dayDate.getMonth() + 1;
      var yearNum = dayDate.getFullYear();
      var isToday = dateStr === formatDate(today);
      var hasMovie = movieMap[dateStr] && movieMap[dateStr].length > 0;
      var isSelected = dateStr === state.selectedDate;

      var dayEl = document.createElement('div');
      dayEl.className = 'mh-calendar__day';
      if (isToday) dayEl.classList.add('mh-calendar__day--today');
      if (hasMovie) dayEl.classList.add('mh-calendar__day--has-movie');
      if (isSelected) dayEl.classList.add('mh-calendar__day--selected');
      dayEl.setAttribute('data-date', dateStr);

      if (hasMovie) {
        var emojiSpan = document.createElement('span');
        emojiSpan.className = 'mh-calendar__emoji';
        emojiSpan.textContent = movieMap[dateStr].length === 1 ? '🎬' : '🎬🎬';
        dayEl.appendChild(emojiSpan);
      }

      var dateSpan = document.createElement('span');
      dateSpan.className = 'mh-calendar__date';
      dateSpan.textContent = dayNum + '/' + monthNum;
      dayEl.appendChild(dateSpan);

      dayEl.addEventListener('click', function (dateStr) {
        return function () {
          state.selectedDate = state.selectedDate === dateStr ? '' : dateStr;
          renderCalendar();
          applyFilterAndSearch();
          renderMovieList();
        };
      }(dateStr));

      cal.appendChild(dayEl);
    }
  }

  function updateWeekLabel() {
    var label = document.getElementById('mhWeekLabel');
    if (!label) return;
    var today = new Date();
    var ref = new Date(today);
    ref.setDate(ref.getDate() + state.weekOffset * 7);
    var monday = getMonday(ref);
    var sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);

    var weekNum = getWeekNumber(monday);
    var year = monday.getFullYear();
    var monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'];
    label.textContent = 'Week ' + weekNum + ' (' + monthNames[monday.getMonth()] + ' ' + year + ')';
  }

  function getWeekNumber(d) {
    var copy = new Date(d);
    copy.setHours(0, 0, 0, 0);
    copy.setDate(copy.getDate() + 3 - (copy.getDay() + 6) % 7);
    var week1 = new Date(copy.getFullYear(), 0, 4);
    return 1 + Math.round(((copy - week1) / 86400000 - 3 + (week1.getDay() + 6) % 7) / 7);
  }

  function formatDate(date) {
    var y = date.getFullYear();
    var m = String(date.getMonth() + 1).padStart(2, '0');
    var d = String(date.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + d;
  }

  /* ─── Movie List ───────────────────────────────────── */

  function renderMovieList() {
    var list = document.getElementById('mhMovieList');
    if (!list) return;

    var source = state.selectedDate
      ? state.movies.filter(function (m) { return m.releaseDate === state.selectedDate; })
      : state.filtered;

    list.innerHTML = '';

    if (source.length === 0) {
      list.appendChild(createEmptyState());
      return;
    }

    source.forEach(function (movie) {
      list.appendChild(createMovieCard(movie));
    });
  }

  function createEmptyState() {
    var div = document.createElement('div');
    div.className = 'mh-empty';
    var icon = document.createElement('div');
    icon.className = 'mh-empty__icon';
    icon.textContent = '🍿';
    div.appendChild(icon);
    var text = document.createElement('p');
    text.className = 'mh-empty__text';
    text.textContent = 'No movies found';
    div.appendChild(text);
    var sub = document.createElement('p');
    sub.className = 'mh-empty__sub';
    sub.textContent = 'Add your first movie to get started!';
    div.appendChild(sub);
    return div;
  }

  function createMovieCard(movie) {
    var card = document.createElement('div');
    card.className = 'mh-movie-card';

    /* Top */
    var top = document.createElement('div');
    top.className = 'mh-movie-card__top';

    /* Poster */
    var poster = document.createElement('div');
    poster.className = 'mh-movie-card__poster';
    if (movie.posterUrl) {
      var img = document.createElement('img');
      img.className = 'mh-movie-card__poster';
      img.src = movie.posterUrl;
      img.alt = movie.title + ' poster';
      img.loading = 'lazy';
      img.onerror = function () {
        this.style.display = 'none';
        this.parentNode.classList.add('mh-movie-card__poster--empty');
        this.parentNode.textContent = '🎬';
      };
      poster = img;
    } else {
      poster.classList.add('mh-movie-card__poster--empty');
      poster.textContent = '🎬';
    }

    /* Info */
    var info = document.createElement('div');
    info.className = 'mh-movie-card__info';

    var title = document.createElement('h3');
    title.className = 'mh-movie-card__title';
    title.textContent = movie.title;
    info.appendChild(title);

    var meta = document.createElement('div');
    meta.className = 'mh-movie-card__meta';

    if (movie.releaseDate) {
      var dateSpan = document.createElement('span');
      dateSpan.textContent = movie.releaseDate;
      meta.appendChild(dateSpan);
    }

    if (movie.duration) {
      var durSpan = document.createElement('span');
      durSpan.textContent = movie.duration + ' min';
      meta.appendChild(durSpan);
    }

    if (movie.special && movie.special.length > 0) {
      var specials = document.createElement('div');
      specials.className = 'mh-specials';
      movie.special.forEach(function (s) {
        var tag = document.createElement('span');
        tag.className = 'mh-special';
        tag.textContent = s;
        specials.appendChild(tag);
      });
      meta.appendChild(specials);
    }

    info.appendChild(meta);

    if (movie.summary) {
      var summary = document.createElement('p');
      summary.className = 'mh-movie-card__summary';
      summary.textContent = movie.summary;
      info.appendChild(summary);
    }

    top.appendChild(poster);
    top.appendChild(info);
    card.appendChild(top);

    /* Bottom */
    var bottom = document.createElement('div');
    bottom.className = 'mh-movie-card__bottom';

    var left = document.createElement('div');
    left.style.display = 'flex';
    left.style.alignItems = 'center';
    left.style.gap = '0.75rem';
    left.style.flexWrap = 'wrap';

    /* Status badge */
    var statusMap = {
      upcoming: { class: 'upcoming', label: 'Upcoming' },
      watching: { class: 'watching', label: 'Watching' },
      watched: { class: 'watched', label: 'Watched' }
    };
    var st = statusMap[movie.status] || statusMap.upcoming;
    var badge = document.createElement('span');
    badge.className = 'mh-movie-card__status mh-movie-card__status--' + st.class;
    badge.textContent = st.label;
    left.appendChild(badge);

    /* Rating */
    if (movie.rating) {
      var rating = document.createElement('span');
      rating.className = 'mh-movie-card__rating';
      rating.textContent = '★'.repeat(movie.rating) + '☆'.repeat(5 - movie.rating);
      left.appendChild(rating);
    }

    bottom.appendChild(left);

    /* Actions */
    var actions = document.createElement('div');
    actions.className = 'mh-movie-card__actions';

    var editBtn = document.createElement('button');
    editBtn.className = 'mh-movie-card__action';
    editBtn.textContent = 'Edit';
    editBtn.addEventListener('click', function (m) {
      return function () { openEditModal(m); };
    }(movie));

    var delBtn = document.createElement('button');
    delBtn.className = 'mh-movie-card__action mh-movie-card__action--danger';
    delBtn.textContent = 'Delete';
    delBtn.addEventListener('click', function (m) {
      return function () { deleteMovie(m); };
    }(movie));

    actions.appendChild(editBtn);
    actions.appendChild(delBtn);
    bottom.appendChild(actions);

    card.appendChild(bottom);
    return card;
  }

  /* ─── Modal ────────────────────────────────────────── */

  function openAddModal() {
    state.editingId = null;
    openModal({
      title: '',
      releaseDate: '',
      summary: '',
      duration: 120,
      special: [],
      status: 'upcoming',
      rating: 0,
      posterUrl: ''
    }, 'Add Movie');
  }

  function openEditModal(movie) {
    state.editingId = movie.id;
    openModal({
      title: movie.title || '',
      releaseDate: movie.releaseDate || '',
      summary: movie.summary || '',
      duration: movie.duration || 120,
      special: movie.special || [],
      status: movie.status || 'upcoming',
      rating: movie.rating || 0,
      posterUrl: movie.posterUrl || ''
    }, 'Edit Movie');
  }

  function openModal(data, modalTitle) {
    removeExistingModal();

    var overlay = document.createElement('div');
    overlay.className = 'mh-overlay';
    overlay.id = 'mhModalOverlay';

    var modal = document.createElement('div');
    modal.className = 'mh-modal';

    /* Header */
    var header = document.createElement('div');
    header.className = 'mh-modal__header';
    var hTitle = document.createElement('h2');
    hTitle.className = 'mh-modal__title';
    hTitle.textContent = modalTitle;
    header.appendChild(hTitle);
    var closeBtn = document.createElement('button');
    closeBtn.className = 'mh-modal__close';
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', removeExistingModal);
    header.appendChild(closeBtn);
    modal.appendChild(header);

    /* Form */
    var form = document.createElement('div');
    form.className = 'mh-form';

    /* Title */
    form.appendChild(createInputGroup('Movie Title', 'mhFormTitle', 'text', data.title, true));

    /* Release Date */
    form.appendChild(createInputGroup('Release Date', 'mhFormDate', 'date', data.releaseDate, false));

    /* Summary */
    var sumGroup = document.createElement('div');
    sumGroup.className = 'mh-form__group';
    var sumLabel = document.createElement('label');
    sumLabel.className = 'mh-form__label';
    sumLabel.textContent = 'Summary';
    sumLabel.htmlFor = 'mhFormSummary';
    sumGroup.appendChild(sumLabel);
    var sumText = document.createElement('textarea');
    sumText.id = 'mhFormSummary';
    sumText.className = 'mh-form__textarea';
    sumText.value = data.summary;
    sumGroup.appendChild(sumText);
    form.appendChild(sumGroup);

    /* Row: Duration + Poster */
    var row1 = document.createElement('div');
    row1.className = 'mh-form__row';
    row1.appendChild(createInputGroup('Duration (min)', 'mhFormDuration', 'number', data.duration, false));
    row1.appendChild(createInputGroup('Poster URL (optional)', 'mhFormPoster', 'url', data.posterUrl, false));
    form.appendChild(row1);

    /* Special Formats */
    var specGroup = document.createElement('div');
    specGroup.className = 'mh-form__group';
    var specLabel = document.createElement('label');
    specLabel.className = 'mh-form__label';
    specLabel.textContent = 'Special Formats';
    specGroup.appendChild(specLabel);
    var specWrap = document.createElement('div');
    specWrap.className = 'mh-form__specials';
    var formats = ['IMAX', '4DX', 'Dolby', '3D'];
    formats.forEach(function (fmt) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'mh-form__special';
      if (data.special.indexOf(fmt) !== -1) btn.classList.add('mh-form__special--active');
      btn.textContent = fmt;
      btn.addEventListener('click', function () {
        btn.classList.toggle('mh-form__special--active');
      });
      specWrap.appendChild(btn);
    });
    specGroup.appendChild(specWrap);
    form.appendChild(specGroup);

    /* Status */
    var statGroup = document.createElement('div');
    statGroup.className = 'mh-form__group';
    var statLabel = document.createElement('label');
    statLabel.className = 'mh-form__label';
    statLabel.textContent = 'Status';
    statGroup.appendChild(statLabel);
    var statWrap = document.createElement('div');
    statWrap.className = 'mh-form__status';
    var statuses = [
      { val: 'upcoming', label: 'Upcoming' },
      { val: 'watching', label: 'Watching' },
      { val: 'watched', label: 'Watched' }
    ];
    var activeStatus = data.status || 'upcoming';
    statuses.forEach(function (s) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'mh-form__status-option';
      if (s.val === activeStatus) btn.classList.add('mh-form__status-option--active');
      btn.textContent = s.label;
      btn.setAttribute('data-value', s.val);
      btn.addEventListener('click', function () {
        statWrap.querySelectorAll('.mh-form__status-option').forEach(function (el) {
          el.classList.remove('mh-form__status-option--active');
        });
        btn.classList.add('mh-form__status-option--active');
      });
      statWrap.appendChild(btn);
    });
    statGroup.appendChild(statWrap);
    form.appendChild(statGroup);

    /* Rating */
    var ratGroup = document.createElement('div');
    ratGroup.className = 'mh-form__group';
    var ratLabel = document.createElement('label');
    ratLabel.className = 'mh-form__label';
    ratLabel.textContent = 'Rating';
    ratGroup.appendChild(ratLabel);
    var stars = document.createElement('div');
    stars.className = 'mh-form__stars';
    var currentRating = data.rating || 0;
    for (var si = 1; si <= 5; si++) {
      var starEl = document.createElement('span');
      starEl.className = 'mh-form__star';
      if (si <= currentRating) starEl.classList.add('mh-form__star--active');
      starEl.textContent = '★';
      starEl.setAttribute('data-rating', si);
      starEl.addEventListener('click', function () {
        var val = parseInt(this.getAttribute('data-rating'), 10);
        stars.querySelectorAll('.mh-form__star').forEach(function (el) {
          var r = parseInt(el.getAttribute('data-rating'), 10);
          if (r <= val) el.classList.add('mh-form__star--active');
          else el.classList.remove('mh-form__star--active');
        });
      });
      stars.appendChild(starEl);
    }
    ratGroup.appendChild(stars);
    form.appendChild(ratGroup);

    /* Actions */
    var actGroup = document.createElement('div');
    actGroup.className = 'mh-form__actions';
    var cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'mh-btn mh-btn--subtle';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.addEventListener('click', removeExistingModal);
    actGroup.appendChild(cancelBtn);
    var saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'mh-btn mh-btn--primary';
    saveBtn.textContent = 'Save';
    saveBtn.addEventListener('click', function () {
      saveMovieFromModal();
    });
    actGroup.appendChild(saveBtn);
    form.appendChild(actGroup);

    modal.appendChild(form);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    /* Focus first input */
    setTimeout(function () {
      var firstInput = document.getElementById('mhFormTitle');
      if (firstInput) firstInput.focus();
    }, 100);
  }

  function removeExistingModal() {
    var existing = document.getElementById('mhModalOverlay');
    if (existing) existing.remove();
  }

  function createInputGroup(label, id, type, value, required) {
    var group = document.createElement('div');
    group.className = 'mh-form__group';

    var lbl = document.createElement('label');
    lbl.className = 'mh-form__label';
    lbl.textContent = label;
    lbl.htmlFor = id;
    group.appendChild(lbl);

    if (type === 'textarea') {
      var ta = document.createElement('textarea');
      ta.id = id;
      ta.className = 'mh-form__textarea';
      ta.value = value || '';
      if (required) ta.setAttribute('required', '');
      group.appendChild(ta);
    } else {
      var inp = document.createElement('input');
      inp.type = type;
      inp.id = id;
      inp.className = 'mh-form__input';
      inp.value = value || '';
      if (required) inp.setAttribute('required', '');
      group.appendChild(inp);
    }

    return group;
  }

  function getModalData() {
    var title = (document.getElementById('mhFormTitle') || {}).value || '';
    var releaseDate = (document.getElementById('mhFormDate') || {}).value || '';
    var summary = (document.getElementById('mhFormSummary') || {}).value || '';
    var duration = parseInt((document.getElementById('mhFormDuration') || {}).value, 10) || 0;
    var posterUrl = (document.getElementById('mhFormPoster') || {}).value || '';

    var special = [];
    var specBtns = document.querySelectorAll('.mh-form__special');
    specBtns.forEach(function (btn) {
      if (btn.classList.contains('mh-form__special--active')) {
        special.push(btn.textContent.trim());
      }
    });

    var status = 'upcoming';
    var statusBtns = document.querySelectorAll('.mh-form__status-option');
    statusBtns.forEach(function (btn) {
      if (btn.classList.contains('mh-form__status-option--active')) {
        status = btn.getAttribute('data-value') || 'upcoming';
      }
    });

    var rating = 0;
    var starEls = document.querySelectorAll('.mh-form__star--active');
    rating = starEls.length;

    return { title: title.trim(), releaseDate: releaseDate.trim(), summary: summary.trim(), duration: duration, special: special, status: status, rating: rating, posterUrl: posterUrl.trim() };
  }

  /* ─── Save Movie ───────────────────────────────────── */

  function saveMovieFromModal() {
    var data = getModalData();
    if (!data.title) {
      showToast('Movie title is required.', 'error');
      return;
    }

    var now = new Date().toISOString();
    var movies = state.movies.slice();

    if (state.editingId) {
      var idx = -1;
      for (var i = 0; i < movies.length; i++) {
        if (movies[i].id === state.editingId) { idx = i; break; }
      }
      if (idx !== -1) {
        movies[idx] = { id: state.editingId, title: data.title, releaseDate: data.releaseDate, summary: data.summary, duration: data.duration, special: data.special, status: data.status, rating: data.rating, posterUrl: data.posterUrl, createdAt: movies[idx].createdAt || now, updatedAt: now };
      }
    } else {
      movies.push({ id: generateId(), title: data.title, releaseDate: data.releaseDate, summary: data.summary, duration: data.duration, special: data.special, status: data.status, rating: data.rating, posterUrl: data.posterUrl, createdAt: now, updatedAt: now });
    }

    var commitMsg = state.editingId ? 'Update movie: ' + data.title : 'Add movie: ' + data.title;
    saveToGitHub(movies, commitMsg);
  }

  /* ─── Delete Movie ─────────────────────────────────── */

  function deleteMovie(movie) {
    if (!confirm('Delete "' + movie.title + '"? This cannot be undone.')) return;
    var movies = state.movies.filter(function (m) { return m.id !== movie.id; });
    saveToGitHub(movies, 'Delete movie: ' + movie.title);
  }

  /* ─── GitHub API ───────────────────────────────────── */

  function saveToGitHub(movies, commitMsg) {
    passcodeForApi(function (passcode) {
      if (!passcode) return;
      showLoading(true);

      var payload = { movies: movies, message: commitMsg, updatedAt: new Date().toISOString() };
      var apiUrl = API_BASE || '/api/movie-history';

      fetch(apiUrl, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + passcode
        },
        body: JSON.stringify(payload)
      })
        .then(function (res) {
          if (!res.ok) {
            return res.json().then(function (err) {
              throw new Error((err && err.message) || 'API error: ' + res.status);
            });
          }
          return res.json();
        })
        .then(function () {
          state.movies = movies;
          removeExistingModal();
          render();
          showToast(commitMsg + ' ✓', 'success');
        })
        .catch(function (err) {
          console.error('MovieHistory save error:', err);
          showToast('Save failed: ' + err.message, 'error');
        })
        .finally(function () {
          showLoading(false);
        });
    });
  }

  /* ─── Passcode for API ────────────────────────────── */

  function passcodeForApi(callback) {
    var code = prompt('Enter OTP to save changes:');
    if (code && code.trim() === '0512') {
      callback(code.trim());
    } else {
      if (code) showToast('Incorrect OTP.', 'error');
      callback(null);
    }
  }

  /* ─── UI Helpers ───────────────────────────────────── */

  function showLoading(show) {
    var loading = document.getElementById('mhLoading');
    if (!loading) return;
    loading.style.display = show ? '' : 'none';
  }

  function showToast(msg, type) {
    var existing = document.getElementById('mhToast');
    if (existing) existing.remove();

    var toast = document.createElement('div');
    toast.id = 'mhToast';
    toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:2000;padding:12px 24px;border-radius:12px;font-size:0.88rem;font-weight:600;box-shadow:0 8px 24px rgba(0,0,0,0.15);transition:opacity 0.3s;max-width:90vw;text-align:center;';
    if (type === 'error') {
      toast.style.background = 'rgba(224,122,122,0.95)';
      toast.style.color = '#fff';
    } else if (type === 'warning') {
      toast.style.background = 'rgba(232,168,56,0.95)';
      toast.style.color = '#fff';
    } else {
      toast.style.background = 'rgba(0,167,160,0.95)';
      toast.style.color = '#fff';
    }
    toast.textContent = msg;
    document.body.appendChild(toast);

    setTimeout(function () {
      toast.style.opacity = '0';
      setTimeout(function () { if (toast.parentNode) toast.remove(); }, 300);
    }, 3000);
  }

  function generateId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
  }

  /* ─── Event Listeners ──────────────────────────────── */

  document.addEventListener('DOMContentLoaded', function () {
    init();

    /* Week nav */
    var prevBtn = document.getElementById('mhPrevWeek');
    var nextBtn = document.getElementById('mhNextWeek');
    if (prevBtn) prevBtn.addEventListener('click', function () { state.weekOffset -= 1; state.selectedDate = ''; render(); });
    if (nextBtn) nextBtn.addEventListener('click', function () { state.weekOffset += 1; state.selectedDate = ''; render(); });

    /* Add button */
    var addBtn = document.getElementById('mhAddBtn');
    if (addBtn) addBtn.addEventListener('click', openAddModal);

    /* Search / Filter */
    var search = document.getElementById('mhSearch');
    var filter = document.getElementById('mhFilter');
    function onSearchFilter() { render(); }
    if (search) search.addEventListener('input', onSearchFilter);
    if (filter) filter.addEventListener('change', onSearchFilter);

    /* Close modal on overlay click */
    document.addEventListener('click', function (e) {
      if (e.target.classList.contains('mh-overlay')) {
        removeExistingModal();
      }
    });

    /* Close modal on Escape */
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') removeExistingModal();
    });
  });

})();
