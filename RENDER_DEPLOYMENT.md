# Render.com Deployment Guide

Deploy the API backend to Render's free tier.

## Step 1: Prepare Your GitHub Repository

✅ Already done:
- `app.py` - Flask server ready
- `requirements.txt` - All dependencies listed
- `services/city_lookup.py` - Backend service

## Step 2: Connect to Render

1. Go to https://render.com
2. Click **Sign up** with GitHub
3. Authorize Render to access your GitHub repos
4. Click **New +** → **Web Service**
5. Select repository: `Banhang-Chogao/reviewchanthat`
6. Click **Connect**

## Step 3: Configure Web Service

Fill in the following:

| Field | Value |
|-------|-------|
| **Name** | `reviewchanthat-api` |
| **Environment** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |
| **Instance Type** | `Free` |

## Step 4: Add Environment Variables

Click **Advanced** → **Environment**

Add variable:
```
AVIATIONSTACK_API_KEY = f03fa98d3d7917445de7afdec55ddb94
```

## Step 5: Deploy

1. Click **Create Web Service**
2. Render builds and deploys automatically
3. Wait 2-3 minutes for deployment
4. You'll see a live URL like: `https://reviewchanthat-api.onrender.com`

## Step 6: Update Frontend

The backend is now at: `https://reviewchanthat-api.onrender.com/api/destination/search`

Update frontend to use this URL:

**Option A: Update in code** (required for production):
Edit `static/js/travel-destination-search.js`:
```javascript
const CONFIG = {
  apiBaseUrl: 'https://reviewchanthat-api.onrender.com/api/destination/search',
  // ... rest of config
};
```

**Option B: Keep localhost for local dev** (development only):
```javascript
const CONFIG = {
  apiBaseUrl: window.location.hostname === 'localhost' 
    ? '/api/destination/search'  // Local dev
    : 'https://reviewchanthat-api.onrender.com/api/destination/search',  // Production
  // ... rest of config
};
```

## Step 7: Test API

```bash
# Test that API is running
curl https://reviewchanthat-api.onrender.com/health

# Expected response:
# {"status":"ok"}

# Test destination search
curl "https://reviewchanthat-api.onrender.com/api/destination/search?q=Bangkok"

# Expected response:
# {"success":true,"query":"Bangkok","results":[...],"count":1,"timestamp":"..."}
```

## Step 8: Deploy Frontend to GitHub Pages

The static Hugo site continues to deploy to GitHub Pages via GitHub Actions.

```bash
git add -A
git commit -m "feat: update API endpoint for Render production"
git push origin main
```

GitHub Actions will automatically build and deploy to GitHub Pages.

## Step 9: Verify Live

1. Visit: https://banhang-chogao.github.io/reviewchanthat/travel-planner
2. Try searching for destination (Bangkok, Paris, etc.)
3. Should see dropdown suggestions from API
4. Generate AI trip
5. Export visa document

## Important Notes

- **Free tier limitations**:
  - Service spins down after 15 minutes of inactivity
  - First request after spin-down takes ~30 seconds (cold start)
  - 100 API requests per month (should be enough for testing)

- **Keep API key secure**:
  - Set in Render environment variables
  - Never commit to git
  - Never put in frontend code

- **Monitor usage**:
  - Render dashboard shows API calls
  - Watch Aviationstack API usage
  - Consider upgrading if needed

## Troubleshooting

### "Service is not running" or 502 error
- Check Render dashboard logs
- Verify build completed successfully
- Restart service: Dashboard → Service → Manual Deploy

### CORS errors
- Flask-CORS should handle this automatically
- Check app.py has `CORS(app)` enabled
- Verify Render service is running

### API key not working
- Check environment variable is set in Render
- Verify `AVIATIONSTACK_API_KEY` is in Render env vars
- App will fall back to local cities anyway

### Frontend still shows old version
- Clear browser cache (Ctrl+Shift+Delete)
- Update `static/js/travel-destination-search.js` with new URL
- Redeploy frontend to GitHub Pages
- Wait for GitHub Actions to complete

## URLs

| Component | URL |
|-----------|-----|
| **Frontend (Hugo)** | https://banhang-chogao.github.io/reviewchanthat/travel-planner |
| **Backend API** | https://reviewchanthat-api.onrender.com |
| **Health Check** | https://reviewchanthat-api.onrender.com/health |
| **Destination Search** | https://reviewchanthat-api.onrender.com/api/destination/search?q=Bangkok |

## Next Steps

1. ✅ Deploy API to Render (this guide)
2. 📝 Update frontend API URL in `static/js/travel-destination-search.js`
3. 🚀 Push to GitHub (triggers GitHub Actions)
4. ✅ Test destination search on live site
5. 🎉 Done!

Questions? Check GitHub Actions logs or Render service logs for error details.
