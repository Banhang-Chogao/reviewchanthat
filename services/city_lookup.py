#!/usr/bin/env python3
"""
City lookup service for travel planner destination search.

Provides endpoint for searching cities/airports by name or IATA code.
Uses aviationstack.com API with fallback to local cache.
"""

import os
import json
import time
import requests
from typing import Optional, Dict, List
from urllib.parse import quote

# Configuration
AVIATIONSTACK_API_KEY = os.environ.get('AVIATIONSTACK_API_KEY', '')
AVIATIONSTACK_API_URL = 'https://api.aviationstack.com/v1'
CACHE_TTL = 30 * 60  # 30 minutes
MAX_RESULTS = 10
REQUEST_TIMEOUT = 5

# Local fallback cache
FALLBACK_CITIES = {
    'ICN': {
        'city': 'Incheon',
        'airport_name': 'Incheon International Airport',
        'country': 'South Korea',
        'iata': 'ICN',
        'timezone': 'Asia/Seoul',
        'flag': '🇰🇷',
        'latitude': 37.4602,
        'longitude': 126.4407
    },
    'NRT': {
        'city': 'Tokyo',
        'airport_name': 'Narita International Airport',
        'country': 'Japan',
        'iata': 'NRT',
        'timezone': 'Asia/Tokyo',
        'flag': '🇯🇵',
        'latitude': 35.7653,
        'longitude': 140.3931
    },
    'HND': {
        'city': 'Tokyo',
        'airport_name': 'Haneda Airport',
        'country': 'Japan',
        'iata': 'HND',
        'timezone': 'Asia/Tokyo',
        'flag': '🇯🇵',
        'latitude': 35.5494,
        'longitude': 139.7798
    },
    'KIX': {
        'city': 'Osaka',
        'airport_name': 'Kansai International Airport',
        'country': 'Japan',
        'iata': 'KIX',
        'timezone': 'Asia/Tokyo',
        'flag': '🇯🇵',
        'latitude': 34.4275,
        'longitude': 135.2307
    },
    'BKK': {
        'city': 'Bangkok',
        'airport_name': 'Suvarnabhumi Airport',
        'country': 'Thailand',
        'iata': 'BKK',
        'timezone': 'Asia/Bangkok',
        'flag': '🇹🇭',
        'latitude': 13.6923,
        'longitude': 100.7501
    },
    'SIN': {
        'city': 'Singapore',
        'airport_name': 'Singapore Changi Airport',
        'country': 'Singapore',
        'iata': 'SIN',
        'timezone': 'Asia/Singapore',
        'flag': '🇸🇬',
        'latitude': 1.3521,
        'longitude': 103.8198
    },
    'SGN': {
        'city': 'Ho Chi Minh City',
        'airport_name': 'Tan Son Nhat Airport',
        'country': 'Vietnam',
        'iata': 'SGN',
        'timezone': 'Asia/Ho_Chi_Minh',
        'flag': '🇻🇳',
        'latitude': 10.8174,
        'longitude': 106.7331
    },
    'HAN': {
        'city': 'Hanoi',
        'airport_name': 'Noi Bai International Airport',
        'country': 'Vietnam',
        'iata': 'HAN',
        'timezone': 'Asia/Ho_Chi_Minh',
        'flag': '🇻🇳',
        'latitude': 21.0285,
        'longitude': 105.8038
    },
    'CDG': {
        'city': 'Paris',
        'airport_name': 'Charles de Gaulle Airport',
        'country': 'France',
        'iata': 'CDG',
        'timezone': 'Europe/Paris',
        'flag': '🇫🇷',
        'latitude': 49.0097,
        'longitude': 2.5479
    },
    'DXB': {
        'city': 'Dubai',
        'airport_name': 'Dubai International Airport',
        'country': 'UAE',
        'iata': 'DXB',
        'timezone': 'Asia/Dubai',
        'flag': '🇦🇪',
        'latitude': 25.2528,
        'longitude': 55.3644
    },
    'LHR': {
        'city': 'London',
        'airport_name': 'Heathrow Airport',
        'country': 'United Kingdom',
        'iata': 'LHR',
        'timezone': 'Europe/London',
        'flag': '🇬🇧',
        'latitude': 51.4700,
        'longitude': -0.4543
    },
}

COUNTRY_FLAGS = {
    'South Korea': '🇰🇷',
    'Japan': '🇯🇵',
    'Thailand': '🇹🇭',
    'Vietnam': '🇻🇳',
    'Singapore': '🇸🇬',
    'France': '🇫🇷',
    'UAE': '🇦🇪',
    'United Kingdom': '🇬🇧',
    'United States': '🇺🇸',
    'China': '🇨🇳',
    'India': '🇮🇳',
    'Australia': '🇦🇺',
    'Germany': '🇩🇪',
    'Italy': '🇮🇹',
    'Spain': '🇪🇸',
}

