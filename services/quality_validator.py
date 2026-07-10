#!/usr/bin/env python3
"""
Quality Validators

Post-generation validation of itinerary quality.
Ensures destination coherence, POI validity, schedule realism.
"""

from typing import Dict, List, Any, Tuple
import math


class GeographicValidator:
    """Validates that all activities belong to the selected destination."""

    @staticmethod
    def validate_activity(activity: Dict[str, Any], destination_context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate a single activity against destination.

        Rules:
        1. Activity location must be same city/country as destination
        2. Coordinates must be within ~50km of city center
        3. No mixing cities within a single activity

        Returns:
            (is_valid, reason)
        """
        city = destination_context.get('city', '').lower()
        country = destination_context.get('country', '').lower()
        dest_lat = destination_context.get('latitude')
        dest_lon = destination_context.get('longitude')

        # Check activity has required fields
        if 'name' not in activity or 'category' not in activity:
            return False, 'Missing activity name or category'

        # Check city mention
        activity_text = (activity.get('name', '') + ' ' + activity.get('description', '')).lower()
        if city and city not in activity_text and activity_text not in city:
            # Allow some leniency for well-known cities
            if not any(part in activity_text for part in city.split()):
                return False, f"Activity '{activity.get('name')}' not in {destination_context.get('city')}"

        # Check coordinates if present
        if activity.get('latitude') and activity.get('longitude') and dest_lat and dest_lon:
            dist_km = GeographicValidator._haversine(
                dest_lat, dest_lon,
                activity['latitude'], activity['longitude']
            )
            if dist_km > 50:
                return False, f"Activity too far ({dist_km:.1f}km) from {destination_context.get('city')}"

        return True, 'valid'

    @staticmethod
    def validate_itinerary(itinerary: Dict[str, Any], destination_context: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate entire itinerary.

        Returns:
            (is_valid, list of issues)
        """
        issues = []

        # Check each day's activities
        for day_idx, day in enumerate(itinerary.get('dailyItinerary', [])):
            for period in ['morning', 'afternoon', 'evening']:
                activity = day.get(period)
                if activity:
                    valid, reason = GeographicValidator.validate_activity(
                        {'name': activity, 'category': 'activity'},
                        destination_context
                    )
                    if not valid:
                        issues.append(f"Day {day_idx + 1} {period}: {reason}")

        return len(issues) == 0, issues

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Distance in km."""
        R = 6371
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c


class QualityValidator:
    """Validates itinerary quality against acceptance criteria."""

    # Quality dimensions
    DIMENSIONS = {
        'destination_coherence': 0.25,  # All activities in same city/country
        'schedule_realism': 0.20,       # Times are reasonable
        'variety': 0.15,                # Mix of activity types
        'practical_info': 0.20,         # Transport, hotel, emergency info
        'budget_consistency': 0.20,     # Budget matches activity recommendations
    }

    @staticmethod
    def validate_destination_coherence(itinerary: Dict[str, Any], destination_context: Dict[str, Any]) -> float:
        """
        Score: 0-1.0 (1.0 = all activities in same city)
        """
        valid, issues = GeographicValidator.validate_itinerary(itinerary, destination_context)
        if valid:
            return 1.0
        # Penalty for each issue
        return max(0, 1.0 - (len(issues) * 0.2))

    @staticmethod
    def validate_schedule_realism(itinerary: Dict[str, Any]) -> float:
        """
        Score: 0-1.0 based on schedule feasibility
        """
        days = itinerary.get('dailyItinerary', [])
        if not days:
            return 0.0

        valid_days = 0
        for day in days:
            activities = [day.get(p) for p in ['morning', 'afternoon', 'evening'] if day.get(p)]
            # Reasonable: 3-5 activities per day
            if 3 <= len(activities) <= 5:
                valid_days += 1

        return valid_days / len(days) if days else 0.0

    @staticmethod
    def validate_variety(itinerary: Dict[str, Any]) -> float:
        """
        Score: 0-1.0 based on activity type diversity
        """
        categories = set()
        for day in itinerary.get('dailyItinerary', []):
            for period in ['morning', 'afternoon', 'evening']:
                activity = day.get(period, '').lower()
                if 'museum' in activity:
                    categories.add('museum')
                elif 'market' in activity or 'shopping' in activity:
                    categories.add('market')
                elif 'temple' in activity or 'church' in activity or 'shrine' in activity:
                    categories.add('temple')
                elif 'park' in activity or 'nature' in activity:
                    categories.add('nature')
                elif 'food' in activity or 'restaurant' in activity or 'eat' in activity:
                    categories.add('food')
                elif 'walk' in activity or 'tour' in activity:
                    categories.add('tour')

        # Score based on variety (ideal: 4-5 categories)
        return min(1.0, len(categories) / 4)

    @staticmethod
    def validate_practical_info(itinerary: Dict[str, Any]) -> float:
        """
        Score: 0-1.0 based on practical information completeness
        """
        score = 0.0
        checks = [
            'hotelArea',
            'transportation',
            'emergencyNumbers',
            'weatherNotes',
            'localTips',
            'currency',
            'timezone',
        ]

        for check in checks:
            if itinerary.get(check):
                score += 1.0 / len(checks)

        return score

    @staticmethod
    def validate_budget_consistency(itinerary: Dict[str, Any]) -> float:
        """
        Score: 0-1.0 based on budget consistency with activity recommendations
        """
        budget = itinerary.get('budget', 'mid-range').lower()
        activities = itinerary.get('estimatedBudget', '').lower()

        # Simple check: luxury/expensive activities should match budget
        luxury_keywords = ['luxury', 'expensive', '5-star', 'michelin']
        budget_keywords = ['budget', 'cheap', 'affordable', 'backpacker']

        luxury_score = sum(1 for kw in luxury_keywords if kw in activities)
        budget_score = sum(1 for kw in budget_keywords if kw in activities)

        if budget == 'luxury' and luxury_score > budget_score:
            return 1.0
        elif budget == 'budget' and budget_score > luxury_score:
            return 1.0
        elif budget == 'mid-range':
            return 1.0

        return 0.5

    @staticmethod
    def calculate_overall_confidence(itinerary: Dict[str, Any], destination_context: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """
        Calculate overall itinerary confidence score (0-1.0).

        Required: >= 0.95 (95%)

        Returns:
            (overall_confidence, dimension_scores)
        """
        scores = {
            'destination_coherence': QualityValidator.validate_destination_coherence(itinerary, destination_context),
            'schedule_realism': QualityValidator.validate_schedule_realism(itinerary),
            'variety': QualityValidator.validate_variety(itinerary),
            'practical_info': QualityValidator.validate_practical_info(itinerary),
            'budget_consistency': QualityValidator.validate_budget_consistency(itinerary),
        }

        # Weighted average
        overall = sum(
            scores[dim] * QualityValidator.DIMENSIONS[dim]
            for dim in QualityValidator.DIMENSIONS
        )

        return overall, scores

    @staticmethod
    def is_acceptable(itinerary: Dict[str, Any], destination_context: Dict[str, Any], threshold: float = 0.95) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if itinerary meets acceptance criteria.

        Args:
            itinerary: Generated itinerary
            destination_context: Destination context
            threshold: Minimum confidence (default 0.95 = 95%)

        Returns:
            (is_acceptable, validation_result)
        """
        confidence, scores = QualityValidator.calculate_overall_confidence(itinerary, destination_context)

        result = {
            'is_acceptable': confidence >= threshold,
            'confidence': round(confidence * 100, 1),
            'threshold': round(threshold * 100, 1),
            'scores': {k: round(v * 100, 1) for k, v in scores.items()},
        }

        return result['is_acceptable'], result
