// Self-hosted, privacy-first hit counter for reviewchanthat.
// Zero client JS: the blog embeds a plain <img src=".../hits.svg">.
// Each request increments a single integer in Cloudflare KV and returns a
// shields-style badge SVG. No IP, cookie, User-Agent, or personal data is
// stored — only the running total. You own the data end to end.

const TITLE = "hits";
const TITLE_BG = "#555555"; // gray left segment (matches previous badge)
const COUNT_BG = "#79C83D"; // green right segment
const TEXT = "#ffffff";

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// Render a flat shields-style badge. Widths are derived from text length so
// the SVG never distorts as the digit count grows.
function badge(count) {
  const left = TITLE;
  const right = new Intl.NumberFormat("en-US").format(count);
  const lw = Math.round(left.length * 6.5) + 12;
  const rw = Math.round(right.length * 7.5) + 14;
  const w = lw + rw;
  const lx = (lw / 2) * 10;
  const rx = (lw + rw / 2) * 10;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="20" role="img" aria-label="${esc(left)}: ${esc(right)}">
  <linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
  <clipPath id="r"><rect width="${w}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="${lw}" height="20" fill="${TITLE_BG}"/>
    <rect x="${lw}" width="${rw}" height="20" fill="${COUNT_BG}"/>
    <rect width="${w}" height="20" fill="url(#s)"/>
  </g>
  <g fill="${TEXT}" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="110" text-rendering="geometricPrecision">
    <text x="${lx}" y="150" transform="scale(.1)" fill="#000" fill-opacity=".3" textLength="${(lw - 12) * 10}">${esc(left)}</text>
    <text x="${lx}" y="140" transform="scale(.1)" textLength="${(lw - 12) * 10}">${esc(left)}</text>
    <text x="${rx}" y="150" transform="scale(.1)" fill="#000" fill-opacity=".3" textLength="${(rw - 14) * 10}">${esc(right)}</text>
    <text x="${rx}" y="140" transform="scale(.1)" textLength="${(rw - 14) * 10}">${esc(right)}</text>
  </g>
</svg>`;
}

const NO_CACHE = {
  "content-type": "image/svg+xml; charset=utf-8",
  // Force every view to reach the Worker so the count actually increments.
  "cache-control": "no-cache, no-store, must-revalidate, max-age=0",
  "pragma": "no-cache",
  "expires": "0",
  "access-control-allow-origin": "*",
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method !== "GET") {
      return new Response("Method Not Allowed", { status: 405 });
    }
    if (url.pathname !== "/hits.svg") {
      return new Response("Not Found", { status: 404 });
    }

    // Read → increment → write. KV is eventually consistent; a few lost
    // increments under heavy concurrency are acceptable for a blog counter.
    const base = parseInt(env.BASELINE || "0", 10) || 0;
    const stored = parseInt((await env.HITS.get("count")) || "0", 10) || 0;
    const next = stored + 1;
    await env.HITS.put("count", String(next));

    return new Response(badge(base + next), { headers: NO_CACHE });
  },
};
