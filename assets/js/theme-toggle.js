(function() {
  'use strict';

  var btn = document.getElementById('themeToggle');
  if (!btn) return;

  var html = document.documentElement;

  function setTheme(dark) {
    if (dark) {
      html.classList.add('dark-mode');
    } else {
      html.classList.remove('dark-mode');
    }
    try { localStorage.setItem('theme', dark ? 'dark' : 'light'); } catch (e) {}
  }

  btn.addEventListener('click', function() {
    setTheme(!html.classList.contains('dark-mode'));
  });
})();
