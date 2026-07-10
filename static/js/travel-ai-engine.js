(function() {
  'use strict';

  var DESTINATIONS_DATA = null;
  var DATA_LOADED = false;

  function getSeason(month) {
    if (month >= 3 && month <= 5) return 'spring';
    if (month >= 6 && month <= 8) return 'summer';
    if (month >= 9 && month <= 11) return 'autumn';
    return 'winter';
  }

  function getSeasonSouthern(month) {
    if (month >= 9 && month <= 11) return 'spring';
    if (month >= 12 || month <= 2) return 'summer';
    if (month >= 3 && month <= 5) return 'autumn';
    return 'winter';
  }

  function getTropicalSeason(month) {
    if (month >= 11 || month <= 2) return 'cool';
    if (month >= 3 && month <= 6) return 'hot';
    return 'rainy';
  }

  function resolveWeather(dest, month) {
    var weather = dest && dest.weather;
    if (!weather) return { temp: '20-30°C', conditions: 'Variable' };

    // Check tropical pattern (Bangkok, HCMC, Singapore)
    var tropical = weather['cool'] || weather['hot'];
    if (tropical) {
      var key = getTropicalSeason(month);
      var data = weather[key] || weather['year_round'];
      return data || { temp: '25-33°C', conditions: 'Tropical' };
    }

    // Spring/Summer/Autumn/Winter pattern
    var season = weather['spring'] ? getSeason(month) : getSeasonSouthern(month);
    var data = weather[season] || weather['year_round'];
    return data || { temp: '20-25°C', conditions: 'Pleasant' };
  }

  var DEFAULT_CURRENCY = 'USD';

  var BUDGET_RANGES = {
    USD: { 'luxury': 300, 'mid-range': 150, 'budget': 80 },
    JPY: { 'luxury': 45000, 'mid-range': 22000, 'budget': 12000 },
    KRW: { 'luxury': 400000, 'mid-range': 200000, 'budget': 100000 },
    THB: { 'luxury': 10000, 'mid-range': 5000, 'budget': 2500 },
    SGD: { 'luxury': 450, 'mid-range': 220, 'budget': 110 },
    EUR: { 'luxury': 280, 'mid-range': 140, 'budget': 75 },
    VND: { 'luxury': 7000000, 'mid-range': 3500000, 'budget': 1800000 },
    AED: { 'luxury': 1100, 'mid-range': 550, 'budget': 300 },
    GBP: { 'luxury': 240, 'mid-range': 120, 'budget': 65 },
    MYR: { 'luxury': 1200, 'mid-range': 600, 'budget': 300 },
    PHP: { 'luxury': 17000, 'mid-range': 8500, 'budget': 4500 },
    IDR: { 'luxury': 5000000, 'mid-range': 2500000, 'budget': 1300000 },
    CNY: { 'luxury': 2200, 'mid-range': 1100, 'budget': 600 },
    HKD: { 'luxury': 2400, 'mid-range': 1200, 'budget': 650 },
    TWD: { 'luxury': 9500, 'mid-range': 4800, 'budget': 2500 },
    AUD: { 'luxury': 450, 'mid-range': 230, 'budget': 120 },
    INR: { 'luxury': 25000, 'mid-range': 12000, 'budget': 6500 },
    TRY: { 'luxury': 10000, 'mid-range': 5000, 'budget': 2600 },
    CHF: { 'luxury': 280, 'mid-range': 150, 'budget': 85 },
    DKK: { 'luxury': 2100, 'mid-range': 1050, 'budget': 560 },
    SEK: { 'luxury': 3200, 'mid-range': 1600, 'budget': 850 },
    CZK: { 'luxury': 7000, 'mid-range': 3500, 'budget': 1900 },
    HUF: { 'luxury': 110000, 'mid-range': 55000, 'budget': 30000 }
  };

  var COUNTRY_CURRENCY_MAP = {
    'South Korea': 'KRW',
    'Republic of Korea': 'KRW',
    'Korea, Republic of': 'KRW',
    'Japan': 'JPY',
    'Thailand': 'THB',
    'Vietnam': 'VND',
    'Singapore': 'SGD',
    'France': 'EUR',
    'Italy': 'EUR',
    'Spain': 'EUR',
    'Germany': 'EUR',
    'Netherlands': 'EUR',
    'Portugal': 'EUR',
    'Austria': 'EUR',
    'Greece': 'EUR',
    'Finland': 'EUR',
    'United Arab Emirates': 'AED',
    'UAE': 'AED',
    'United Kingdom': 'GBP',
    'UK': 'GBP',
    'Malaysia': 'MYR',
    'Philippines': 'PHP',
    'Indonesia': 'IDR',
    'China': 'CNY',
    'Hong Kong': 'HKD',
    'Taiwan': 'TWD',
    'Australia': 'AUD',
    'United States': 'USD',
    'India': 'INR',
    'Turkey': 'TRY',
    'Switzerland': 'CHF',
    'Denmark': 'DKK',
    'Sweden': 'SEK',
    'Czech Republic': 'CZK',
    'Hungary': 'HUF'
  };

  function normalizeCurrency(currency) {
    return (currency || DEFAULT_CURRENCY).toString().trim().toUpperCase();
  }

  function resolveCurrency(curated, destData) {
    if (curated && curated.currency) return normalizeCurrency(curated.currency);
    if (destData && destData.currency) return normalizeCurrency(destData.currency);
    return COUNTRY_CURRENCY_MAP[destData && destData.country] || DEFAULT_CURRENCY;
  }

  function getDailyBudget(currency, budget) {
    var ranges = BUDGET_RANGES[currency] || BUDGET_RANGES[DEFAULT_CURRENCY];
    return ranges[budget] || ranges['mid-range'];
  }

  function getTravelerMultiplier(tripData) {
    var adults = Math.max(parseInt(tripData.adults, 10) || 1, 1);
    var children = Math.max(parseInt(tripData.children, 10) || 0, 0);
    return adults + (children * 0.6);
  }

  function formatMoney(amount, currency) {
    return currency + ' ' + Math.round(amount).toLocaleString('en-US');
  }

  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  class TravelAIEngine {
    static getData() {
      return DESTINATIONS_DATA;
    }

    static async ensureDataLoaded() {
      if (DATA_LOADED) return;
      try {
        var resp = await fetch('/reviewchanthat/data/travel-destinations.json');
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        DESTINATIONS_DATA = await resp.json();
        DATA_LOADED = true;
      } catch (e) {
        console.warn('Could not load curated dataset, using built-in fallback');
        DESTINATIONS_DATA = {};
        DATA_LOADED = true;
      }
    }

    static lookupDest(iataOrCity) {
      if (!DESTINATIONS_DATA) return null;
      var key = iataOrCity ? iataOrCity.toUpperCase() : '';
      var entry = DESTINATIONS_DATA[key] || DESTINATIONS_DATA[iataOrCity ? iataOrCity.toLowerCase().replace(/\s+/g, '_') : ''];
      return entry || null;
    }

    static async generateItinerary(tripData) {
      await this.ensureDataLoaded();
      return this.generateLocalItinerary(tripData);
    }

    static generateLocalItinerary(tripData) {
      var destData = tripData.destinationData || {};
      var iata = destData.iata || '';
      var city = destData.city || tripData.destination;
      var country = destData.country || '';
      var days = tripData.days || 1;

      // Look up curated data
      var curated = this.lookupDest(iata) || this.lookupDest(city);
      var month = new Date(tripData.departure).getMonth() + 1;
      var weather = resolveWeather(curated, month);
      var budget = tripData.budget || 'mid-range';

      var dailyItinerary = this.generateDailyActivities(curated, city, country, days, budget, tripData);
      var currency = resolveCurrency(curated, destData);
      var daily = getDailyBudget(currency, budget);
      var travelerMultiplier = getTravelerMultiplier(tripData);
      var totalMin = Math.round(daily * days * travelerMultiplier);
      var totalMax = Math.round(totalMin * 1.3);

      return {
        currency: currency,
        budget: budget,
        dailyBudget: daily,
        estimatedBudgetMin: totalMin,
        estimatedBudgetMax: totalMax,
        weather: weather.temp + ', ' + weather.conditions,
        weatherNotes: 'Packing: ' + this.getWeatherPackingAdvice(weather),
        hotelArea: curated ? curated.hotel_areas : 'Central district near main attractions',
        transportation: curated ? curated.transport : 'Public transit recommended. Download local ride-hailing app.',
        estimatedBudget: formatMoney(totalMin, currency) + ' - ' + formatMoney(totalMax, currency) + ' (' + tripData.adults + ' adult(s)' + (tripData.children > 0 ? ', ' + tripData.children + ' child(ren)' : '') + ')',
        packingList: this.getPackingList(weather, budget),
        localTips: curated ? curated.local_tips : 'Check local customs and be respectful. Download offline maps. Learn basic phrases.',
        emergencyNumbers: curated ? curated.emergency_numbers : 'Call your embassy. Local 999/911 variants exist.',
        airportNotes: curated ? curated.airport_notes : 'Ask hotel for airport transfer recommendations.',
        dailyItinerary: dailyItinerary,
        visaItinerary: this.generateVisaItinerary(tripData, dailyItinerary)
      };
    }

    static getWeatherPackingAdvice(weather) {
      var temp = weather.temp || '';
      var cond = weather.conditions || '';
      var avgTemp = 25;
      var matches = temp.match(/(\d+)/g);
      if (matches && matches.length > 0) {
        var sum = 0;
        for (var i = 0; i < matches.length; i++) sum += parseInt(matches[i], 10);
        avgTemp = sum / matches.length;
      }

      if (avgTemp > 30) return 'Light cotton clothing, sunscreen, hat, sunglasses, reusable water bottle. Avoid synthetic fabrics.';
      if (avgTemp > 25) return 'Light layers, T-shirts, shorts/skirts, sunscreen, rain jacket for sudden showers.';
      if (avgTemp > 18) return 'Light jacket or sweater for evenings. Comfortable walking shoes. Versatile layers work best.';
      if (avgTemp > 10) return 'Warm layers, medium jacket, closed shoes. Umbrella recommended. Scarf for windy days.';
      return 'Winter coat, thermal layers, gloves, warm hat, scarf, waterproof boots. Pack hand warmers for extreme cold.';
    }

    static generateDailyActivities(curated, city, country, days, budget, tripData) {
      var fallbackActs = {
        morning: ['Explore the city center and main landmarks', 'Visit the local market', 'Walking tour of historic district', 'Visit a local museum'],
        lunch: ['Try local cuisine at a recommended restaurant', 'Street food lunch at popular spot', 'Lunch with a view of main square', 'Market food court lunch'],
        afternoon: ['Shopping at local boutiques', 'Visit cultural sites', 'Explore neighborhoods', 'Relax at a cafe'],
        dinner: ['Dinner at local specialty restaurant', 'Night market exploration', 'Rooftop dining', 'Local cuisine experience']
      };

      var curatedActs = curated && curated.activities || fallbackActs;
      var pool = {};
      var tods = ['morning', 'lunch', 'afternoon', 'dinner'];
      for (var t = 0; t < tods.length; t++) {
        var tod = tods[t];
        var items = curatedActs[tod] || fallbackActs[tod] || [];
        pool[tod] = shuffle(items);
      }

      var activities = [];
      for (var i = 0; i < days; i++) {
        var act = { morning: '', lunch: '', afternoon: '', dinner: '', notes: '' };

        if (i === 0) {
          act.morning = 'Arrival at airport and transfer to hotel. Check-in and rest.';
          act.notes = 'Rest and acclimatize. Explore the hotel area in the evening.';
          // For remaining day 1 activities, use curated picks
          act.lunch = this.pickActivity(pool, 'lunch', i);
          act.afternoon = this.pickActivity(pool, 'afternoon', i);
          act.dinner = this.pickActivity(pool, 'dinner', i);
        } else if (i === days - 1) {
          act.morning = 'Hotel checkout and prepare for departure. Last-minute souvenir shopping.';
          act.lunch = 'Lunch at airport or en route to airport.';
          act.afternoon = 'Transfer to airport, check-in, and security.';
          act.dinner = 'In-flight meal or dinner at departure airport.';
          act.notes = 'Departure day. Arrive at airport 3 hours before international flight.';
        } else {
          act.morning = this.pickActivity(pool, 'morning', i);
          act.lunch = this.pickActivity(pool, 'lunch', i);
          act.afternoon = this.pickActivity(pool, 'afternoon', i);
          act.dinner = this.pickActivity(pool, 'dinner', i);

          // Add day-specific notes
          var dayNotes = this.getDayNotes(i, days, city);
          if (dayNotes) act.notes = dayNotes;
        }

        activities.push(act);
      }

      return activities;
    }

    static pickActivity(pool, tod, dayIndex) {
      var items = pool[tod] || [];
      if (items.length === 0) return 'Explore ' + tod;
      // Use dayIndex modulo but shuffled, so different each time
      return items[dayIndex % items.length];
    }

    static getDayNotes(dayIndex, totalDays, city) {
      var notes = [
        'Consider booking popular restaurants in advance for dinner.',
        'Stay hydrated and wear comfortable walking shoes.',
        'Check opening hours for attractions before heading out.',
        'Try to experience local transportation at least once during your stay.',
        'Take a morning walk to photograph the city before crowds arrive.',
      ];
      var midTrip = [
        'Halfway through your trip — review your remaining must-sees and adjust plans.',
        'Consider a local cooking class or cultural experience today.',
        'Take it easy today — a relaxed day is part of a great vacation.',
        'Visit a viewpoint or observation deck for panoramic city photos.',
        'Explore a neighborhood outside the tourist center for authentic experiences.',
      ];
      var pool = dayIndex < totalDays / 2 ? notes : midTrip;
      return pool[dayIndex % pool.length];
    }

    static getPackingList(weather, budget) {
      var base = [
        'Passport & photocopies',
        'Travel insurance documents',
        'Credit/debit cards & emergency cash',
        'Smartphone & charger cables',
        'Universal power adapter',
        'Comfortable walking shoes (already broken in)',
        'Casual clothing sets (3-4)',
        'Underwear & socks (1 pair per day + 2 extra)',
        'Light jacket or hoodie',
        'Toiletries travel kit (toothbrush, deodorant, etc.)',
        'Prescription medications + basic first aid kit',
        'Sunscreen SPF 50+ & lip balm with SPF',
        'Reusable water bottle',
        'Power bank (10,000 mAh+)',
        'Small backpack/daypack for excursions'
      ];

      var avgTemp = 25;
      var matches = (weather.temp || '').match(/(\d+)/g);
      if (matches && matches.length > 0) {
        var sum = 0;
        for (var i = 0; i < matches.length; i++) sum += parseInt(matches[i], 10);
        avgTemp = sum / matches.length;
      }

      if (avgTemp > 30) {
        base.push('Sunglasses & wide-brim hat');
        base.push('Cooling towel or small fan');
        base.push('Electrolyte packets for hydration');
      }
      if (avgTemp > 25) {
        base.push('Rain jacket or collapsible umbrella');
        base.push('Breathable fabrics (linen, cotton)');
      }
      if (avgTemp > 10 && avgTemp <= 25) {
        base.push('Versatile layers (cardigan, fleece)');
        base.push('Light scarf for wind or sun protection');
      }
      if (avgTemp <= 10) {
        base.push('Thermal underwear (top & bottom)');
        base.push('Insulated winter coat');
        base.push('Warm hat, gloves, scarf');
        base.push('Wool socks (thick)');
      }

      if (weather.conditions && (weather.conditions.toLowerCase().indexOf('rain') !== -1 || weather.conditions.toLowerCase().indexOf('monsoon') !== -1)) {
        base.push('Waterproof jacket or poncho');
        base.push('Water-resistant shoes');
        base.push('Dry bag for electronics');
      }

      if (budget === 'budget') {
        base.push('Local SIM card or eSIM data plan');
        base.push('Padlock for hostel lockers');
        base.push('Earplugs & sleep mask');
      }

      return base;
    }

    static generateVisaItinerary(tripData, dailyItinerary) {
      var visaItinerary = [];
      var startDate = new Date(tripData.departure);
      var destData = tripData.destinationData || {};
      var city = destData.city || tripData.destination;

      for (var i = 0; i < tripData.days; i++) {
        var date = new Date(startDate);
        date.setDate(date.getDate() + i);
        var dateStr = date.toISOString().split('T')[0];
        var dayNum = i + 1;

        visaItinerary.push({
          date: dateStr,
          day: 'Day ' + dayNum,
          activity: this.getVisaActivityDescription(dailyItinerary[i]),
          accommodation: city
        });
      }

      return visaItinerary;
    }

    static getVisaActivityDescription(dayActivity) {
      if (!dayActivity) return 'TBD';
      var parts = [];
      if (dayActivity.morning) parts.push(dayActivity.morning);
      if (dayActivity.lunch) parts.push(dayActivity.lunch);
      if (dayActivity.afternoon) parts.push(dayActivity.afternoon);
      if (dayActivity.dinner) parts.push(dayActivity.dinner);
      return parts.join(' | ') || 'Tourism activities';
    }
  }

  window.TravelAIEngine = TravelAIEngine;
})();
