(function() {
  'use strict';

  var dateEl = document.getElementById('liveClockDate');
  var timeEl = document.getElementById('liveClockTime');
  if (!dateEl || !timeEl) return;

  var WEEKDAYS = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];

  function pad(n) { return n < 10 ? '0' + n : '' + n; }

  function update() {
    var now = new Date();
    var d = now.getDay();
    var dd = pad(now.getDate());
    var mm = pad(now.getMonth() + 1);
    var yyyy = now.getFullYear();
    dateEl.textContent = WEEKDAYS[d] + ', ' + dd + '/' + mm + '/' + yyyy;
    timeEl.textContent = pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
  }

  update();
  setInterval(update, 1000);
})();
