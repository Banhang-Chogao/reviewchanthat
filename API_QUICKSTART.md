# API Quick Start

## Pure Python Setup (Like Before)

This is the simple approach using `requests` library that you used initially.

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set API Key
```bash
# Add to .env or export:
export AVIATIONSTACK_API_KEY=f03fa98d3d7917445de7afdec55ddb94
```

### 3. Run Flask API Server
```bash
python3 app.py
```

Expected output:
```
 * Running on http://0.0.0.0:5000
 * Press CTRL+C to quit
```

### 4. Test API in Another Terminal
```bash
# Search by city name
curl "http://localhost:5000/api/destination/search?q=Bangkok"

# Search by IATA code
curl "http://localhost:5000/api/destination/search?q=ICN"

# Health check
curl "http://localhost:5000/health"
```

### 5. Run Hugo Frontend (Another Terminal)
```bash
hugo server
# Visit http://localhost:1313/reviewchanthat/travel-planner
```

### 6. Test Destination Search UI
1. Go to: http://localhost:1313/reviewchanthat/travel-planner
2. Click "Điểm đến" input field
3. Type "Bangkok"
4. Should see dropdown with suggestions
5. Select one destination
6. Fill dates
7. Click "Generate AI Trip"

## How It Works

```
Frontend (Hugo)
    ↓
    └─→ GET /api/destination/search?q=Bangkok
            ↓
        Flask App (app.py)
            ↓
            └─→ services/city_lookup.py
                    ↓
                    ├─→ Try: Aviationstack API (requires network)
                    └─→ Fallback: FALLBACK_CITIES (local cache)
            ↓
        Returns JSON
    ↓
Frontend renders dropdown
```

## File Structure

```
├── app.py                          # Flask server (NEW)
├── services/
│   └── city_lookup.py             # Destination search service (requests library)
├── static/js/
│   └── travel-destination-search.js # Frontend autocomplete
├── .env                           # API key (your config)
└── DEPLOYMENT.md                  # Full deployment guide
```

## Environment Variable

The `.env` file should contain:
```
AVIATIONSTACK_API_KEY=f03fa98d3d7917445de7afdec55ddb94
```

Load it in:
- **Local dev**: `export $(cat .env | xargs)`
- **Production**: Set in your deployment platform (Railway, Render, Vercel, etc.)

## What If API Key Fails?

The app automatically falls back to local cities:
- Seoul (ICN)
- Tokyo (NRT, HND)
- Osaka (KIX)
- Bangkok (BKK)
- Singapore (SIN)
- Hanoi (HAN)
- Ho Chi Minh (SGN)
- Paris (CDG)
- Dubai (DXB)
- London (LHR)

Users can still:
- Search from local cache
- Generate AI trips
- Export visa documents
- Full app works offline

## Production Deployment

Choose one:

### Easy: Vercel (Full Stack Python Support)
```bash
vercel --prod
```

### Budget-friendly: Railway
```bash
railway up --environment production
```

### Free tier: Render
- Connect GitHub repo
- Select Python 3
- Done!

See `DEPLOYMENT.md` for detailed instructions.

## Testing Checklist

- [ ] Local Flask server runs: `python3 app.py`
- [ ] API endpoint responds: `curl http://localhost:5000/health`
- [ ] Destination search works: Type "Bangkok" in UI
- [ ] Fallback works: Disconnect internet, app still searches
- [ ] Data persists: Generate trip, reload page, destination still selected
- [ ] All dates work: Single date and date range
- [ ] Mobile works: Test on phone/tablet
- [ ] Dark mode works: Toggle theme
- [ ] Export works: Generate visa document, download PDF

Done! Ready to deploy.
