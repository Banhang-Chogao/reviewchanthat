(() => {
  const container = document.getElementById('service-status');
  if (!container) return;

  const dot = (id) => document.getElementById(id);
  const badge = (id) => document.getElementById(id);
  const setStatus = (dotId, badgeId, status, label) => {
    const d = dot(dotId);
    const b = badge(badgeId);
    if (d) d.setAttribute('data-status', status);
    if (b) { b.setAttribute('data-status', status); b.textContent = label; }
  };

  const checkGA = () => {
    const check = () => {
      const loaded = typeof window.gtag === 'function';
      setStatus('status-dot-ga', 'status-badge-ga', loaded ? 'connected' : 'disconnected', loaded ? 'Đã kết nối' : 'Chưa kết nối');
    };
    if (document.readyState === 'complete') { check(); }
    else { window.addEventListener('load', check); }
    setTimeout(() => setStatus('status-dot-ga', 'status-badge-ga', 'disconnected', 'Chưa kết nối'), 8000);
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
