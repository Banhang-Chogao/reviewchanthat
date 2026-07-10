#!/usr/bin/env python3
"""
Test Hybrid Planning Pipeline

Validates each stage of the 10-stage pipeline.
"""

import sys
sys.path.insert(0, '/Users/duynguyen/Desktop/reviewchanthat')

from services.destination_context import DestinationContext, get_destination_context
from services.knowledge_retriever import StructuredDestinationKnowledge
from services.route_optimizer import RouteOptimizer, DayScheduler
from services.quality_validator import QualityValidator, GeographicValidator


def test_destination_context():
    """Stage 1: Destination Context Builder"""
    print("Testing Stage 1: Destination Context Builder...")

    destination_data = {
        'city': 'Ho Chi Minh City',
        'country': 'Vietnam',
        'iata': 'SGN',
        'iso2': 'VN',
        'latitude': 10.7769,
        'longitude': 106.6976
    }

    context = get_destination_context(destination_data)

    assert context['city'] == 'Ho Chi Minh City'
    assert context['country'] == 'Vietnam'
    assert context['iso2'] == 'VN'
    assert context['timezone'] == 'Asia/Ho_Chi_Minh'
    assert context['currency'] == 'VND'
    assert context['language'] == 'vi'

    is_valid, missing = DestinationContext.validate(context)
    assert is_valid, f"Missing: {missing}"

    print("✅ Stage 1 passed")
    return context


def test_knowledge_retrieval(context):
    """Stage 2: Knowledge Retrieval"""
    print("Testing Stage 2: Knowledge Retrieval...")

    knowledge = StructuredDestinationKnowledge.retrieve(context)

    assert knowledge['destination']['city'] == 'Ho Chi Minh City'
    assert knowledge['destination']['country'] == 'Vietnam'
    assert len(knowledge['attractions']) > 0
    assert len(knowledge['districts']) > 0

    print(f"  - Found {len(knowledge['attractions'])} attractions")
    print(f"  - Found {len(knowledge['districts'])} districts")
    print("✅ Stage 2 passed")

    return knowledge


def test_poi_validation(knowledge, context):
    """Stages 3-4: POI Validation"""
    print("Testing Stages 3-4: POI Validation...")

    attractions = knowledge['attractions']

    # Test each attraction
    valid_count = 0
    for attr in attractions:
        is_valid = StructuredDestinationKnowledge.validate_poi(attr, context)
        if is_valid:
            valid_count += 1

    print(f"  - {valid_count}/{len(attractions)} POIs valid for {context['city']}")
    assert valid_count > 0

    print("✅ Stages 3-4 passed")


def test_route_optimization(knowledge):
    """Stage 5: Route Optimizer"""
    print("Testing Stage 5: Route Optimizer...")

    attractions = knowledge['attractions'][:5]  # Use first 5
    hotel_loc = {'lat': 10.7769, 'lon': 106.6976}

    # Test clustering
    clusters = RouteOptimizer.cluster_attractions(attractions)
    print(f"  - Clustered {len(attractions)} attractions into {len(clusters)} clusters")

    # Test optimization
    optimized = RouteOptimizer.optimize_route(attractions, hotel_loc)
    print(f"  - Optimized route order: {[a.get('name', 'Unknown')[:20] for a in optimized[:3]]}")

    assert len(optimized) > 0
    print("✅ Stage 5 passed")

    return optimized


def test_day_scheduler(optimized):
    """Stage 6: Day Scheduler"""
    print("Testing Stage 6: Day Scheduler...")

    hotel_loc = {'lat': 10.7769, 'lon': 106.6976}
    schedule = DayScheduler.schedule_day(optimized, hotel_loc, available_hours=8)

    print(f"  - Activities: {len(schedule['activities'])}")
    print(f"  - Total time: {schedule['total_time']} minutes")
    print(f"  - Feasible: {schedule['feasible']}")

    assert schedule['feasible']
    print("✅ Stage 6 passed")


def test_geographic_validator(context):
    """Stage 8: Geographic Validator"""
    print("Testing Stage 8: Geographic Validator...")

    # Test valid activity
    valid_activity = {
        'name': 'War Remnants Museum, Ho Chi Minh City',
        'category': 'museum',
        'latitude': 10.7855,
        'longitude': 106.6940
    }

    is_valid, reason = GeographicValidator.validate_activity(valid_activity, context)
    assert is_valid, f"Should be valid: {reason}"

    # Test invalid activity (different city)
    invalid_activity = {
        'name': 'Grand Palace, Bangkok',
        'category': 'landmark',
        'latitude': 13.6515,
        'longitude': 100.4918
    }

    is_valid, reason = GeographicValidator.validate_activity(invalid_activity, context)
    assert not is_valid, "Should be invalid"

    print("✅ Stage 8 passed")


def test_quality_validator(context):
    """Stages 9-10: Quality Validator"""
    print("Testing Stages 9-10: Quality Validator...")

    # Create test itinerary
    itinerary = {
        'destination': 'Ho Chi Minh City',
        'dailyItinerary': [
            {
                'morning': 'Visit War Remnants Museum',
                'afternoon': 'Explore Ben Thanh Market',
                'evening': 'Dinner at Pham Ngu Lao Street'
            },
            {
                'morning': 'Visit Reunification Palace',
                'afternoon': 'Walk around Dong Khoi',
                'evening': 'Visit Saigon Notre-Dame'
            }
        ],
        'hotelArea': 'District 1',
        'transportation': 'Taxi and walking',
        'emergencyNumbers': '113',
        'weatherNotes': 'Hot and humid',
        'currency': 'VND',
        'timezone': 'Asia/Ho_Chi_Minh'
    }

    is_acceptable, result = QualityValidator.is_acceptable(itinerary, context)

    print(f"  - Confidence: {result['confidence']}%")
    print(f"  - Threshold: {result['threshold']}%")
    print(f"  - Acceptable: {result['is_acceptable']}")
    print(f"  - Scores: {result['scores']}")

    # Should have reasonable confidence
    assert result['confidence'] > 50, "Confidence too low"
    print("✅ Stages 9-10 passed")


def main():
    print("=" * 60)
    print("Testing Trust-first Hybrid Planning Engine")
    print("=" * 60)
    print()

    # Run all stages
    context = test_destination_context()
    print()

    knowledge = test_knowledge_retrieval(context)
    print()

    test_poi_validation(knowledge, context)
    print()

    optimized = test_route_optimization(knowledge)
    print()

    test_day_scheduler(optimized)
    print()

    test_geographic_validator(context)
    print()

    test_quality_validator(context)
    print()

    print("=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)


if __name__ == '__main__':
    main()
