# Deployment Guide: Travel Planner with API

## Current Setup

- **Frontend**: Hugo static site (`public/`)
- **Backend**: Python Flask app (`app.py`) wrapping `services/city_lookup.py`
- **API Endpoint**: `/api/destination/search?q=<query>`
- **Dependencies**: requests, flask, flask-cors, gunicorn

## Local Development

### Prerequisites
```bash
pip install -r requirements.txt  # Install all dependencies
```

### Environment Setup
```bash
# Create .env file or export variable
export AVIATIONSTACK_API_KEY=f03fa98d3d7917445de7afdec55ddb94
```

### Run Locally
```bash
# Terminal 1: Flask API server (port 5000)
python3 app.py

# Terminal 2: Hugo dev server (port 1313)
hugo server

# Test API directly:
curl "http://localhost:5000/api/destination/search?q=Bangkok"
```

Response example:
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

## Deployment Options

### Option 1: GitHub Pages + Railway/Render (Backend) — RECOMMENDED

**Best for**: Free static hosting + free backend hosting

1. **Deploy frontend to GitHub Pages** (automatic)
   ```bash
   # Already configured in .github/workflows/deploy.yml
   git push origin main
   ```

2. **Deploy backend to Railway or Render**
   
   **Railway.app**:
   ```bash
   npm install -g @railway/cli
   railway login
   railway link  # This project
   railway up --environment production
   ```
   
   **Render.com**:
   - Connect GitHub repo
   - New Web Service
   - Runtime: Python 3
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app --bind 0.0.0.0:$PORT`

3. **Update frontend API URL for production**
   - In `static/js/travel-destination-search.js`, update:
     ```javascript
     apiBaseUrl: 'https://your-backend-url.railway.app/api/destination/search'
     // or
     apiBaseUrl: 'https://your-app.onrender.com/api/destination/search'
     ```

### Option 2: Vercel Full Stack (Recommended - Easiest)

**Best for**: Single provider, zero-config deployment

Vercel natively supports Python backend with Flask apps.

1. **Connect repo to Vercel**
   ```bash
   npm install -g vercel
   vercel link
   ```

2. **Set environment variable**
   - Project Settings → Environment Variables
   - Add: `AVIATIONSTACK_API_KEY=f03fa98d3d7917445de7afdec55ddb94`

3. **Deploy**
   ```bash
   vercel --prod
   ```

Vercel automatically:
- Detects Python + Hugo
- Runs Flask app at `/api/*` routes
- Builds and serves Hugo at `/`
- Provides SSL, CDN, auto-scaling for free

### Option 3: Docker (Local or Cloud)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
```

Deploy to any Docker host (DigitalOcean, AWS, Heroku, etc.)

## API Reference

### GET `/api/destination/search`

Search for destinations by city name or IATA airport code.

**Parameters**:
- `q` (string, required): Search query (min 2 characters)

**Example**:
```bash
curl "http://localhost:5000/api/destination/search?q=Bangkok"
curl "http://localhost:5000/api/destination/search?q=ICN"  # IATA code
```

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
  ],
  "count": 1,
  "timestamp": "2026-07-11T00:00:00Z"
}
```

**Backend Behavior**:
1. Checks in-memory cache (30 min TTL)
2. If not cached, calls Aviationstack API with `requests` library
3. If API fails, falls back to local FALLBACK_CITIES
4. Returns max 10 results

**Frontend Behavior**:
- Calls `/api/destination/search` on localhost:5000 (dev)
- Points to backend URL on production
- CORS handled by Flask-CORS
- Frontend caches results for 30 minutes
- Debounces input (300ms)
- Keyboard navigation (Arrow/Enter/ESC)
- Fallback to local cities if endpoint unreachable

## Troubleshooting

### "Cannot reach API" or CORS errors
- **Local dev**: Ensure `python3 app.py` is running on port 5000
- **Production**: Check backend deployment status
- **CORS**: Flask-CORS should allow all origins for frontend requests

### "403 Forbidden" from Aviationstack API
- API key (`AVIATIONSTACK_API_KEY`) may be invalid or expired
- Rate limit exceeded (free tier: 100 requests/month)
- Backend will automatically fall back to FALLBACK_CITIES
- Planner still works with local city cache

### "No destination found" dropdown
- Query length < 2 characters (minimum required)
- Destination not in Aviationstack data + not in FALLBACK_CITIES
- Try IATA code (e.g., "ICN" instead of "Incheon")
- Fallback cities include: ICN, NRT, BKK, SIN, SGN, HAN, CDG, DXB, LHR

### Version badge not updating
- Run: `bash scripts/update-version.sh`
- Check: `data/version.toml` is generated
- Hugo rebuild required: `hugo --gc --minify`

### Backend errors in production
- Check environment variables are set: `AVIATIONSTACK_API_KEY`
- Review logs:
  - **Railway**: `railway logs`
  - **Render**: Dashboard → Logs
  - **Vercel**: Dashboard → Deployments → Logs
- Test endpoint: `curl https://your-backend.com/health`

## Next Steps

1. **Local testing**:
   ```bash
   python3 app.py  # Terminal 1
   hugo server     # Terminal 2
   # Visit http://localhost:1313/reviewchanthat/travel-planner
   ```

2. **Deploy backend** (Railway/Render/Vercel)

3. **Update frontend API URL** for production

4. **Test live**:
   - Search destinations
   - Generate AI itinerary
   - Export visa document

5. **Monitor**:
   - Backend logs
   - Aviationstack API usage
   - User feedback
