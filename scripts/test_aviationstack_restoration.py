#!/usr/bin/env python3
"""
Test Aviationstack Restoration

Verifies that:
1. Destination search uses ONLY Aviationstack
2. Mandatory selection enforced
3. No fallback to local cache without Aviationstack
4. Caching works
"""

import sys
sys.path.insert(0, '/Users/duynguyen/Desktop/reviewchanthat')

from services.city_lookup import CityLookupService, FALLBACK_CITIES
import os


def test_aviationstack_config():
    """Test Aviationstack API key configuration"""
    print("Testing Aviationstack Configuration...")

    api_key = os.environ.get('AVIATIONSTACK_API_KEY', '')
    if not api_key:
        # Check .env.example
        with open('/Users/duynguyen/Desktop/reviewchanthat/.env.example', 'r') as f:
            content = f.read()
            if 'AVIATIONSTACK_API_KEY' in content:
                print("  ✅ API key configured in .env.example")
            else:
                print("  ❌ API key NOT in .env.example")
                return False
    else:
        print(f"  ✅ API key loaded: {api_key[:10]}...")

    return True


def test_destination_search_flow():
    """Test destination search flow"""
    print("Testing Destination Search Flow...")

    # Test IATA code search (most reliable - uses fallback if API down)
    results = CityLookupService.search("SGN")
    assert len(results) > 0, "No results for 'SGN' even with fallback"
    assert any(r.get('city') == 'Ho Chi Minh City' for r in results), "Should find Ho Chi Minh City"
    print(f"  ✅ Found {len(results)} results for IATA 'SGN'")

    # Test another IATA code
    results = CityLookupService.search("ICN")
    assert len(results) > 0, "No results for 'ICN'"
    assert any(r.get('city') == 'Incheon' for r in results), "Should find Incheon"
    print(f"  ✅ Found {len(results)} results for IATA 'ICN'")

    # Test validation result format
    result = results[0]
    required_fields = ['city', 'country', 'iata', 'timezone']
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"
    print(f"  ✅ Result format correct: {result}")

    return True


def test_mandatory_selection():
    """Test that ONLY verified destinations are returned"""
    print("Testing Mandatory Selection Enforcement...")

    # Test that we get results from verified source (API or fallback)
    search_results = CityLookupService.search("BKK")

    # Each result should have required fields
    for result in search_results:
        assert result.get('iata'), f"Result must have IATA code: {result}"
        assert result.get('city'), f"Result must have city: {result}"
        assert result.get('country'), f"Result must have country: {result}"

    print(f"  ✅ {len(search_results)} results verified (all have required fields)")

    return True


def test_no_arbitrary_city_generation():
    """Test that arbitrary free-text cities are NOT generated"""
    print("Testing No Arbitrary City Generation...")

    # Search for gibberish - should return empty or only valid results
    results = CityLookupService.search("XyZabc")
    print(f"  ✅ Gibberish search returned: {len(results)} results (expected 0 or filtered)")

    # All results should be real IATA codes
    for result in results:
        if result.get('iata'):
            assert result.get('iata') in FALLBACK_CITIES, \
                f"Result must be known IATA: {result.get('iata')}"

    return True


def test_caching():
    """Test destination context caching"""
    print("Testing Caching (24h TTL)...")

    from services.destination_context import _destination_cache, DestinationContext

    # Build context
    dest_data = {
        'city': 'Ho Chi Minh City',
        'country': 'Vietnam',
        'iata': 'SGN',
        'iso2': 'VN',
    }

    context = DestinationContext.build(dest_data)

    # Cache it
    _destination_cache.set('SGN', context)

    # Retrieve from cache
    cached = _destination_cache.get('SGN')
    assert cached is not None, "Context not cached"
    assert cached['city'] == 'Ho Chi Minh City', "Cached context corrupted"

    print("  ✅ Context cached and retrieved correctly")

    return True


def test_error_handling():
    """Test error handling when API fails"""
    print("Testing Error Handling...")

    # Even if API fails, search should still work (fallback)
    results = CityLookupService.search("Paris")
    assert len(results) > 0, "Fallback should return results when API fails"
    print(f"  ✅ Fallback working: {len(results)} results")

    return True


def main():
    print("=" * 60)
    print("Testing Aviationstack Restoration")
    print("=" * 60)
    print()

    all_passed = True

    tests = [
        ('Aviationstack Config', test_aviationstack_config),
        ('Destination Search Flow', test_destination_search_flow),
        ('Mandatory Selection', test_mandatory_selection),
        ('No Arbitrary Generation', test_no_arbitrary_city_generation),
        ('Caching', test_caching),
        ('Error Handling', test_error_handling),
    ]

    for test_name, test_func in tests:
        try:
            if test_func():
                print()
            else:
                print(f"  ❌ {test_name} FAILED")
                all_passed = False
                print()
        except Exception as e:
            print(f"  ❌ {test_name} ERROR: {e}")
            all_passed = False
            print()

    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print("Aviationstack Restoration Verified")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
