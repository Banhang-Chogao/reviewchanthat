# QA Testing - AI Travel Planner v2

## Quick Start
```bash
# Terminal 1: Start Python backend
pip install -r requirements.txt
export AVIATIONSTACK_API_KEY=f03fa98d3d7917445de7afdec55ddb94
python3 app.py

# Terminal 2: Start Hugo
hugo server

# Visit: http://localhost:1313/reviewchanthat/travel-planner
```

## Test Cases

### Autocomplete
- [ ] Type "Bangkok" → shows 🇹🇭 Bangkok (BKK) in dropdown
- [ ] Type "ICN" → shows 🇰🇷 Incheon (ICN)
- [ ] Debounce works: rapid typing → single API call
- [ ] Click item → selected, shows in badge

### Keyboard Navigation
- [ ] Arrow ↓/↑ → highlight items
- [ ] Enter → select highlighted
- [ ] Esc → close dropdown

### Fallback
- [ ] API down → shows local cities (Bangkok, Tokyo, Paris, etc.)
- [ ] Still selectable and works

### Desktop
- [ ] Dropdown floats properly
- [ ] S-DNA rounded corners applied
- [ ] Keyboard nav works

### Mobile
- [ ] Responsive layout
- [ ] Touch works
- [ ] Dropdown fits screen

### Live Site
- [ ] Generate AI Trip works with selected destination
- [ ] Version badge shows in red (top-left)
- [ ] Dates are required
- [ ] Submit enabled after destination + dates

