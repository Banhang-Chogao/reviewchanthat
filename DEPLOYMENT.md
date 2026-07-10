# Deployment Guide: Travel Planner with API

## Current Setup

- **Frontend**: Hugo static site
- **Backend**: Node.js serverless function (`api/destination.js`)
- **Deployment target**: GitHub Pages (frontend) + Vercel (backend)

## Local Development

### Prerequisites
```bash
npm install -g vercel  # Install Vercel CLI
pip install -r requirements.txt
```

### Environment Setup
```bash
# Create .env file
echo "AVIATIONSTACK_API_KEY=f03fa98d3d7917445de7afdec55ddb94" > .env
```

### Run Locally
```bash
# Terminal 1: Hugo dev server
hugo server

# Terminal 2: Vercel dev environment (simulates API endpoints)
vercel dev

# Or just test the backend:
node api/destination.js
```

The frontend will call `http://localhost:3000/api/destination/search?q=Bangkok`

## Deployment Options

### Option 1: GitHub Pages (Frontend) + Vercel (Backend) — RECOMMENDED

**Best for**: Public project, free tier, simple setup

1. **Deploy to GitHub Pages** (automatic via GitHub Actions)
   ```bash
   # Already configured in .github/workflows/deploy.yml
   git push origin main
   ```

2. **Deploy backend to Vercel**
   ```bash
   vercel login
   vercel --prod
   ```

3. **Update frontend API base URL** for production
   - Change `apiBaseUrl: '/api/destination/search'` in `static/js/travel-destination-search.js`
   - To point to Vercel: `apiBaseUrl: 'https://reviewchanthat.vercel.app/api/destination/search'`

### Option 2: Full Vercel Deployment

**Best for**: Single provider, easier management

1. **Connect Vercel to this GitHub repo**
   ```bash
   vercel link
   ```

2. **Set environment variables**
   - Go to Vercel Project Settings → Environment Variables
   - Add: `AVIATIONSTACK_API_KEY=f03fa98d3d7917445de7afdec55ddb94`

3. **Push to trigger automatic deployment**
   ```bash
   git push origin main
   ```

Vercel will automatically:
- Run Hugo build
- Deploy to `reviewchanthat.vercel.app`
- Run Node.js API functions at `/api/destination`
- Frontend can call API directly

## API Reference

### GET `/api/destination/search`

Search for destinations by city name or IATA airport code.

**Parameters**:
- `q` (string, required): Search query (min 2 characters)

**Response**:
```json
{
  "success": true,
  "query": "Bangkok",
  "results": [
    {
      "city": "Bangkok",
      "country": "Thailand",
      "iata": "BKK",
      "timezone": "Asia/Bangkok",
      "flag": "🇹🇭",
      "latitude": 13.6923,
      "longitude": 100.7501
    }
  ]
}
```

**Behavior**:
- Tries Aviationstack API first
- Falls back to local FALLBACK_CITIES on error
- CORS enabled for any origin
- Caches results on frontend for 30 minutes

## Troubleshooting

### "API error 403" or "Cannot reach API"
- Verify AVIATIONSTACK_API_KEY is set correctly in .env
- Check that backend is running/deployed
- Verify CORS headers are being returned

### "Destination search shows only fallback cities"
- Aviationstack API rate limit may be exceeded
- Check Aviationstack account status
- Fallback cache (FALLBACK_CITIES) will still work

### Version badge not updating
- Script `scripts/update-version.sh` should run during build
- Verify `.github/workflows/deploy.yml` includes version update step
- Check `data/version.toml` is generated

## Next Steps

1. Deploy to Vercel for full integration (recommended)
2. Test destination search in live environment
3. Generate and export visa itinerary
4. Monitor API usage on Aviationstack dashboard
