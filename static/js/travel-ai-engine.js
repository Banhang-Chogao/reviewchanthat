(function() {
  'use strict';

  const IATA_DATABASE = {
    'ICN': { city: 'Incheon', country: 'South Korea', timezone: 'Asia/Seoul' },
    'NRT': { city: 'Tokyo', country: 'Japan', timezone: 'Asia/Tokyo' },
    'HND': { city: 'Tokyo', country: 'Japan', timezone: 'Asia/Tokyo' },
    'KIX': { city: 'Osaka', country: 'Japan', timezone: 'Asia/Tokyo' },
    'BKK': { city: 'Bangkok', country: 'Thailand', timezone: 'Asia/Bangkok' },
    'SIN': { city: 'Singapore', country: 'Singapore', timezone: 'Asia/Singapore' },
    'SGN': { city: 'Ho Chi Minh City', country: 'Vietnam', timezone: 'Asia/Ho_Chi_Minh' },
    'HAN': { city: 'Hanoi', country: 'Vietnam', timezone: 'Asia/Ho_Chi_Minh' },
    'CDG': { city: 'Paris', country: 'France', timezone: 'Europe/Paris' },
    'DXB': { city: 'Dubai', country: 'UAE', timezone: 'Asia/Dubai' },
    'LHR': { city: 'London', country: 'UK', timezone: 'Europe/London' }
  };

  const WEATHER_PATTERNS = {
    'ICN': { season: 'Fall/Winter', temp: '5-15°C', conditions: 'Clear, sometimes cold' },
    'NRT': { season: 'Fall', temp: '10-20°C', conditions: 'Pleasant, occasional rain' },
    'KIX': { season: 'Fall', temp: '12-22°C', conditions: 'Clear, moderate humidity' },
    'BKK': { season: 'Cool', temp: '25-35°C', conditions: 'Hot, humid, occasional rain' },
    'SIN': { season: 'Tropical', temp: '24-32°C', conditions: 'Hot, humid, frequent rain' },
    'SGN': { season: 'Cool', temp: '20-30°C', conditions: 'Warm, occasional rain' },
    'HAN': { season: 'Cool', temp: '15-25°C', conditions: 'Pleasant, clear' },
    'CDG': { season: 'Summer', temp: '15-25°C', conditions: 'Pleasant, occasional rain' },
    'DXB': { season: 'Winter', temp: '15-28°C', conditions: 'Sunny, warm days, cool nights' },
    'LHR': { season: 'Summer', temp: '12-20°C', conditions: 'Variable, frequent rain' }
  };

  const BUDGET_RANGES = {
    'luxury': { daily: 300, hotel: 150, food: 80, activities: 70 },
    'mid-range': { daily: 150, hotel: 60, food: 50, activities: 40 },
    'budget': { daily: 80, hotel: 30, food: 30, activities: 20 }
  };

  class TravelAIEngine {
    static async generateItinerary(tripData) {
      const prompt = this.buildPrompt(tripData);

      try {
        // Call backend AI service
        const response = await fetch('/api/ai/generate-itinerary', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            destination: tripData.destination,
            departure: tripData.departure,
            returnDate: tripData.returnDate,
            days: tripData.days,
            adults: tripData.adults,
            children: tripData.children,
            budget: tripData.budget,
            purposes: tripData.purposes,
            visaMode: tripData.visaMode,
            prompt: prompt
          })
        });

        if (!response.ok) {
          // Fallback to local generation
          return this.generateLocalItinerary(tripData);
        }

        const data = await response.json();
        return this.formatItinerary(data, tripData);
      } catch (error) {
        console.warn('AI API failed, using local generation:', error);
        return this.generateLocalItinerary(tripData);
      }
    }

    static buildPrompt(tripData) {
      // Use full destination data from API instead of hardcoded IATA database
      const destData = tripData.destinationData || {};
      const city = destData.city || tripData.destination;
      const country = destData.country || 'Unknown';
      const iata = destData.iata || tripData.destination;
      const timezone = destData.timezone || 'Unknown';
      const coordinates = destData.latitude && destData.longitude
        ? `${destData.latitude}, ${destData.longitude}`
        : 'Unknown';
      const budget = tripData.budget;
      const purpose = tripData.purposes.join(', ') || 'tourism';

      return `Create a professional ${tripData.days}-day travel itinerary for ${city}, ${country}.

Destination Details (DO NOT HALLUCINATE - USE THESE EXACT VALUES):
- City: ${city}
- Country: ${country}
- IATA Code: ${iata}
- Timezone: ${timezone}
- Coordinates: ${coordinates}

Trip Details:
- Duration: ${tripData.days} days (${tripData.departure} to ${tripData.returnDate})
- Travelers: ${tripData.adults} adult(s), ${tripData.children} child(ren)
- Budget Level: ${budget}
- Purpose: ${purpose}

Requirements:
1. Daily schedule with Morning, Lunch, Afternoon, Dinner activities
2. Optimize route (no backtracking, group nearby attractions)
3. Mix cultural, entertainment, dining, and rest activities
4. Include transportation tips and walking times
5. Weather-aware recommendations
6. Estimated budget breakdown
7. Packing list recommendations
8. Local emergency contacts and tips
9. Airport arrival/departure instructions
${tripData.visaMode === 'visa' ? '10. Professional visa application itinerary format' : ''}

Format as JSON with structure:
{
  "weather": "description",
  "weatherNotes": "what to pack/expect",
  "hotelArea": "recommended neighborhood",
  "transportation": "how to get around",
  "estimatedBudget": "total estimate",
  "packingList": ["item1", "item2", ...],
  "localTips": "useful information",
  "emergencyNumbers": "emergency contacts",
  "airportNotes": "airport instructions",
  "dailyItinerary": [
    {
      "morning": "activity",
      "lunch": "recommendation",
      "afternoon": "activity",
      "dinner": "recommendation",
      "notes": "special notes"
    }
  ],
  "visaItinerary": [
    {
      "date": "YYYY-MM-DD",
      "day": "Day 1",
      "activity": "description",
      "accommodation": "hotel area"
    }
  ]
}`;
    }

    static generateLocalItinerary(tripData) {
      // Use full destination data from API
      const destData = tripData.destinationData || {};
      const dest = {
        city: destData.city || tripData.destination,
        country: destData.country || 'Unknown',
        iata: destData.iata || ''
      };

      // Look up weather pattern by IATA or city name
      const weatherKey = destData.iata || tripData.destination;
      const weather = WEATHER_PATTERNS[weatherKey] || {
        season: 'Seasonal',
        temp: '20-25°C',
        conditions: 'Variable'
      };
      const budget = BUDGET_RANGES[tripData.budget];

      const days = tripData.days;
      const dailyItinerary = this.generateDailyActivities(dest, days, tripData.budget);

      return {
        weather: `${weather.season} (${weather.temp})`,
        weatherNotes: weather.conditions,
        hotelArea: this.suggestHotelArea(dest.city),
        transportation: this.suggestTransport(dest.city),
        estimatedBudget: `$${budget.daily * days} - $${budget.daily * 1.2 * days} (${tripData.adults} adult${tripData.adults > 1 ? 's' : ''}${tripData.children > 0 ? `, ${tripData.children} child(ren)` : ''})`,
        packingList: this.getPackingList(weather, tripData.budget),
        localTips: this.getLocalTips(dest.city),
        emergencyNumbers: this.getEmergencyNumbers(dest.country),
        airportNotes: this.getAirportNotes(dest.city),
        dailyItinerary: dailyItinerary,
        visaItinerary: this.generateVisaItinerary(tripData, dailyItinerary)
      };
    }

    static generateDailyActivities(dest, days, budget) {
      const activities = [];

      for (let i = 0; i < days; i++) {
        let activity = {
          morning: this.getActivity(dest.city, 'morning', i),
          lunch: this.getActivity(dest.city, 'lunch', i),
          afternoon: this.getActivity(dest.city, 'afternoon', i),
          dinner: this.getActivity(dest.city, 'dinner', i),
          notes: ''
        };

        if (i === 0) {
          activity.morning = `Arrival at airport, take AREX/taxi to hotel`;
          activity.notes = 'Rest and acclimatize, explore hotel area';
        } else if (i === days - 1) {
          activity.morning = `Hotel checkout, prepare for departure`;
          activity.lunch = 'Lunch at airport or en route';
          activity.afternoon = 'Depart for airport';
          activity.dinner = 'In-flight meal';
        }

        activities.push(activity);
      }

      return activities;
    }

    static getActivity(city, timeOfDay, dayIndex) {
      const activities = {
        'Tokyo': {
          morning: ['Visit Senso-ji Temple', 'Explore Tsukiji Market', 'Shibuya Crossing walk', 'Meiji Shrine visit'],
          lunch: ['Conveyor belt sushi', 'Ramen at Ichiran', 'Tonkatsu at Maisen', 'Izakaya lunch'],
          afternoon: ['Harajuku street fashion shopping', 'Teamlab Digital Museum', 'Shinjuku neon district', 'Museum visit'],
          dinner: ['Kaiseki experience', 'Yakitori at local izakaya', 'Okonomiyaki in Hiroshima-style', 'Tempura omakase']
        },
        'Seoul': {
          morning: ['Gyeongbokgung Palace tour', 'N Seoul Tower sunrise', 'Bukchon Hanok Village', 'Insadong art street'],
          lunch: ['Bibimbap at Myeongdong', 'Banchan experience', 'Samgyetang (ginseng chicken)', 'Korean BBQ'],
          afternoon: ['Myeongdong shopping', 'Ewha University street', 'Tricks Eye Museum', 'Gangnam district'],
          dinner: ['Korean BBQ', 'Street food at Myeongdong', 'Pojangmacha (street stall)', 'Galbijjim']
        },
        'Bangkok': {
          morning: ['Wat Phra Kaew (Grand Palace)', 'Wat Arun temple', 'Chao Phraya River cruise', 'Floating markets'],
          lunch: ['Tom Yum at Pratunam', 'Pad Thai street vendor', 'Mango sticky rice', 'Seafood at Or Tor Kor'],
          afternoon: ['Chatuchak Weekend Market', 'Lumphini Park', 'Jim Thompson House', 'Shopping mall exploration'],
          dinner: ['Rooftop bar at Vertigo', 'Street food tour', 'Thai massage + dinner', 'Riverside restaurant']
        },
        'Singapore': {
          morning: ['Gardens by the Bay', 'Marina Bay Sands observation deck', 'Merlion Park photo', 'Botanic Gardens'],
          lunch: ['Hawker center at Tiong Bahru', 'Laksa at Zion Road', 'Dim sum in Chinatown', 'Food court meal'],
          afternoon: ['Orchard Road shopping', 'National Museum', 'Arab Street exploration', 'ArtScience Museum'],
          dinner: ['Fine dining at Marina Bay', 'Chinatown street food', 'Kampong Glam experience', 'Rooftop dinner']
        },
        'Paris': {
          morning: ['Eiffel Tower visit', 'Louvre Museum', 'Arc de Triomphe', 'Notre-Dame Cathedral'],
          lunch: ['Cafe at Seine', 'Bistro classic', 'Croissant + coffee', 'Market fresh lunch'],
          afternoon: ['Sacré-Cœur basilica', 'Montmartre walk', 'Musée d\'Orsay', 'Shopping on Champs-Élysées'],
          dinner: ['Traditional bistro', 'Brasserie dinner', 'Seine river dinner cruise', 'Latin Quarter dining']
        },
        'Hanoi': {
          morning: ['Hoan Kiem Lake sunrise', 'Old Quarter exploration', 'Temple of Literature', 'Ho Tay (West Lake)'],
          lunch: ['Pho at local restaurant', 'Egg coffee with traditional Vietnamese', 'Bun Cha', 'Fresh spring rolls'],
          afternoon: ['Water puppet theater', 'Hanoi night market', 'Temple visit', 'Cycling around Old Quarter'],
          dinner: ['Street food tour', 'Traditional Vietnamese', 'Rooftop bar', 'Local market dining']
        }
      };

      const cityActivities = activities[city] || activities['Bangkok'];
      const timeActivities = cityActivities[timeOfDay] || [];

      return timeActivities[dayIndex % timeActivities.length] || `Explore ${city}`;
    }

    static suggestHotelArea(city) {
      const areas = {
        'Tokyo': 'Shinjuku, Shibuya, or Asakusa (central, good transit)',
        'Seoul': 'Myeongdong, Gangnam, or Insadong (close to attractions)',
        'Bangkok': 'Silom, Sukhumvit, or Riverside (easy BTS access)',
        'Singapore': 'Marina Bay, Chinatown, or Orchard (central, walkable)',
        'Paris': '5th/6th Arrondissement, Marais, or near Eiffel Tower',
        'Hanoi': 'Old Quarter, Hoan Kiem area (walkable, vibrant)',
        'Ho Chi Minh City': 'District 1 (Dong Khoi), Ben Thanh area',
        'Osaka': 'Dotonbori, Umeda, or Namba (central, lively)'
      };

      return areas[city] || 'Central district near main attractions';
    }

    static suggestTransport(city) {
      const transports = {
        'Tokyo': 'IC Card (Suica/Pasmo) for train/subway. Efficient rail system covers entire city.',
        'Seoul': 'T-money card for subway/bus. Clean, fast metro system with English signage.',
        'Bangkok': 'BTS Skytrain pass recommended. Tuk-tuk for local flavor (negotiate fare first).',
        'Singapore': 'EZ-Link card for MRT/bus. Uber/Grab apps work well.',
        'Paris': 'Paris Visite pass or carnet of 10 tickets. Excellent metro system.',
        'Hanoi': 'Grab/Uber for reliable transport. Taxis or motorbike taxis (Grab Bike).',
        'Ho Chi Minh City': 'Grab app for taxis/bikes. Buses available, taxis recommended.',
        'Osaka': 'ICOCA card for trains/subway. Excellent transport connections.'
      };

      return transports[city] || 'Local taxi apps (Grab/Uber) or public transport cards recommended.';
    }

    static getPackingList(weather, budget) {
      const baseList = [
        'Passport & copies',
        'Travel insurance documents',
        'Credit cards & cash',
        'Phone chargers',
        'Universal adapter',
        'Comfortable walking shoes',
        'Casual clothing (2-3 sets)',
        'Underwear & socks',
        'Light jacket/sweater',
        'Toiletries (or buy locally)',
        'Medications (if needed)',
        'Sunscreen & sunglasses',
        'Small umbrella'
      ];

      if (weather.conditions.includes('Rain') || weather.season.includes('Monsoon')) {
        baseList.push('Raincoat or poncho');
        baseList.push('Waterproof bag');
      }

      if (weather.temp.includes('5-15') || weather.temp.includes('15-') && weather.temp.includes('25')) {
        baseList.push('Layers (hoodie, long sleeves)');
      }

      if (budget === 'budget') {
        baseList.push('Reusable water bottle');
        baseList.push('Local SIM card or WiFi plans');
      }

      return baseList;
    }

    static getLocalTips(city) {
      const tips = {
        'Tokyo': 'Download Suica app. Convenience stores (7-11, Family Mart) open 24h. Free WiFi in many places.',
        'Seoul': 'Many places cash-only, also accept cards. Download Naver Map app. Street food abundant & cheap.',
        'Bangkok': 'Haggle at markets. Stay hydrated. Respect monarchy. Smile (Thai way of saying thanks).',
        'Singapore': 'Very clean & safe. Expensive compared to neighbors. Excellent food courts for budget dining.',
        'Paris': 'Book popular restaurants ahead. Say "Bonjour" when entering shops. Tipping not required.',
        'Hanoi': 'Cross streets confidently (drivers expect it). Try street food - it\'s safe & delicious. Bargain in markets.',
        'Ho Chi Minh City': 'Pho & coffee everywhere for under $2. Grab/Uber cheaper than taxis. Chaotic traffic.',
        'Osaka': 'Cash preferred at smaller shops. Less crowded than Tokyo. Great street food scene.'
      };

      return tips[city] || 'Check local customs and be respectful. Download offline maps. Learn basic phrases.';
    }

    static getEmergencyNumbers(country) {
      const numbers = {
        'Japan': '911 (Police), 119 (Ambulance/Fire)',
        'South Korea': '112 (Police), 119 (Ambulance/Fire)',
        'Thailand': '191 (Police), 1669 (Tourist Police), 1554 (Ambulance)',
        'Singapore': '999 (Police/Ambulance)',
        'France': '15 (Emergency), 17 (Police), 18 (Fire)',
        'Vietnam': '113 (Police), 114 (Fire)',
        'UAE': '999 (Emergency)',
        'UK': '999 (Emergency)'
      };

      return numbers[country] || 'Call your embassy. Local 999/911 variants exist.';
    }

    static getAirportNotes(city) {
      const notes = {
        'Tokyo': 'Narita: 60km east (Express train 1h). Haneda: 15km south (Monorail 30min). Haneda recommended.',
        'Seoul': 'Incheon: 50km west (AREX train 43min). Gimpo: 20km west (subway 30min). AREX has luggage service.',
        'Bangkok': 'Suvarnabhumi: 30km east (ARL train 28min, or Grab 45min). Luggage storage available.',
        'Singapore': 'Changi: 15km east (MRT 30min). Excellent facilities. Many lounge access options.',
        'Paris': 'CDG: 25km northeast (RER B 30min). Orly: 14km south (Orlyval 15min). CDG most international.',
        'Hanoi': 'Noi Bai: 30km north (bus/train 45min). Grab most reliable. Check ride before boarding.',
        'Dubai': 'DXB: 5km south (Metro 15min). Modern, efficient. Check visa requirements (many are visa-free).'
      };

      return notes[city] || 'Ask hotel for airport transfer recommendations. Pre-book Grab/Uber if unsure.';
    }

    static generateVisaItinerary(tripData, dailyItinerary) {
      const visaItinerary = [];
      const startDate = new Date(tripData.departure);

      for (let i = 0; i < tripData.days; i++) {
        const date = new Date(startDate);
        date.setDate(date.getDate() + i);
        const dateStr = date.toISOString().split('T')[0];
        const dayNum = i + 1;

        visaItinerary.push({
          date: dateStr,
          day: `Day ${dayNum}`,
          activity: this.getVisaActivityDescription(dailyItinerary[i]),
          accommodation: IATA_DATABASE[tripData.destination]?.city || tripData.destination
        });
      }

      return visaItinerary;
    }

    static getVisaActivityDescription(dayActivity) {
      if (!dayActivity) return 'TBD';

      const activities = [];
      if (dayActivity.morning) activities.push(dayActivity.morning);
      if (dayActivity.lunch) activities.push(dayActivity.lunch);
      if (dayActivity.afternoon) activities.push(dayActivity.afternoon);
      if (dayActivity.dinner) activities.push(dayActivity.dinner);

      return activities.join(' | ') || 'Tourism activities';
    }

    static formatItinerary(data, tripData) {
      // Parse AI response if it's a JSON string
      if (typeof data === 'string') {
        try {
          data = JSON.parse(data);
        } catch (e) {
          // Fallback to local generation
          return this.generateLocalItinerary(tripData);
        }
      }

      return {
        weather: data.weather || 'TBD',
        weatherNotes: data.weatherNotes || 'N/A',
        hotelArea: data.hotelArea || 'TBD',
        transportation: data.transportation || 'TBD',
        estimatedBudget: data.estimatedBudget || 'TBD',
        packingList: data.packingList || [],
        localTips: data.localTips || 'N/A',
        emergencyNumbers: data.emergencyNumbers || 'N/A',
        airportNotes: data.airportNotes || 'N/A',
        dailyItinerary: data.dailyItinerary || [],
        visaItinerary: data.visaItinerary || []
      };
    }
  }

  window.TravelAIEngine = TravelAIEngine;
})();
