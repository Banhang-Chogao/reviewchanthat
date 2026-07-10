import fetch from 'node-fetch';

const AVIATIONSTACK_API_KEY = process.env.AVIATIONSTACK_API_KEY;

// Local fallback cities
const FALLBACK_CITIES = {
  'ICN': { city: 'Incheon', country: 'South Korea', iata: 'ICN', timezone: 'Asia/Seoul', flag: '🇰🇷' },
  'NRT': { city: 'Tokyo', country: 'Japan', iata: 'NRT', timezone: 'Asia/Tokyo', flag: '🇯🇵' },
  'BKK': { city: 'Bangkok', country: 'Thailand', iata: 'BKK', timezone: 'Asia/Bangkok', flag: '🇹🇭' },
  'SGN': { city: 'Ho Chi Minh City', country: 'Vietnam', iata: 'SGN', timezone: 'Asia/Ho_Chi_Minh', flag: '🇻🇳' },
  'HAN': { city: 'Hanoi', country: 'Vietnam', iata: 'HAN', timezone: 'Asia/Ho_Chi_Minh', flag: '🇻🇳' },
  'CDG': { city: 'Paris', country: 'France', iata: 'CDG', timezone: 'Europe/Paris', flag: '🇫🇷' },
  'DXB': { city: 'Dubai', country: 'UAE', iata: 'DXB', timezone: 'Asia/Dubai', flag: '🇦🇪' },
  'SIN': { city: 'Singapore', country: 'Singapore', iata: 'SIN', timezone: 'Asia/Singapore', flag: '🇸🇬' }
};

async function searchDestination(query) {
  if (!query || query.length < 2) {
    return [];
  }

  try {
    // Try Aviationstack API
    const response = await fetch(
      `https://api.aviationstack.com/v1/cities?access_key=${AVIATIONSTACK_API_KEY}&search=${encodeURIComponent(query)}&limit=10`
    );

    if (response.ok) {
      const data = await response.json();
      if (data.data && data.data.length > 0) {
        return data.data.map(city => ({
          city: city.city_name,
          country: city.country_name,
          iata: city.iata_code || '',
          timezone: city.timezone || '',
          flag: getCountryFlag(city.country_name),
          latitude: city.latitude,
          longitude: city.longitude
        }));
      }
    }

    // Try airports endpoint
    const airportResponse = await fetch(
      `https://api.aviationstack.com/v1/airports?access_key=${AVIATIONSTACK_API_KEY}&search=${encodeURIComponent(query)}&limit=10`
    );

    if (airportResponse.ok) {
      const data = await airportResponse.json();
      if (data.data && data.data.length > 0) {
        return data.data.map(airport => ({
          city: airport.city_name,
          airport_name: airport.airport_name,
          country: airport.country_name,
          iata: airport.iata_code || '',
          timezone: airport.timezone || '',
          flag: getCountryFlag(airport.country_name),
          latitude: airport.latitude,
          longitude: airport.longitude
        }));
      }
    }
  } catch (error) {
    console.error('Aviationstack API error:', error.message);
  }

  // Fallback to local cities
  return Object.values(FALLBACK_CITIES).filter(city =>
    city.city.toLowerCase().includes(query.toLowerCase()) ||
    city.iata.toLowerCase().includes(query.toLowerCase())
  );
}

function getCountryFlag(country) {
  const flagMap = {
    'South Korea': '🇰🇷', 'Japan': '🇯🇵', 'Thailand': '🇹🇭',
    'Vietnam': '🇻🇳', 'Singapore': '🇸🇬', 'France': '🇫🇷',
    'UAE': '🇦🇪', 'United Kingdom': '🇬🇧', 'China': '🇨🇳',
    'India': '🇮🇳', 'Australia': '🇦🇺', 'United States': '🇺🇸'
  };
  return flagMap[country] || '🌍';
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', 'application/json');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  const q = req.query.q;

  if (!q) {
    res.status(400).json({ error: 'Missing query parameter: q' });
    return;
  }

  try {
    const results = await searchDestination(q);
    res.status(200).json({
      success: true,
      query: q,
      results
    });
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({
      success: false,
      query: q,
      error: error.message,
      results: []
    });
  }
}
