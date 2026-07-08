(() => {
  const root = document.getElementById('print-watermark');
  if (!root) {
    return;
  }

  const siteUrl = (root.dataset.siteUrl || window.location.origin).replace(/\/?$/, '/');

  function randomHash16() {
    if (window.crypto && window.crypto.getRandomValues) {
      const bytes = new Uint8Array(8);
      window.crypto.getRandomValues(bytes);
      return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('').slice(0, 16);
    }
    return Math.random().toString(16).slice(2, 18).padEnd(16, '0').slice(0, 16);
  }

  function buildWatermarkText() {
    return `${randomHash16()}_${siteUrl}`;
  }

  function renderTiles(text) {
    root.innerHTML = '';
    root.dataset.text = text;

    const positions = [
      { top: '18%', left: '8%' },
      { top: '18%', left: '52%' },
      { top: '48%', left: '30%' },
      { top: '78%', left: '8%' },
      { top: '78%', left: '52%' }
    ];

    positions.forEach((pos) => {
      const tile = document.createElement('span');
      tile.className = 'print-watermark__tile';
      tile.textContent = text;
      tile.style.top = pos.top;
      tile.style.left = pos.left;
      root.append(tile);
    });

    const stamp = document.createElement('span');
    stamp.className = 'print-watermark__stamp';
    stamp.textContent = text;
    root.append(stamp);
  }

  function applyWatermark() {
    renderTiles(buildWatermarkText());
  }

  window.addEventListener('beforeprint', applyWatermark);
  window.addEventListener('afterprint', () => {
    root.innerHTML = '';
    root.dataset.text = '';
  });

  applyWatermark();
})();