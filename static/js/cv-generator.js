(function () {
  'use strict';

  var STORAGE_KEY = 'cv_generator_draft';
  var ACCESS_CODE = '9898';
  var DEBOUNCE_DELAY = 300;

  var state = {
    fullName: '',
    email: '',
    phone: '',
    address: '',
    linkedin: '',
    website: '',
    objective: '',
    school: '',
    degree: '',
    eduStart: '',
    eduEnd: '',
    eduGpa: '',
    experiences: [{ company: '', position: '', start: '', end: '', desc: '' }],
    projects: [{ name: '', desc: '', tech: '', url: '' }],
    skills: [],
    certifications: '',
    languages: '',
    awards: '',
    activities: '',
    references: '',
    additional: ''
  };

  var debounceTimer = null;
  var gateEl = document.getElementById('cvGate');
  var appEl = document.getElementById('cvApp');
  var formEl = document.getElementById('cvForm');
  var previewEl = document.getElementById('cvPreview');
  var lockBtn = document.getElementById('cvLockBtn');
  var unlockBtn = document.getElementById('cvGateUnlock');
  var gateInput = document.getElementById('cvGateInput');
  var gateError = document.getElementById('cvGateError');

  /* ---- Gate ---- */
  function checkAccess() {
    try {
      return localStorage.getItem('cv_access') === ACCESS_CODE;
    } catch (e) { return false; }
  }

  function unlockApp() {
    gateEl.style.display = 'none';
    appEl.style.display = 'block';
    try { localStorage.setItem('cv_access', ACCESS_CODE); } catch (e) {}
  }

  if (checkAccess()) {
    unlockApp();
  }

  unlockBtn.addEventListener('click', function () {
    if (gateInput.value === ACCESS_CODE) {
      unlockApp();
    } else {
      gateError.textContent = 'Mã truy cập không đúng.';
    }
  });
  gateInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') unlockBtn.click();
  });

  lockBtn.addEventListener('click', function () {
    try { localStorage.removeItem('cv_access'); localStorage.removeItem(STORAGE_KEY); } catch (e) {}
    appEl.style.display = 'none';
    gateEl.style.display = 'flex';
    gateInput.value = '';
    gateError.textContent = '';
    resetState();
    renderPreview();
    updateKpis();
  });

  /* ---- State Management ---- */
  function getFormData() {
    state.fullName = document.getElementById('cvFullName').value;
    state.email = document.getElementById('cvEmail').value;
    state.phone = document.getElementById('cvPhone').value;
    state.address = document.getElementById('cvAddress').value;
    state.linkedin = document.getElementById('cvLinkedin').value;
    state.website = document.getElementById('cvWebsite').value;
    state.objective = document.getElementById('cvObjective').value;
    state.school = document.getElementById('cvSchool').value;
    state.degree = document.getElementById('cvDegree').value;
    state.eduStart = document.getElementById('cvEduStart').value;
    state.eduEnd = document.getElementById('cvEduEnd').value;
    state.eduGpa = document.getElementById('cvEduGpa').value;

    state.experiences = [];
    document.querySelectorAll('.cv-experience-item').forEach(function (item) {
      state.experiences.push({
        company: item.querySelector('.cv-exp-company').value,
        position: item.querySelector('.cv-exp-position').value,
        start: item.querySelector('.cv-exp-start').value,
        end: item.querySelector('.cv-exp-end').value,
        desc: item.querySelector('.cv-exp-desc').value
      });
    });

    state.projects = [];
    document.querySelectorAll('.cv-project-item').forEach(function (item) {
      state.projects.push({
        name: item.querySelector('.cv-proj-name').value,
        desc: item.querySelector('.cv-proj-desc').value,
        tech: item.querySelector('.cv-proj-tech').value,
        url: item.querySelector('.cv-proj-url').value
      });
    });

    var skillsVal = document.getElementById('cvSkills').value;
    state.skills = skillsVal.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    state.certifications = document.getElementById('cvCerts').value;
    state.languages = document.getElementById('cvLanguages').value;
    state.awards = document.getElementById('cvAwards').value;
    state.activities = document.getElementById('cvActivities').value;
    state.references = document.getElementById('cvReferences').value;
    state.additional = document.getElementById('cvAdditional').value;
  }

  function saveToStorage() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {}
  }

  function restoreFromStorage() {
    try {
      var data = localStorage.getItem(STORAGE_KEY);
      if (data) {
        var parsed = JSON.parse(data);
        Object.keys(parsed).forEach(function (k) {
          if (k in state) state[k] = parsed[k];
        });
        applyStateToForm();
        return true;
      }
    } catch (e) {}
    return false;
  }

  function applyStateToForm() {
    setField('cvFullName', state.fullName);
    setField('cvEmail', state.email);
    setField('cvPhone', state.phone);
    setField('cvAddress', state.address);
    setField('cvLinkedin', state.linkedin);
    setField('cvWebsite', state.website);
    setField('cvObjective', state.objective);
    setField('cvSchool', state.school);
    setField('cvDegree', state.degree);
    setField('cvEduStart', state.eduStart);
    setField('cvEduEnd', state.eduEnd);
    setField('cvEduGpa', state.eduGpa);

    renderExperienceItems();
    renderProjectItems();

    setField('cvSkills', state.skills.join(', '));
    renderSkillsTags();
    setField('cvCerts', state.certifications);
    setField('cvLanguages', state.languages);
    setField('cvAwards', state.awards);
    setField('cvActivities', state.activities);
    setField('cvReferences', state.references);
    setField('cvAdditional', state.additional);
  }

  function setField(id, val) {
    var el = document.getElementById(id);
    if (el) el.value = val || '';
  }

  function resetState() {
    state = {
      fullName: '', email: '', phone: '', address: '', linkedin: '', website: '',
      objective: '', school: '', degree: '', eduStart: '', eduEnd: '', eduGpa: '',
      experiences: [{ company: '', position: '', start: '', end: '', desc: '' }],
      projects: [{ name: '', desc: '', tech: '', url: '' }],
      skills: [], certifications: '', languages: '', awards: '', activities: '',
      references: '', additional: ''
    };
    applyStateToForm();
    try { localStorage.removeItem(STORAGE_KEY); } catch (e) {}
  }

  /* ---- Dynamic Items ---- */
  function renderExperienceItems() {
    var list = document.getElementById('cvExperienceList');
    list.innerHTML = '';
    state.experiences.forEach(function (exp, i) {
      var div = document.createElement('div');
      div.className = 'cv-experience-item';
      div.dataset.index = i;
      div.innerHTML =
        '<div class="cv-field"><label class="cv-field__label">Company <span class="cv-required">*</span></label><input type="text" class="cv-field__input cv-exp-company" required placeholder="Company name" value="' + esc(exp.company) + '"></div>' +
        '<div class="cv-field"><label class="cv-field__label">Position <span class="cv-required">*</span></label><input type="text" class="cv-field__input cv-exp-position" required placeholder="Job title" value="' + esc(exp.position) + '"></div>' +
        '<div class="cv-field-row"><div class="cv-field"><label class="cv-field__label">Start Date</label><input type="text" class="cv-field__input cv-exp-start" placeholder="Jan 2020" value="' + esc(exp.start) + '"></div>' +
        '<div class="cv-field"><label class="cv-field__label">End Date</label><input type="text" class="cv-field__input cv-exp-end" placeholder="Present" value="' + esc(exp.end) + '"></div></div>' +
        '<div class="cv-field"><label class="cv-field__label">Description <span class="cv-required">*</span></label><textarea class="cv-field__textarea cv-exp-desc" rows="3" required placeholder="Describe your responsibilities and achievements...">' + esc(exp.desc) + '</textarea></div>' +
        '<button type="button" class="cv-field__remove cv-exp-remove" title="Remove experience">Remove</button>';
      list.appendChild(div);
    });
    bindDynamicEvents();
  }

  function renderProjectItems() {
    var list = document.getElementById('cvProjectsList');
    list.innerHTML = '';
    state.projects.forEach(function (proj, i) {
      var div = document.createElement('div');
      div.className = 'cv-project-item';
      div.dataset.index = i;
      div.innerHTML =
        '<div class="cv-field"><label class="cv-field__label">Project Name</label><input type="text" class="cv-field__input cv-proj-name" placeholder="Project name" value="' + esc(proj.name) + '"></div>' +
        '<div class="cv-field"><label class="cv-field__label">Description</label><textarea class="cv-field__textarea cv-proj-desc" rows="2" placeholder="Brief description and your role...">' + esc(proj.desc) + '</textarea></div>' +
        '<div class="cv-field"><label class="cv-field__label">Technologies</label><input type="text" class="cv-field__input cv-proj-tech" placeholder="React, Node.js, PostgreSQL" value="' + esc(proj.tech) + '"></div>' +
        '<div class="cv-field"><label class="cv-field__label">URL</label><input type="url" class="cv-field__input cv-proj-url" placeholder="https://github.com/..." value="' + esc(proj.url) + '"></div>' +
        '<button type="button" class="cv-field__remove cv-proj-remove" title="Remove project">Remove</button>';
      list.appendChild(div);
    });
    bindDynamicEvents();
  }

  function esc(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function bindDynamicEvents() {
    document.querySelectorAll('.cv-exp-remove').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var items = document.querySelectorAll('.cv-experience-item');
        if (items.length <= 1) return;
        this.closest('.cv-experience-item').remove();
        onFormChange();
      });
    });
    document.querySelectorAll('.cv-proj-remove').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var items = document.querySelectorAll('.cv-project-item');
        if (items.length <= 1) return;
        this.closest('.cv-project-item').remove();
        onFormChange();
      });
    });
    document.querySelectorAll('.cv-experience-item input, .cv-experience-item textarea, .cv-project-item input, .cv-project-item textarea').forEach(function (el) {
      el.addEventListener('input', onFormChange);
    });
  }

  document.getElementById('cvAddExperience').addEventListener('click', function () {
    state.experiences.push({ company: '', position: '', start: '', end: '', desc: '' });
    renderExperienceItems();
    onFormChange();
  });
  document.getElementById('cvAddProject').addEventListener('click', function () {
    state.projects.push({ name: '', desc: '', tech: '', url: '' });
    renderProjectItems();
    onFormChange();
  });

  /* ---- Form Change Handler ---- */
  function onFormChange() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function () {
      getFormData();
      saveToStorage();
      renderPreview();
      updateKpis();
      renderSkillsTags();
      runAtsCheck();
    }, DEBOUNCE_DELAY);
  }

  formEl.addEventListener('input', onFormChange);
  formEl.addEventListener('change', onFormChange);

  /* ---- Skills Tags ---- */
  function renderSkillsTags() {
    var container = document.getElementById('cvSkillsTags');
    var skillsVal = document.getElementById('cvSkills').value;
    var skills = skillsVal.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    container.innerHTML = skills.map(function (s) { return '<span class="cv-skills-tag">' + esc(s) + '</span>'; }).join('');
  }

  /* ---- Preview Renderer ---- */
  function renderPreview() {
    getFormData();
    var isDark = document.documentElement.classList.contains('dark-mode');
    var html = '<div class="cv-doc' + (isDark ? ' cv-doc--dark' : '') + '">';
    html += '<div class="cv-doc__header">';
    html += '  <div class="cv-doc__header-main">';
    html += '    <h1 class="cv-doc__name">' + esc(state.fullName || 'Your Name') + '</h1>';
    html += '    <p class="cv-doc__title">' + esc(state.objective ? state.objective.split('.')[0] : 'Professional') + '</p>';
    html += '    <div class="cv-doc__contact">';
    if (state.email) html += '<span>' + esc(state.email) + '</span>';
    if (state.phone) html += '<span>' + esc(state.phone) + '</span>';
    if (state.address) html += '<span>' + esc(state.address) + '</span>';
    if (state.linkedin) html += '<a href="' + esc(state.linkedin) + '" target="_blank">LinkedIn</a>';
    if (state.website) html += '<a href="' + esc(state.website) + '" target="_blank">Portfolio</a>';
    html += '    </div>';
    html += '  </div>';
    html += '  <div class="cv-doc__photo-frame">Attach<br>Passport<br>Photo</div>';
    html += '</div>';

    if (state.objective) {
      html += '<div class="cv-doc__section">';
      html += '  <h2 class="cv-doc__section-title">Career Objective</h2>';
      html += '  <p class="cv-doc__objective">' + esc(state.objective) + '</p>';
      html += '</div>';
    }

    html += renderEducationSection();
    html += renderExperienceSection();
    html += renderProjectSection();

    if (state.skills.length) {
      html += '<div class="cv-doc__section">';
      html += '  <h2 class="cv-doc__section-title">Skills</h2>';
      html += '  <div class="cv-doc__skills">';
      state.skills.forEach(function (s) { html += '    <span class="cv-doc__skill">' + esc(s) + '</span>'; });
      html += '  </div>';
      html += '</div>';
    }

    if (state.certifications) {
      html += '<div class="cv-doc__section">';
      html += '  <h2 class="cv-doc__section-title">Certifications</h2>';
      html += '  <ul class="cv-doc__list">';
      state.certifications.split('\n').filter(Boolean).forEach(function (c) { html += '    <li>' + esc(c) + '</li>'; });
      html += '  </ul>';
      html += '</div>';
    }

    if (state.languages) {
      html += '<div class="cv-doc__section">';
      html += '  <h2 class="cv-doc__section-title">Languages</h2>';
      html += '  <ul class="cv-doc__list">';
      state.languages.split('\n').filter(Boolean).forEach(function (l) { html += '    <li>' + esc(l) + '</li>'; });
      html += '  </ul>';
      html += '</div>';
    }

    if (state.awards) {
      html += '<div class="cv-doc__section">';
      html += '  <h2 class="cv-doc__section-title">Awards</h2>';
      html += '  <ul class="cv-doc__list">';
      state.awards.split('\n').filter(Boolean).forEach(function (a) { html += '    <li>' + esc(a) + '</li>'; });
      html += '  </ul>';
      html += '</div>';
    }

    if (state.activities) {
      html += '<div class="cv-doc__section">';
      html += '  <h2 class="cv-doc__section-title">Activities</h2>';
      html += '  <ul class="cv-doc__list">';
      state.activities.split('\n').filter(Boolean).forEach(function (a) { html += '    <li>' + esc(a) + '</li>'; });
      html += '  </ul>';
      html += '</div>';
    }

    if (state.references) {
      html += '<div class="cv-doc__section">';
      html += '  <h2 class="cv-doc__section-title">References</h2>';
      html += '  <p class="cv-doc__objective">' + esc(state.references) + '</p>';
      html += '</div>';
    }

    if (state.additional) {
      html += '<div class="cv-doc__section">';
      html += '  <h2 class="cv-doc__section-title">Additional Information</h2>';
      html += '  <p class="cv-doc__objective">' + esc(state.additional) + '</p>';
      html += '</div>';
    }

    html += '</div>';
    previewEl.innerHTML = html;
  }

  function renderEducationSection() {
    if (!state.school && !state.degree) return '';
    var html = '<div class="cv-doc__section">';
    html += '  <h2 class="cv-doc__section-title">Education</h2>';
    html += '  <div class="cv-doc__entry">';
    html += '    <div class="cv-doc__entry-header">';
    html += '      <div>';
    if (state.school) html += '        <h3 class="cv-doc__entry-title">' + esc(state.school) + '</h3>';
    if (state.degree) html += '        <p class="cv-doc__entry-sub">' + esc(state.degree) + '</p>';
    html += '      </div>';
    if (state.eduStart || state.eduEnd) {
      html += '      <span class="cv-doc__entry-date">' + esc(state.eduStart) + ' - ' + esc(state.eduEnd) + '</span>';
    }
    html += '    </div>';
    if (state.eduGpa) html += '    <p class="cv-doc__entry-desc">GPA: ' + esc(state.eduGpa) + '</p>';
    html += '  </div>';
    html += '</div>';
    return html;
  }

  function renderExperienceSection() {
    var valid = state.experiences.filter(function (e) { return e.company || e.position || e.desc; });
    if (!valid.length) return '';
    var html = '<div class="cv-doc__section">';
    html += '  <h2 class="cv-doc__section-title">Work Experience</h2>';
    valid.forEach(function (e) {
      if (!e.company && !e.position && !e.desc) return;
      html += '  <div class="cv-doc__entry">';
      html += '    <div class="cv-doc__entry-header">';
      html += '      <div>';
      if (e.position) html += '        <h3 class="cv-doc__entry-title">' + esc(e.position) + '</h3>';
      if (e.company) html += '        <p class="cv-doc__entry-sub">' + esc(e.company) + '</p>';
      html += '      </div>';
      if (e.start || e.end) html += '      <span class="cv-doc__entry-date">' + esc(e.start) + ' - ' + esc(e.end) + '</span>';
      html += '    </div>';
      if (e.desc) html += '    <p class="cv-doc__entry-desc">' + esc(e.desc) + '</p>';
      html += '  </div>';
    });
    html += '</div>';
    return html;
  }

  function renderProjectSection() {
    var valid = state.projects.filter(function (p) { return p.name || p.desc; });
    if (!valid.length) return '';
    var html = '<div class="cv-doc__section">';
    html += '  <h2 class="cv-doc__section-title">Projects</h2>';
    valid.forEach(function (p) {
      html += '  <div class="cv-doc__entry">';
      html += '    <div class="cv-doc__entry-header">';
      html += '      <div>';
      if (p.name) html += '        <h3 class="cv-doc__entry-title">' + esc(p.name) + '</h3>';
      html += '      </div>';
      if (p.url) html += '      <a class="cv-doc__entry-date" href="' + esc(p.url) + '" target="_blank">Link</a>';
      html += '    </div>';
      if (p.desc) html += '    <p class="cv-doc__entry-desc">' + esc(p.desc) + '</p>';
      if (p.tech) html += '    <p class="cv-doc__entry-desc" style="font-size:0.75rem;color:var(--color-primary,#00A7A0)">' + esc(p.tech) + '</p>';
      html += '  </div>';
    });
    html += '</div>';
    return html;
  }

  /* ---- KPI Updates ---- */
  function updateKpis() {
    getFormData();
    var required = [
      { key: 'fullName', val: state.fullName },
      { key: 'email', val: state.email },
      { key: 'phone', val: state.phone },
      { key: 'objective', val: state.objective },
      { key: 'school', val: state.school },
      { key: 'degree', val: state.degree }
    ];
    var filled = required.filter(function (f) { return f.val.trim(); }).length;
    var total = required.length;
    var completion = Math.round((filled / total) * 100);

    var validExperiences = state.experiences.filter(function (e) { return e.company && e.position && e.desc; }).length;
    var hasSkills = state.skills.length > 0;
    var atsScore = Math.min(100, Math.round(
      (completion * 0.4) +
      (hasSkills ? 20 : 0) +
      (validExperiences >= 1 ? 20 : 0) +
      (state.certifications ? 10 : 0) +
      (state.languages ? 10 : 0)
    ));

    var missing = total - filled;
    var recruiterScore = Math.min(100, Math.round(
      (completion * 0.25) +
      (validExperiences >= 2 ? 30 : validExperiences === 1 ? 15 : 0) +
      (hasSkills ? 20 : 0) +
      (state.linkedin ? 10 : 0) +
      (state.certifications ? 10 : 0) +
      (state.languages ? 5 : 0)
    ));

    document.getElementById('cvKpiCompletion').textContent = completion + '%';
    document.getElementById('cvKpiMissing').textContent = missing;
    document.getElementById('cvKpiAts').textContent = atsScore + '%';
    document.getElementById('cvKpiScore').textContent = recruiterScore;
    document.getElementById('cvKpiProgressFill').style.width = completion + '%';
  }

  /* ---- ATS Checker ---- */
  function runAtsCheck() {
    getFormData();
    var actionVerbs = ['achieved', 'improved', 'developed', 'managed', 'created', 'implemented', 'led', 'designed', 'built', 'delivered', 'increased', 'reduced', 'optimized', 'coordinated', 'established', 'generated', 'launched', 'negotiated', 'organized', 'performed', 'planned', 'produced', 'spearheaded', 'streamlined', 'strengthened', 'trained', 'transformed'];
    var keywordScore = 0;
    var formattingScore = 0;
    var verbsScore = 0;
    var lengthScore = 0;
    var balanceScore = 0;
    var educationScore = 0;
    var skillsScore = 0;

    var allText = Object.values(state).filter(function (v) { return typeof v === 'string'; }).join(' ').toLowerCase();
    var expTexts = state.experiences.map(function (e) { return (e.desc + ' ' + e.position).toLowerCase(); }).join(' ');
    var expWords = expTexts.split(/\s+/).filter(Boolean);

    var actionFound = actionVerbs.filter(function (v) { return expTexts.indexOf(v) >= 0; });
    verbsScore = Math.min(100, Math.round((actionFound.length / 6) * 100));

    var skillMatches = state.skills.filter(function (s) { return allText.indexOf(s.toLowerCase()) >= 0; });
    keywordScore = state.skills.length ? Math.min(100, Math.round((skillMatches.length / state.skills.length) * 100)) : 50;

    if (state.fullName && state.email && state.phone) formattingScore = 100;
    else if (state.fullName && state.email) formattingScore = 70;
    else formattingScore = 40;

    var hasSections = [state.objective, state.school, state.skills.length, state.experiences.some(function (e) { return e.desc; })].filter(Boolean).length;
    lengthScore = Math.min(100, hasSections * 25);

    var expCount = state.experiences.filter(function (e) { return e.desc; }).length;
    balanceScore = expCount >= 2 ? 100 : expCount === 1 ? 60 : 20;

    educationScore = state.school && state.degree ? 100 : state.school ? 60 : 20;

    skillsScore = state.skills.length >= 6 ? 100 : state.skills.length >= 3 ? 70 : state.skills.length ? 40 : 10;

    var overall = Math.round((keywordScore + formattingScore + verbsScore + lengthScore + balanceScore + educationScore + skillsScore) / 7);

    document.getElementById('cvAtsScoreNumber').textContent = overall;
    var circle = document.querySelector('.cv-ats-score__circle');
    if (circle) circle.style.background = 'conic-gradient(var(--color-primary,#00A7A0) ' + overall + '%, var(--color-border,#e0e0e0) ' + overall + '%)';

    setAtsBar('cvAtsKeywords', keywordScore);
    setAtsBar('cvAtsFormatting', formattingScore);
    setAtsBar('cvAtsVerbs', verbsScore);
    setAtsBar('cvAtsLength', lengthScore);
    setAtsBar('cvAtsBalance', balanceScore);
    setAtsBar('cvAtsEducation', educationScore);
    setAtsBar('cvAtsSkills', skillsScore);

    var suggestions = [];
    if (keywordScore < 70) suggestions.push('Include more skill-related keywords throughout your CV.');
    if (verbsScore < 60) suggestions.push('Use more action verbs like "achieved", "developed", "implemented".');
    if (balanceScore < 100) suggestions.push('Add more work experience entries with detailed descriptions.');
    if (skillsScore < 70) suggestions.push('List at least 6 relevant technical skills.');
    if (educationScore < 100) suggestions.push('Add your degree and school information.');
    if (formattingScore < 100) suggestions.push('Add your full name, email, and phone number for proper header.');

    var sugEl = document.getElementById('cvAtsSuggestions');
    if (suggestions.length) {
      sugEl.innerHTML = '<strong>Suggestions:</strong><ul>' + suggestions.map(function (s) { return '<li>' + s + '</li>'; }).join('') + '</ul>';
    } else {
      sugEl.innerHTML = '<p style="color:var(--color-primary,#00A7A0);font-weight:600;">Great! Your CV looks ATS-ready.</p>';
    }
  }

  function setAtsBar(id, score) {
    var el = document.getElementById(id);
    if (el) el.style.width = score + '%';
  }

  /* ---- AI Assistant ---- */
  var AI_PROMPTS = {
    'improve-objective': 'Rewrite this career objective to be more compelling and professional, highlighting key strengths and career goals: ',
    'improve-experience': 'Rewrite this work experience description to be more impactful, focusing on achievements and quantifiable results: ',
    'rewrite-bullets': 'Convert this text into concise, impactful bullet points suitable for a CV: ',
    'professional-tone': 'Rewrite this text to have a more professional and formal tone suitable for a CV: ',
    'shorter': 'Condense this text to be more concise while keeping key information, suitable for a CV: ',
    'more-impact': 'Rewrite this to be more impactful, using strong action verbs and quantifiable achievements: ',
    'grammar-check': 'Fix any grammar, spelling, or punctuation errors in this text: ',
    'ats-optimize': 'Optimize this text for ATS systems - include relevant keywords while keeping it natural: '
  };

  document.querySelectorAll('.cv-ai-btn[data-action]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var action = this.dataset.action;
      if (action === 'suggest-skills') {
        suggestSkills();
        return;
      }
      if (action === 'achievement-bullets') {
        generateAchievementBullets();
        return;
      }
      var prompt = AI_PROMPTS[action];
      if (!prompt) return;
      var targetText = window.prompt('Enter the text to process:');
      if (!targetText) return;
      var fullPrompt = prompt + targetText;
      callAi(fullPrompt, function (result) {
        showAiResult(result, action);
      });
    });
  });

  function suggestSkills() {
    var expText = state.experiences.map(function (e) { return e.desc + ' ' + e.position; }).join(' ');
    var prompt = 'Based on this work experience description, suggest 8-12 relevant technical and soft skills for a CV. Return only a comma-separated list: ' + expText;
    callAi(prompt, function (result) {
      document.getElementById('cvSkills').value = result;
      onFormChange();
    });
  }

  function generateAchievementBullets() {
    var expText = state.experiences.map(function (e) { return e.desc; }).filter(Boolean).join('. ');
    var prompt = 'Generate 3-5 achievement-oriented bullet points based on this experience, focusing on quantifiable results. Return each bullet on a new line starting with - : ' + (expText || 'Software development experience');
    callAi(prompt, function (result) {
      showAiResult(result, 'achievement-bullets');
    });
  }

  function callAi(prompt, callback) {
    var resultEl = document.getElementById('cvAiResult');
    var contentEl = document.getElementById('cvAiResultContent');
    resultEl.style.display = 'block';
    contentEl.textContent = 'Processing...';
    document.getElementById('cvAiApply').style.display = 'none';

    var aiEngine = window.CvAiEngine || window.TravelAiEngine;
    if (aiEngine && typeof aiEngine.generate === 'function') {
      aiEngine.generate(prompt).then(function (res) {
        contentEl.textContent = res || 'No result returned.';
        document.getElementById('cvAiApply').style.display = 'inline-block';
        if (callback) callback(res || '');
      }).catch(function (err) {
        contentEl.textContent = 'Error: ' + (err.message || err);
      });
    } else {
      setTimeout(function () {
        var fakeResult = 'Suggested improvement based on your input.\n\n' +
          '- Strengthened the description with more specific examples\n' +
          '- Improved clarity and professional tone\n' +
          '- Added quantifiable achievements where applicable\n\n' +
          'Note: AI engine not fully loaded. This is a mock response.';
        contentEl.textContent = fakeResult;
        document.getElementById('cvAiApply').style.display = 'inline-block';
        if (callback) callback(fakeResult);
      }, 500);
    }
  }

  function showAiResult(content, action) {
    var resultEl = document.getElementById('cvAiResult');
    var contentEl = document.getElementById('cvAiResultContent');
    resultEl.style.display = 'block';
    contentEl.textContent = content;
    document.getElementById('cvAiApply').style.display = 'inline-block';
  }

  /* ---- Export ---- */
  document.getElementById('cvGeneratePdf').addEventListener('click', function () {
    if (!validateForm()) return;
    exportCv('pdf');
  });
  document.getElementById('cvGenerateDocx').addEventListener('click', function () {
    if (!validateForm()) return;
    exportCv('docx');
  });
  document.getElementById('cvPrint').addEventListener('click', function () {
    window.print();
  });
  document.getElementById('cvReset').addEventListener('click', function () {
    if (confirm('Reset all fields? This will clear your current CV.')) {
      resetState();
      renderPreview();
      updateKpis();
      runAtsCheck();
    }
  });

  function validateForm() {
    var required = ['cvFullName', 'cvEmail', 'cvPhone', 'cvObjective', 'cvSchool', 'cvDegree'];
    var valid = true;
    required.forEach(function (id) {
      var el = document.getElementById(id);
      if (!el.value.trim()) {
        el.classList.add('cv-field--missing');
        valid = false;
      } else {
        el.classList.remove('cv-field--missing');
      }
    });
    if (!valid) {
      alert('Please fill in all required fields (marked with *).');
    }
    return valid;
  }

  function exportCv(format) {
    getFormData();
    var payload = {
      format: format,
      data: state,
      html: previewEl.innerHTML,
      name: state.fullName || 'CV'
    };

    var btn = format === 'pdf' ? document.getElementById('cvGeneratePdf') : document.getElementById('cvGenerateDocx');
    btn.textContent = 'Generating...';
    btn.disabled = true;

    fetch('/reviewchanthat/api/cv-export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (res) {
      if (!res.ok) throw new Error('Export failed');
      return res.blob();
    }).then(function (blob) {
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = state.fullName.replace(/\s+/g, '_') + '_CV.' + format;
      a.click();
      URL.revokeObjectURL(url);
    }).catch(function (err) {
      fallbackExport(format);
    }).finally(function () {
      btn.textContent = format === 'pdf' ? '📄 PDF' : '📝 DOCX';
      btn.disabled = false;
    });
  }

  function fallbackExport(format) {
    getFormData();
    var win = window.open('', '_blank');
    if (!win) {
      alert('Please allow popups for this site to export.');
      return;
    }
    var docHtml = '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>' + esc(state.fullName || 'CV') + '</title>';
    docHtml += '<style>';
    docHtml += 'body{font-family:"Inter","Be Vietnam Pro",-apple-system,sans-serif;max-width:210mm;margin:auto;padding:2rem;color:#222;line-height:1.5;font-size:10pt}';
    docHtml += '.header{display:flex;gap:1.5rem;margin-bottom:1rem;border-bottom:2px solid #00A7A0;padding-bottom:0.75rem}';
    docHtml += '.header-main{flex:1}';
    docHtml += '.name{font-size:1.4rem;font-weight:800;margin:0 0 0.15rem}';
    docHtml += '.title{font-size:0.95rem;color:#00A7A0;margin:0 0 0.35rem;font-weight:600}';
    docHtml += '.contact{display:flex;flex-wrap:wrap;gap:0.35rem 0.75rem;font-size:0.75rem;color:#555}';
    docHtml += '.photo{width:90px;height:120px;border:2px dashed #ccc;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:0.6rem;color:#999;flex-shrink:0;text-align:center}';
    docHtml += '.section{margin-bottom:0.75rem}';
    docHtml += '.section-title{font-size:0.85rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:#00A7A0;border-bottom:1px solid #e0e0e0;padding-bottom:0.2rem;margin:0 0 0.4rem}';
    docHtml += '.entry{margin-bottom:0.5rem}';
    docHtml += '.entry-header{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap}';
    docHtml += '.entry-title{font-weight:700;font-size:0.9rem;margin:0}';
    docHtml += '.entry-sub{font-weight:600;font-size:0.8rem;color:#00A7A0;margin:0}';
    docHtml += '.entry-date{font-size:0.75rem;color:#888}';
    docHtml += '.entry-desc{font-size:0.8rem;color:#444;margin:0.15rem 0 0}';
    docHtml += '.skills{display:flex;flex-wrap:wrap;gap:0.3rem}';
    docHtml += '.skill{background:#00A7A0;color:#fff;padding:0.15rem 0.5rem;border-radius:12px;font-size:0.7rem;font-weight:600}';
    docHtml += '.list{margin:0;padding-left:1rem;font-size:0.8rem}';
    docHtml += '@media print{body{padding:0}}';
    docHtml += '</style></head><body>';
    docHtml += '<div class="header"><div class="header-main">';
    docHtml += '<h1 class="name">' + esc(state.fullName) + '</h1>';
    docHtml += '<p class="title">' + esc(state.objective ? state.objective.split('.')[0] : 'Professional') + '</p>';
    docHtml += '<div class="contact">';
    if (state.email) docHtml += '<span>' + esc(state.email) + '</span>';
    if (state.phone) docHtml += '<span>' + esc(state.phone) + '</span>';
    if (state.address) docHtml += '<span>' + esc(state.address) + '</span>';
    docHtml += '</div></div>';
    docHtml += '<div class="photo">Attach<br>Passport<br>Photo</div></div>';

    if (state.objective) {
      docHtml += '<div class="section"><h2 class="section-title">Career Objective</h2><p>' + esc(state.objective) + '</p></div>';
    }
    if (state.school || state.degree) {
      docHtml += '<div class="section"><h2 class="section-title">Education</h2><div class="entry"><div class="entry-header"><div>';
      if (state.school) docHtml += '<h3 class="entry-title">' + esc(state.school) + '</h3>';
      if (state.degree) docHtml += '<p class="entry-sub">' + esc(state.degree) + '</p>';
      docHtml += '</div>';
      if (state.eduStart || state.eduEnd) docHtml += '<span class="entry-date">' + esc(state.eduStart) + ' - ' + esc(state.eduEnd) + '</span>';
      docHtml += '</div>';
      if (state.eduGpa) docHtml += '<p class="entry-desc">GPA: ' + esc(state.eduGpa) + '</p>';
      docHtml += '</div></div>';
    }

    var exps = state.experiences.filter(function (e) { return e.company || e.position; });
    if (exps.length) {
      docHtml += '<div class="section"><h2 class="section-title">Work Experience</h2>';
      exps.forEach(function (e) {
        docHtml += '<div class="entry"><div class="entry-header"><div>';
        if (e.position) docHtml += '<h3 class="entry-title">' + esc(e.position) + '</h3>';
        if (e.company) docHtml += '<p class="entry-sub">' + esc(e.company) + '</p>';
        docHtml += '</div>';
        if (e.start || e.end) docHtml += '<span class="entry-date">' + esc(e.start) + ' - ' + esc(e.end) + '</span>';
        docHtml += '</div>';
        if (e.desc) docHtml += '<p class="entry-desc">' + esc(e.desc) + '</p>';
        docHtml += '</div>';
      });
      docHtml += '</div>';
    }

    if (state.skills.length) {
      docHtml += '<div class="section"><h2 class="section-title">Skills</h2><div class="skills">';
      state.skills.forEach(function (s) { docHtml += '<span class="skill">' + esc(s) + '</span>'; });
      docHtml += '</div></div>';
    }

    if (state.certifications) {
      docHtml += '<div class="section"><h2 class="section-title">Certifications</h2><ul class="list">';
      state.certifications.split('\n').filter(Boolean).forEach(function (c) { docHtml += '<li>' + esc(c) + '</li>'; });
      docHtml += '</ul></div>';
    }

    if (state.languages) {
      docHtml += '<div class="section"><h2 class="section-title">Languages</h2><ul class="list">';
      state.languages.split('\n').filter(Boolean).forEach(function (l) { docHtml += '<li>' + esc(l) + '</li>'; });
      docHtml += '</ul></div>';
    }

    docHtml += '</body></html>';
    win.document.write(docHtml);
    win.document.close();
    setTimeout(function () {
      if (format === 'pdf') {
        win.focus();
        win.print();
      }
    }, 500);
  }

  /* ---- Excel Import/Export ---- */
  var CV_SECTIONS = {
    'Personal Information': ['Full Name', 'Email', 'Phone', 'Address', 'LinkedIn', 'Website'],
    'Career Objective': ['Objective'],
    'Education': ['School / University', 'Degree', 'Start Year', 'End Year', 'GPA'],
    'Work Experience': ['Company', 'Position', 'Start Date', 'End Date', 'Description'],
    'Projects': ['Project Name', 'Description', 'Technologies', 'URL'],
    'Skills': ['Skills (comma separated)'],
    'Certifications': ['Certifications (one per line)'],
    'Languages': ['Languages (one per line)'],
    'Awards': ['Awards (one per line)'],
    'Activities': ['Activities / Volunteer (one per line)'],
    'References': ['References'],
    'Additional Information': ['Additional Info']
  };

  function getCvData() {
    getFormData();
    return {
      'Personal Information': [state.fullName, state.email, state.phone, state.address, state.linkedin, state.website],
      'Career Objective': [state.objective],
      'Education': state.experiences.length ? [state.school, state.degree, state.eduStart, state.eduEnd, state.eduGpa] : ['', '', '', '', ''],
      'Work Experience': state.experiences.map(function(e) { return [e.company, e.position, e.start, e.end, e.desc]; }),
      'Projects': state.projects.map(function(p) { return [p.name, p.desc, p.tech, p.url]; }),
      'Skills': [state.skills.join(', ')],
      'Certifications': [state.certifications],
      'Languages': [state.languages],
      'Awards': [state.awards],
      'Activities': [state.activities],
      'References': [state.references],
      'Additional Information': [state.additional]
    };
  }

  function downloadTemplate() {
    if (typeof XLSX === 'undefined') {
      alert('Excel library not ready. Please try again.');
      return;
    }
    var wb = XLSX.utils.book_new();
    var sheetNames = Object.keys(CV_SECTIONS);

    sheetNames.forEach(function(name) {
      var headers = CV_SECTIONS[name];
      var data = [];
      if (name === 'Work Experience') {
        data = [headers,
          ['Acme Corp', 'Software Engineer', 'Jan 2020', 'Present', 'Developed and maintained web applications using React and Node.js. Led a team of 3 developers.'],
          ['Startup XYZ', 'Junior Developer', 'Jun 2018', 'Dec 2019', 'Built RESTful APIs and contributed to front-end development.'],
          ['', '', '', '', '']];
      } else if (name === 'Projects') {
        data = [headers,
          ['E-commerce Platform', 'Built a full-stack e-commerce platform with payment integration.', 'React, Node.js, PostgreSQL, Stripe', 'https://github.com/example/ecommerce'],
          ['Mobile App', 'Developed a cross-platform mobile application for task management.', 'React Native, Firebase', ''],
          ['', '', '', '']];
      } else {
        data = [headers];
        if (name === 'Education') data.push(['University of Science', 'Bachelor of Computer Science', '2018', '2022', '3.5 / 4.0']);
        else if (name === 'Skills') data.push(['JavaScript, Python, React, Node.js, Docker, PostgreSQL']);
        else if (name === 'Certifications') data.push(['AWS Solutions Architect - 2024\nGoogle Cloud Professional - 2023']);
        else if (name === 'Languages') data.push(['Vietnamese - Native\nEnglish - Fluent\nJapanese - N3']);
        else if (name === 'Personal Information') data.push(['Nguyen Van A', 'nguyenvana@example.com', '+84 90 123 4567', 'Ho Chi Minh City, Vietnam', 'https://linkedin.com/in/...', 'https://...']);
        else if (name === 'Career Objective') data.push(['Experienced software engineer with 5+ years building scalable web applications...']);
        else data.push(['']);
      }

      var ws = XLSX.utils.aoa_to_sheet(data);

      var colWidths = headers.map(function(h) {
        return { wch: Math.max(h.length * 1.5, 18) };
      });
      ws['!cols'] = colWidths;

      ws['!rows'] = data.map(function(_, i) {
        if (i === 0) return { hpx: 30 };
        return { hpx: 20 };
      });

      XLSX.utils.book_append_sheet(wb, ws, name);
    });

    XLSX.writeFile(wb, 'CV_Template.xlsx');
  }

  function importExcel() {
    if (typeof XLSX === 'undefined') {
      alert('Excel library not ready. Please try again.');
      return;
    }
    var input = document.createElement('input');
    input.type = 'file';
    input.accept = '.xlsx';
    input.addEventListener('change', function(e) {
      var file = e.target.files[0];
      if (!file) return;
      if (file.size > 10 * 1024 * 1024) {
        alert('File too large. Maximum 10 MB.');
        return;
      }
      processExcelFile(file);
    });
    input.click();
  }

  function processExcelFile(file) {
    showProgress(10);
    var reader = new FileReader();
    reader.onload = function(ev) {
      try {
        showProgress(30);
        var data = new Uint8Array(ev.target.result);
        var wb = XLSX.read(data, { type: 'array' });
        showProgress(50);

        var errors = [];
        var imported = {};
        var summary = [];

        var sheetNames = wb.SheetNames;
        Object.keys(CV_SECTIONS).forEach(function(section) {
          var sheetName = sheetNames.filter(function(s) { return s.trim().toLowerCase() === section.toLowerCase(); })[0];
          if (!sheetName) {
            summary.push({ section: section, status: 'missing', msg: 'Worksheet not found' });
            return;
          }
          var ws = wb.Sheets[sheetName];
          var rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' });
          if (!rows || rows.length < 2) {
            summary.push({ section: section, status: 'empty', msg: 'No data rows' });
            return;
          }

          var headerRow = rows[0].map(function(h) { return String(h).trim(); });
          var expectedHeaders = CV_SECTIONS[section];
          var colMap = {};
          expectedHeaders.forEach(function(h, idx) {
            var norm = h.toLowerCase().replace(/[^a-z0-9]/g, '');
            var found = -1;
            headerRow.forEach(function(rh, ri) {
              if (rh.toLowerCase().replace(/[^a-z0-9]/g, '') === norm) found = ri;
            });
            colMap[idx] = found;
          });

          var dataRows = rows.slice(1).filter(function(row) {
            return row.some(function(cell) { return String(cell).trim(); });
          });

          if (dataRows.length === 0) {
            summary.push({ section: section, status: 'empty', msg: 'No data after filtering empty rows' });
            return;
          }

          if (section === 'Personal Information') {
            imported.fullName = getCell(dataRows[0], colMap[0]);
            imported.email = getCell(dataRows[0], colMap[1]);
            imported.phone = getCell(dataRows[0], colMap[2]);
            imported.address = getCell(dataRows[0], colMap[3]);
            imported.linkedin = getCell(dataRows[0], colMap[4]);
            imported.website = getCell(dataRows[0], colMap[5]);

            if (!imported.fullName) errors.push('Full Name is required');
            if (!imported.email) errors.push('Email is required');
            if (!imported.phone) errors.push('Phone is required');
            summary.push({ section: section, status: 'ok', msg: imported.fullName || 'Imported' });
          } else if (section === 'Career Objective') {
            imported.objective = getCell(dataRows[0], colMap[0]);
            summary.push({ section: section, status: 'ok', msg: 'Imported' });
          } else if (section === 'Education') {
            imported.school = getCell(dataRows[0], colMap[0]);
            imported.degree = getCell(dataRows[0], colMap[1]);
            imported.eduStart = getCell(dataRows[0], colMap[2]);
            imported.eduEnd = getCell(dataRows[0], colMap[3]);
            imported.eduGpa = getCell(dataRows[0], colMap[4]);
            summary.push({ section: section, status: 'ok', msg: imported.school || 'Imported' });
          } else if (section === 'Work Experience') {
            imported.experiences = dataRows.map(function(row) {
              return {
                company: getCell(row, colMap[0]),
                position: getCell(row, colMap[1]),
                start: getCell(row, colMap[2]),
                end: getCell(row, colMap[3]),
                desc: getCell(row, colMap[4])
              };
            }).filter(function(e) { return e.company || e.position; });
            if (!imported.experiences.length) imported.experiences = [{ company: '', position: '', start: '', end: '', desc: '' }];
            summary.push({ section: section, status: 'ok', msg: imported.experiences.length + ' entries' });
          } else if (section === 'Projects') {
            imported.projects = dataRows.map(function(row) {
              return {
                name: getCell(row, colMap[0]),
                desc: getCell(row, colMap[1]),
                tech: getCell(row, colMap[2]),
                url: getCell(row, colMap[3])
              };
            }).filter(function(p) { return p.name || p.desc; });
            if (!imported.projects.length) imported.projects = [{ name: '', desc: '', tech: '', url: '' }];
            summary.push({ section: section, status: 'ok', msg: imported.projects.length + ' entries' });
          } else if (section === 'Skills') {
            imported.skills = getCell(dataRows[0], colMap[0]).split(',').map(function(s) { return s.trim(); }).filter(Boolean);
            summary.push({ section: section, status: 'ok', msg: imported.skills.length + ' skills' });
          } else if (section === 'Certifications') {
            imported.certifications = getCell(dataRows[0], colMap[0]);
            summary.push({ section: section, status: 'ok', msg: 'Imported' });
          } else if (section === 'Languages') {
            imported.languages = getCell(dataRows[0], colMap[0]);
            summary.push({ section: section, status: 'ok', msg: 'Imported' });
          } else if (section === 'Awards') {
            imported.awards = getCell(dataRows[0], colMap[0]);
            summary.push({ section: section, status: 'ok', msg: 'Imported' });
          } else if (section === 'Activities') {
            imported.activities = getCell(dataRows[0], colMap[0]);
            summary.push({ section: section, status: 'ok', msg: 'Imported' });
          } else if (section === 'References') {
            imported.references = getCell(dataRows[0], colMap[0]);
            summary.push({ section: section, status: 'ok', msg: 'Imported' });
          } else if (section === 'Additional Information') {
            imported.additional = getCell(dataRows[0], colMap[0]);
            summary.push({ section: section, status: 'ok', msg: 'Imported' });
          }
        });

        showProgress(80);

        if (errors.length > 0) {
          showSummary(summary, errors);
          showProgress(0);
          return;
        }

        // Check merge mode
        var hasExisting = state.fullName || state.objective || state.school;
        if (hasExisting) {
          var mode = confirm('Your CV already has data. Click OK to Replace All, Cancel to choose Merge.');
          if (!mode) {
            // Merge: only overwrite fields present in Excel
            mergeData(imported);
          } else {
            // Replace
            replaceData(imported);
          }
        } else {
          replaceData(imported);
        }

        showProgress(100);
        showSummary(summary, []);
        applyStateToForm();
        onFormChange();
        showImportSuccess('CV imported successfully.' + (summary.filter(function(s) { return s.status === 'ok'; }).length) + '/' + Object.keys(CV_SECTIONS).length + ' sections loaded.');
      } catch (e) {
        showProgress(0);
        alert('Error reading Excel file: ' + e.message);
      }
    };
    reader.readAsArrayBuffer(file);
  }

  function getCell(row, colIdx) {
    if (colIdx < 0 || !row || !row[colIdx]) return '';
    return String(row[colIdx]).trim();
  }

  function replaceData(imported) {
    Object.keys(imported).forEach(function(k) {
      state[k] = imported[k];
    });
  }

  function mergeData(imported) {
    Object.keys(imported).forEach(function(k) {
      var val = imported[k];
      if (Array.isArray(val)) {
        if (val.length && (val[0].company || val[0].position || val[0].name)) {
          state[k] = val;
        }
      } else if (typeof val === 'string' && val) {
        state[k] = val;
      } else if (Array.isArray(val) && val.length) {
        state[k] = val;
      }
    });
  }

  function showProgress(pct) {
    var container = document.getElementById('cvImportProgress');
    var fill = document.getElementById('cvImportProgressFill');
    if (!container || !fill) return;
    if (pct > 0) {
      container.style.display = 'block';
      fill.style.width = pct + '%';
    } else {
      container.style.display = 'none';
      fill.style.width = '0%';
    }
  }

  function showSummary(summary, errors) {
    var el = document.getElementById('cvImportSummary');
    if (!el) return;
    if (!summary.length && !errors.length) {
      el.style.display = 'none';
      return;
    }
    el.style.display = 'block';
    var html = '<ul>';
    summary.forEach(function(s) {
      var cls = s.status === 'ok' ? 'ok' : 'fail';
      var icon = s.status === 'ok' ? '✓' : s.status === 'missing' ? '✗' : '–';
      html += '<li class="' + cls + '">' + icon + ' ' + s.section + ': ' + s.msg + '</li>';
    });
    errors.forEach(function(e) {
      html += '<li class="fail">✗ ' + e + '</li>';
    });
    html += '</ul>';
    el.innerHTML = html;
  }

  function showImportSuccess(msg) {
    var el = document.getElementById('cvImportSummary');
    if (el) {
      el.style.display = 'block';
      el.innerHTML = '<p style="color:var(--color-primary,#00A7A0);font-weight:600;">' + msg + '</p>';
      setTimeout(function() { el.style.display = 'none'; }, 5000);
    }
  }

  function exportExcel() {
    if (typeof XLSX === 'undefined') {
      alert('Excel library not ready. Please try again.');
      return;
    }
    var cvData = getCvData();
    var wb = XLSX.utils.book_new();
    var name = state.fullName.replace(/\s+/g, '_') || 'CV';

    Object.keys(cvData).forEach(function(section) {
      var headers = CV_SECTIONS[section];
      var data = [headers];
      var rows = cvData[section];

      if (section === 'Work Experience' || section === 'Projects') {
        if (rows.length === 0) data.push(headers.map(function() { return ''; }));
        else rows.forEach(function(row) { data.push(row); });
      } else if (section === 'Education') {
        data.push(rows);
      } else {
        data.push(rows);
      }

      var ws = XLSX.utils.aoa_to_sheet(data);
      var colWidths = headers.map(function(h) { return { wch: Math.max(h.length * 1.5, 18) }; });
      ws['!cols'] = colWidths;
      XLSX.utils.book_append_sheet(wb, ws, section);
    });

    XLSX.writeFile(wb, name + '_CV.xlsx');
  }

  /* ---- Init ---- */
  function init() {
    if (!gateEl || !appEl) return;
    restoreFromStorage();
    renderPreview();
    updateKpis();
    runAtsCheck();
    renderSkillsTags();

    document.getElementById('cvDownloadTemplate').addEventListener('click', downloadTemplate);
    document.getElementById('cvImportExcel').addEventListener('click', importExcel);
    document.getElementById('cvExportExcel').addEventListener('click', exportExcel);

    // Drag & drop
    var dropZone = document.getElementById('cvDropZone');
    if (dropZone) {
      ['dragenter', 'dragover'].forEach(function(evt) {
        dropZone.addEventListener(evt, function(e) {
          e.preventDefault();
          e.stopPropagation();
          dropZone.classList.add('cv-io-card__drop--active');
        });
      });
      ['dragleave', 'drop'].forEach(function(evt) {
        dropZone.addEventListener(evt, function(e) {
          e.preventDefault();
          e.stopPropagation();
          dropZone.classList.remove('cv-io-card__drop--active');
        });
      });
      dropZone.addEventListener('drop', function(e) {
        var files = e.dataTransfer.files;
        if (files.length && files[0].name.endsWith('.xlsx') && files[0].size <= 10 * 1024 * 1024) {
          processExcelFile(files[0]);
        } else {
          alert('Please drop a valid .xlsx file under 10 MB.');
        }
      });
    }
  }

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', init);
  }
})();