# In-memory cache
_cache = {}


class CityLookupService:
    """Service for looking up cities and airports."""

    @staticmethod
    def search(query: str) -> List[Dict]:
        """
        Search for cities/airports by name or IATA code.

        Args:
            query: Search term (city name or IATA code)

        Returns:
            List of matching cities/airports with metadata
        """
        if not query or len(query) < 2:
            return []

        # Check cache
        cached = _cache.get(query)
        if cached and time.time() - cached['timestamp'] < CACHE_TTL:
            return cached['results']

        # Try API
        if AVIATIONSTACK_API_KEY:
            results = CityLookupService._search_api(query)
            if results:
                _cache[query] = {
                    'results': results,
                    'timestamp': time.time()
                }
                return results

        # Fallback to local cache
        results = CityLookupService._search_fallback(query)
        _cache[query] = {
            'results': results,
            'timestamp': time.time()
        }
        return results

    @staticmethod
    def _search_api(query: str) -> Optional[List[Dict]]:
        """Search using aviationstack API."""
        try:
            # Try cities endpoint first
            response = requests.get(
                f'{AVIATIONSTACK_API_URL}/cities',
                params={
                    'access_key': AVIATIONSTACK_API_KEY,
                    'search': query,
                    'limit': MAX_RESULTS
                },
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            cities = response.json().get('data', [])
            if cities:
                results = []
                for city in cities:
                    results.append(CityLookupService._format_city(city))
                return results

            # If cities endpoint fails, try airports
            response = requests.get(
                f'{AVIATIONSTACK_API_URL}/airports',
                params={
                    'access_key': AVIATIONSTACK_API_KEY,
                    'search': query,
                    'limit': MAX_RESULTS
                },
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            airports = response.json().get('data', [])
            if airports:
                return [CityLookupService._format_airport(a) for a in airports]

        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            print(f'API lookup failed: {e}')

        return None

    @staticmethod
    def _search_fallback(query: str) -> List[Dict]:
        """Search local fallback cache."""
        query_lower = query.lower()
        results = []

        for iata, city_data in FALLBACK_CITIES.items():
            if (query_lower in city_data['city'].lower() or
                query_lower in city_data.get('airport_name', '').lower() or
                query_lower in iata.lower() or
                query_lower in city_data['country'].lower()):
                results.append(city_data)

        return results[:MAX_RESULTS]

    @staticmethod
    def _format_city(city_data: Dict) -> Dict:
        """Format city data from API."""
        country = city_data.get('country_name', '')
        return {
            'city': city_data.get('city_name', ''),
            'country': country,
            'iata': city_data.get('iata_code', ''),
            'timezone': city_data.get('timezone', ''),
            'flag': COUNTRY_FLAGS.get(country, '🌍'),
            'latitude': float(city_data.get('latitude', 0)) if city_data.get('latitude') else None,
            'longitude': float(city_data.get('longitude', 0)) if city_data.get('longitude') else None,
        }

    @staticmethod
    def _format_airport(airport_data: Dict) -> Dict:
        """Format airport data from API."""
        country = airport_data.get('country_name', '')
        return {
            'city': airport_data.get('city_name', ''),
            'airport_name': airport_data.get('airport_name', ''),
            'country': country,
            'iata': airport_data.get('iata_code', ''),
            'timezone': airport_data.get('timezone', ''),
            'flag': COUNTRY_FLAGS.get(country, '🌍'),
            'latitude': float(airport_data.get('latitude', 0)) if airport_data.get('latitude') else None,
            'longitude': float(airport_data.get('longitude', 0)) if airport_data.get('longitude') else None,
        }


def search_destination(query: str) -> Dict:
    """
    HTTP endpoint for destination search.

    Usage:
        GET /api/destination/search?q=Seoul

    Returns:
        {
            "success": true,
            "query": "Seoul",
            "results": [...],
            "count": N,
            "timestamp": "2026-07-11T..."
        }
    """
    results = CityLookupService.search(query)

    return {
        'success': True,
        'query': query,
        'results': results,
        'count': len(results),
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }


# CLI for testing
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage: python3 city_lookup.py <query>')
        sys.exit(1)

    query = sys.argv[1]
    result = search_destination(query)
    print(json.dumps(result, indent=2, ensure_ascii=False))
