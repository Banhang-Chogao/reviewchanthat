# reviewchanthat-hits — self-hosted hit counter

A tiny Cloudflare Worker that counts blog visits and returns a badge SVG.
The blog stays 100% static and zero-JS: the footer embeds a plain
`<img src="…/hits.svg">`. You own the data — the Worker stores **only** a
running integer in KV. No IP, cookie, or User-Agent is ever recorded.

```
static <img>  ──▶  reviewchanthat-hits.<subdomain>.workers.dev/hits.svg
                          │
                          └─ KV "count"  +1 per visit  ──▶  badge SVG
```

## One-time deploy

Prereqs: a Cloudflare account and `wrangler` (`npm i` here installs it).

```bash
cd counter-worker
npm install

# 1. Log in
npx wrangler login

# 2. Create the KV namespace, then paste the printed id into wrangler.toml
#    ([[kv_namespaces]] → id = "…")
npx wrangler kv namespace create HITS

# 3. (optional) seed a starting total instead of 0
#    npx wrangler kv key put --binding HITS count 1000 --remote

# 4. Ship it
npx wrangler deploy
```

`wrangler deploy` prints the live URL, e.g.
`https://reviewchanthat-hits.<your-subdomain>.workers.dev`.

## Wire it to the blog

The badge URL lives in `hugo.toml`:

```toml
hits_badge_url = "https://reviewchanthat-hits.<your-subdomain>.workers.dev/hits.svg"
```

Set it to your real deployed URL (mine defaults to the `tamsudev-com`
subdomain — change if yours differs). Empty string hides the badge entirely.
The Worker sends `no-store` headers so every page view increments once.

## Verify

```bash
curl -s "https://reviewchanthat-hits.<subdomain>.workers.dev/hits.svg" | head
# → an <svg> whose count rises by 1 on each request
```

## Notes

- KV is eventually consistent; a handful of increments may be lost under heavy
  concurrent traffic. Fine for a blog counter, not for billing.
- `BASELINE` in `wrangler.toml` is added on top of the KV count if you want to
  represent visits from before the counter existed.
