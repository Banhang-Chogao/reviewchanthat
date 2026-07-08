(() => {
  const container = document.getElementById('service-status');
  if (!container) return;

  const byId = (id) => document.getElementById(id);
  const setStatus = (dotId, badgeId, status, label) => {
    const d = byId(dotId);
    const b = byId(badgeId);
    if (d) d.setAttribute('data-status', status);
    if (b) { b.setAttribute('data-status', status); b.textContent = label; }
  };

  const checkGA = (retries = 5) => {
    const loaded = typeof window.gtag === 'function';
    setStatus('status-dot-ga', 'status-badge-ga', loaded ? 'connected' : 'disconnected', loaded ? 'Đã kết nối' : 'Chưa kết nối');
    if (!loaded && retries > 0) {
      setTimeout(() => checkGA(retries - 1), 1000);
    }
  };

  const checkSC = async () => {
    try {
      const base = document.body.getAttribute('data-site-base') || '/';
      const res = await fetch(base + 'google359ea2ec9d73ed9c.html', { method: 'HEAD', cache: 'no-cache' });
      setStatus('status-dot-sc', 'status-badge-sc', res.ok ? 'connected' : 'disconnected', res.ok ? 'Đã kết nối' : 'Lỗi xác minh');
    } catch {
      setStatus('status-dot-sc', 'status-badge-sc', 'disconnected', 'Không thể truy cập');
    }
  };

  setStatus('status-dot-ga', 'status-badge-ga', 'checking', 'Đang kiểm tra…');
  setStatus('status-dot-sc', 'status-badge-sc', 'checking', 'Đang kiểm tra…');
  checkGA();
  checkSC();
})();
