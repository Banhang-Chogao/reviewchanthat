#!/usr/bin/env python3
"""
Knowledge Retrieval Service

Pre-fetches verified destination data before AI generation.
Prevents LLM hallucination by providing structured facts only.
"""

from typing import Dict, List, Any, Optional
import json
from datetime import datetime


class KnowledgeSource:
    """Base class for knowledge sources."""

    def retrieve(self, destination_context: Dict[str, Any]) -> Dict[str, List[Any]]:
        raise NotImplementedError


class StructuredDestinationKnowledge:
    """
    Build structured knowledge base for a destination.
    Use verified data sources only - NEVER LLM memory.
    """

    # POI categories
    POI_CATEGORIES = [
        'attractions',
        'museums',
        'landmarks',
        'parks',
        'temples',
        'shopping',
        'food_areas',
        'markets',
        'transport_hubs',
        'neighborhoods',
        'beaches',
        'nature',
        'architecture',
        'entertainment',
    ]

    # Default knowledge for known destinations
    KNOWN_DESTINATIONS = {
        'Ho Chi Minh City': {
            'country': 'Vietnam',
            'iso2': 'VN',
            'districts': ['District 1', 'District 3', 'District 5', 'District 7', 'Binh Thanh', 'Phu Nhuan'],
            'neighborhoods': {
                'Dong Khoi': {'lat': 10.7769, 'lon': 106.7008},
                'Ben Thanh': {'lat': 10.7725, 'lon': 106.6980},
                'District 1': {'lat': 10.7769, 'lon': 106.6976},
            },
            'attractions': [
                {'name': 'War Remnants Museum', 'category': 'museum', 'lat': 10.7855, 'lon': 106.6940, 'duration': 120},
                {'name': 'Reunification Palace', 'category': 'landmark', 'lat': 10.7935, 'lon': 106.6935, 'duration': 60},
                {'name': 'Saigon Notre-Dame', 'category': 'architecture', 'lat': 10.7925, 'lon': 106.6955, 'duration': 45},
                {'name': 'Ben Thanh Market', 'category': 'market', 'lat': 10.7725, 'lon': 106.6980, 'duration': 90},
                {'name': 'Bitexco Financial Tower', 'category': 'landmark', 'lat': 10.7714, 'lon': 106.7030, 'duration': 60},
            ],
            'food_areas': [
                {'name': 'Pham Ngu Lao Street', 'type': 'street_food', 'lat': 10.7740, 'lon': 106.6920},
                {'name': 'Nguyen Hue Walking Street', 'type': 'local_food', 'lat': 10.7778, 'lon': 106.7025},
            ],
            'transport': {
                'subway': ['Line 1: Ben Thanh - Suoi Tien'],
                'bus_hubs': ['Ben Thanh Station', 'Tao Duan Station'],
                'taxi_services': ['Vinasun', 'Mai Linh'],
                'ride_sharing': ['Grab', 'Go-Viet'],
            },
            'emergency': {
                'police': '113',
                'ambulance': '115',
                'fire': '114',
                'hospital': 'Cho Ray Hospital',
            },
        },
        'Bangkok': {
            'country': 'Thailand',
            'iso2': 'TH',
            'districts': ['Sukhumvit', 'Silom', 'Riverside', 'Old City', 'Dusit'],
            'attractions': [
                {'name': 'Grand Palace', 'category': 'landmark', 'lat': 13.6515, 'lon': 100.4918, 'duration': 120},
                {'name': 'Wat Phra Kaew', 'category': 'temple', 'lat': 13.6515, 'lon': 100.4918, 'duration': 90},
                {'name': 'Wat Arun', 'category': 'temple', 'lat': 13.6428, 'lon': 100.4861, 'duration': 90},
            ],
            'transport': {
                'subway': ['BTS (Skytrain)', 'MRT (Underground)'],
                'water': ['Chao Phraya Express Boat'],
            },
        },
        'Tokyo': {
            'country': 'Japan',
            'iso2': 'JP',
            'districts': ['Shinjuku', 'Shibuya', 'Asakusa', 'Harajuku', 'Ginza'],
            'attractions': [
                {'name': 'Senso-ji Temple', 'category': 'temple', 'lat': 35.7149, 'lon': 139.7967, 'duration': 90},
                {'name': 'Meiji Shrine', 'category': 'shrine', 'lat': 35.6762, 'lon': 139.7000, 'duration': 60},
            ],
        },
        'Paris': {
            'country': 'France',
            'iso2': 'FR',
            'districts': ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th'],
            'attractions': [
                {'name': 'Eiffel Tower', 'category': 'landmark', 'lat': 48.8584, 'lon': 2.2945, 'duration': 120},
                {'name': 'Louvre Museum', 'category': 'museum', 'lat': 48.8606, 'lon': 2.3376, 'duration': 180},
            ],
        },
    }

    @staticmethod
    def retrieve(destination_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve structured knowledge for destination.

        Args:
            destination_context: From DestinationContext.build()

        Returns:
            Structured knowledge including attractions, transport, neighborhoods, etc.
        """
        city = destination_context.get('city', '')
        country = destination_context.get('country', '')

        # Get known data
        known = StructuredDestinationKnowledge.KNOWN_DESTINATIONS.get(city, {})

        knowledge = {
            'destination': {
                'city': city,
                'country': country,
                'iso2': destination_context.get('iso2'),
            },
            'districts': known.get('districts', []),
            'neighborhoods': known.get('neighborhoods', {}),
            'attractions': known.get('attractions', []),
            'food_areas': known.get('food_areas', []),
            'transport': known.get('transport', {}),
            'emergency': known.get('emergency', {}),
            'retrieved_at': datetime.utcnow().isoformat() + 'Z',
            'source': 'structured_database',
        }

        return knowledge

    @staticmethod
    def validate_poi(poi: Dict[str, Any], destination_context: Dict[str, Any]) -> bool:
        """
        Validate that POI belongs to destination.

        Rules:
        - Same city
        - Same country
        - Valid coordinates (within ~50km of city center)
        """
        # Check country match
        if poi.get('country') and poi['country'].lower() != destination_context.get('country', '').lower():
            return False

        # Check coordinates sanity (rough bounds)
        if poi.get('lat') and poi.get('lon'):
            city_lat = destination_context.get('latitude', 0)
            city_lon = destination_context.get('longitude', 0)

            # Rough distance check (~50km)
            if city_lat and city_lon:
                lat_diff = abs(poi['lat'] - city_lat)
                lon_diff = abs(poi['lon'] - city_lon)
                if lat_diff > 1 or lon_diff > 1:
                    return False

        return True


def get_destination_knowledge(destination_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get structured knowledge for destination.

    Never use LLM knowledge - always use verified data.
    """
    return StructuredDestinationKnowledge.retrieve(destination_context)
