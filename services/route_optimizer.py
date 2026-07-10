#!/usr/bin/env python3
"""
Route Optimizer

Clusters nearby attractions and minimizes travel time.
Ensures geographic continuity and avoids backtracking.
"""

from typing import Dict, List, Any
import math


class RouteOptimizer:
    """Optimize attraction sequence for each day."""

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in kilometers."""
        R = 6371  # Earth radius in km
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    @staticmethod
    def cluster_attractions(attractions: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Cluster nearby attractions (within ~2km).

        Returns:
            List of clusters, each cluster is a list of nearby attractions
        """
        if not attractions:
            return []

        clusters = []
        used = set()

        for i, attr in enumerate(attractions):
            if i in used:
                continue

            cluster = [attr]
            used.add(i)

            for j, other in enumerate(attractions):
                if j <= i or j in used:
                    continue

                # Check if close enough (< 2km)
                if attr.get('lat') and attr.get('lon') and other.get('lat') and other.get('lon'):
                    dist = RouteOptimizer.haversine_distance(
                        attr['lat'], attr['lon'],
                        other['lat'], other['lon']
                    )
                    if dist < 2:
                        cluster.append(other)
                        used.add(j)

            clusters.append(cluster)

        return clusters

    @staticmethod
    def optimize_route(attractions: List[Dict[str, Any]], hotel_loc: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Optimize route for a single day.

        Strategy:
        1. Cluster nearby attractions
        2. Start from hotel
        3. Visit clusters in geographic order
        4. Return to hotel area
        """
        if not attractions:
            return []

        # Cluster attractions
        clusters = RouteOptimizer.cluster_attractions(attractions)

        # Sort clusters by proximity to hotel
        def cluster_distance(cluster):
            avg_lat = sum(a.get('lat', 0) for a in cluster) / len(cluster)
            avg_lon = sum(a.get('lon', 0) for a in cluster) / len(cluster)
            return RouteOptimizer.haversine_distance(
                hotel_loc['lat'], hotel_loc['lon'],
                avg_lat, avg_lon
            )

        sorted_clusters = sorted(clusters, key=cluster_distance)

        # Flatten: visit all attractions in optimized order
        optimized = []
        for cluster in sorted_clusters:
            optimized.extend(cluster)

        return optimized

    @staticmethod
    def estimate_travel_time(from_loc: Dict[str, float], to_loc: Dict[str, float]) -> int:
        """
        Estimate travel time in minutes.

        Rules:
        - Walking: ~1.4 km/h
        - Taxi: ~20 km/h (including traffic)
        - Subway: ~30 km/h (including waiting)
        """
        if not all(k in from_loc and k in to_loc for k in ['lat', 'lon']):
            return 30  # Default 30 min

        dist = RouteOptimizer.haversine_distance(
            from_loc['lat'], from_loc['lon'],
            to_loc['lat'], to_loc['lon']
        )

        # Walking distance threshold
        if dist < 1:
            return max(10, int(dist * 60 / 1.4))  # ~1.4 km/h walking
        # Short taxi/subway distance
        elif dist < 5:
            return 15
        # Medium distance
        elif dist < 15:
            return 30
        # Long distance
        else:
            return 45


class DayScheduler:
    """Schedule attractions for each day with time estimates."""

    # Time estimates (minutes)
    VISIT_DURATION = {
        'attraction': 60,
        'museum': 120,
        'landmark': 45,
        'temple': 60,
        'market': 60,
        'park': 90,
        'shopping': 120,
    }

    MEAL_DURATION = 60
    REST_DURATION = 30

    @staticmethod
    def schedule_day(attractions: List[Dict[str, Any]], hotel_loc: Dict[str, float], available_hours: int = 8) -> Dict[str, Any]:
        """
        Schedule attractions for one day.

        Constraints:
        - Total time available (minutes): available_hours * 60
        - Includes: meals (3 * 60 min), rest (30 min), travel
        - No impossible schedules
        """
        # Optimize route first
        route = RouteOptimizer.optimize_route(attractions, hotel_loc)

        # Allocate time
        available_minutes = available_hours * 60
        meal_time = 3 * DayScheduler.MEAL_DURATION  # 3 meals
        rest_time = DayScheduler.REST_DURATION
        activity_budget = available_minutes - meal_time - rest_time

        # Build itinerary
        schedule = {
            'date': '',
            'activities': [],
            'total_time': 0,
            'feasible': True,
        }

        current_time = 0
        current_loc = hotel_loc

        for attr in route:
            # Travel time
            travel = RouteOptimizer.estimate_travel_time(current_loc, {'lat': attr.get('lat', 0), 'lon': attr.get('lon', 0)})
            duration = DayScheduler.VISIT_DURATION.get(attr.get('category', 'attraction'), 60)

            # Check if fits
            if current_time + travel + duration > activity_budget:
                break

            # Add to schedule
            schedule['activities'].append({
                'name': attr.get('name', 'Unknown'),
                'category': attr.get('category', 'attraction'),
                'duration': duration,
                'travel_time': travel,
                'estimated_time': f'{(9 + current_time // 60):02d}:{current_time % 60:02d}',  # 9 AM start
            })

            current_time += travel + duration
            current_loc = {'lat': attr.get('lat', 0), 'lon': attr.get('lon', 0)}

        # Add meals and rest
        schedule['meals'] = 3
        schedule['rest_time'] = rest_time
        schedule['total_activity_time'] = current_time
        schedule['total_time'] = current_time + meal_time + rest_time

        # Check feasibility
        schedule['feasible'] = schedule['total_time'] <= available_minutes and len(schedule['activities']) > 0

        return schedule
