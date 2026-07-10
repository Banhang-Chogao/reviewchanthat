#!/usr/bin/env python3
"""
Destination Context Builder

Normalizes destination data into canonical form for structured itinerary generation.
Never relies on LLM knowledge - uses verified geographic data only.
"""

from typing import Dict, Any, Optional
import json
from datetime import datetime

# Import from city_lookup service
from services.city_lookup import CityLookupService


class DestinationContext:
    """Build canonical destination context for AI planning."""

    # Timezone mapping (ISO 3166-1 alpha-2 → IANA timezone)
    TIMEZONE_MAP = {
        'VN': 'Asia/Ho_Chi_Minh',
        'TH': 'Asia/Bangkok',
        'JP': 'Asia/Tokyo',
        'KR': 'Asia/Seoul',
        'SG': 'Asia/Singapore',
        'MY': 'Asia/Kuala_Lumpur',
        'ID': 'Asia/Jakarta',
        'PH': 'Asia/Manila',
        'TW': 'Asia/Taipei',
        'CN': 'Asia/Shanghai',
        'IN': 'Asia/Kolkata',
        'FR': 'Europe/Paris',
        'GB': 'Europe/London',
        'DE': 'Europe/Berlin',
        'IT': 'Europe/Rome',
        'ES': 'Europe/Madrid',
        'US': 'America/New_York',
        'CA': 'America/Toronto',
        'AU': 'Australia/Sydney',
        'NZ': 'Pacific/Auckland',
        'AE': 'Asia/Dubai',
    }

    # Currency mapping (ISO 3166-1 alpha-2 → currency code)
    CURRENCY_MAP = {
        'VN': 'VND',
        'TH': 'THB',
        'JP': 'JPY',
        'KR': 'KRW',
        'SG': 'SGD',
        'MY': 'MYR',
        'ID': 'IDR',
        'PH': 'PHP',
        'TW': 'TWD',
        'CN': 'CNY',
        'IN': 'INR',
        'FR': 'EUR',
        'GB': 'GBP',
        'DE': 'EUR',
        'IT': 'EUR',
        'ES': 'EUR',
        'US': 'USD',
        'CA': 'CAD',
        'AU': 'AUD',
        'NZ': 'NZD',
        'AE': 'AED',
    }

    # Language mapping (ISO 3166-1 alpha-2 → primary language code)
    LANGUAGE_MAP = {
        'VN': 'vi',
        'TH': 'th',
        'JP': 'ja',
        'KR': 'ko',
        'SG': 'en',
        'MY': 'ms',
        'ID': 'id',
        'PH': 'en',
        'TW': 'zh-TW',
        'CN': 'zh-CN',
        'IN': 'en',
        'FR': 'fr',
        'GB': 'en',
        'DE': 'de',
        'IT': 'it',
        'ES': 'es',
        'US': 'en',
        'CA': 'en',
        'AU': 'en',
        'NZ': 'en',
        'AE': 'ar',
    }

    @staticmethod
    def build(destination_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build canonical destination context from search result.

        Args:
            destination_data: From city_lookup API

        Returns:
            Normalized destination context with all required fields
        """
        city = destination_data.get('city', '')
        country = destination_data.get('country', '')
        iata = destination_data.get('iata', '')
        iso2 = destination_data.get('iso2', '')

        # Try to deduce ISO2 if missing
        if not iso2 and iata:
            iso2 = DestinationContext._iata_to_iso2(iata)

        # Build canonical context
        context = {
            'city': city,
            'country': country,
            'iso2': iso2,
            'iso3': DestinationContext._iso2_to_iso3(iso2),
            'iata_code': iata,
            'airport_name': destination_data.get('airport_name', ''),
            'timezone': DestinationContext.TIMEZONE_MAP.get(iso2, 'UTC'),
            'currency': DestinationContext.CURRENCY_MAP.get(iso2, 'USD'),
            'language': DestinationContext.LANGUAGE_MAP.get(iso2, 'en'),
            'latitude': destination_data.get('latitude'),
            'longitude': destination_data.get('longitude'),
            'administrative_region': destination_data.get('administrative_region', ''),
            'flag': destination_data.get('flag', '🌍'),
            'context_built_at': datetime.utcnow().isoformat() + 'Z',
            'confidence': 'high' if all([city, country, iso2]) else 'medium'
        }

        return context

    @staticmethod
    def _iata_to_iso2(iata: str) -> str:
        """Deduce ISO2 from IATA code."""
        iata_to_iso2_map = {
            'ICN': 'KR', 'NRT': 'JP', 'HND': 'JP', 'KIX': 'JP',
            'BKK': 'TH', 'SIN': 'SG', 'SGN': 'VN', 'HAN': 'VN',
            'CDG': 'FR', 'DXB': 'AE', 'LHR': 'GB', 'PUS': 'KR',
            'CTS': 'JP', 'CIX': 'MY', 'CGK': 'ID', 'MNL': 'PH',
            'TPE': 'TW', 'PVG': 'CN', 'DEL': 'IN', 'ORY': 'FR',
            'TXL': 'DE', 'FCO': 'IT', 'MAD': 'ES', 'JFK': 'US',
        }
        return iata_to_iso2_map.get(iata, '')

    @staticmethod
    def _iso2_to_iso3(iso2: str) -> str:
        """Convert ISO 3166-1 alpha-2 to alpha-3."""
        iso2_to_iso3_map = {
            'VN': 'VNM', 'TH': 'THA', 'JP': 'JPN', 'KR': 'KOR',
            'SG': 'SGP', 'MY': 'MYS', 'ID': 'IDN', 'PH': 'PHL',
            'TW': 'TWN', 'CN': 'CHN', 'IN': 'IND', 'FR': 'FRA',
            'GB': 'GBR', 'DE': 'DEU', 'IT': 'ITA', 'ES': 'ESP',
            'US': 'USA', 'CA': 'CAN', 'AU': 'AUS', 'NZ': 'NZL',
            'AE': 'ARE',
        }
        return iso2_to_iso3_map.get(iso2, '')

    @staticmethod
    def validate(context: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate destination context completeness.

        Returns:
            (is_valid, list of missing fields)
        """
        required_fields = ['city', 'country', 'iso2', 'iata_code', 'timezone', 'currency']
        missing = [f for f in required_fields if not context.get(f)]

        return len(missing) == 0, missing


class DestinationContextCache:
    """Simple in-memory cache for destination contexts (TTL: 30 days)."""

    def __init__(self):
        self._cache: Dict[str, tuple[Dict[str, Any], datetime]] = {}
        self.ttl_seconds = 30 * 24 * 60 * 60  # 30 days

    def get(self, destination_id: str) -> Optional[Dict[str, Any]]:
        """Get cached destination context if not expired."""
        if destination_id not in self._cache:
            return None

        context, created_at = self._cache[destination_id]
        age = (datetime.utcnow() - created_at).total_seconds()

        if age > self.ttl_seconds:
            del self._cache[destination_id]
            return None

        return context

    def set(self, destination_id: str, context: Dict[str, Any]):
        """Cache destination context."""
        self._cache[destination_id] = (context, datetime.utcnow())

    def clear(self):
        """Clear entire cache."""
        self._cache.clear()


# Global cache instance
_destination_cache = DestinationContextCache()


def get_destination_context(destination_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get or build destination context with caching.

    Args:
        destination_data: From city_lookup API

    Returns:
        Canonical destination context
    """
    # Use IATA as cache key
    cache_key = destination_data.get('iata', destination_data.get('city', ''))

    # Check cache
    cached = _destination_cache.get(cache_key)
    if cached:
        return cached

    # Build context
    context = DestinationContext.build(destination_data)

    # Validate
    is_valid, missing = DestinationContext.validate(context)
    if not is_valid:
        print(f'Warning: Destination context incomplete, missing: {missing}')

    # Cache
    _destination_cache.set(cache_key, context)

    return context
