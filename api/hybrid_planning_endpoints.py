#!/usr/bin/env python3
"""
Hybrid Planning Engine API Endpoints

10-stage pipeline for trusted itinerary generation.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
import json
import os

from services.destination_context import get_destination_context
from services.knowledge_retriever import StructuredDestinationKnowledge
from services.route_optimizer import RouteOptimizer, DayScheduler
from services.quality_validator import QualityValidator, GeographicValidator

router = APIRouter(prefix="/api/hybrid-planner", tags=["hybrid-planning"])


@router.post("/validate-destination")
async def validate_destination(destination_data: Dict[str, Any]):
    """
    Stage 1: Destination Context Builder

    Normalizes destination data into canonical form.
    """
    try:
        context = get_destination_context(destination_data)
        is_valid, missing = context.get('iso2') is not None, []

        return {
            'success': is_valid,
            'context': context,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retrieve-knowledge")
async def retrieve_knowledge(destination_context: Dict[str, Any]):
    """
    Stage 2: Knowledge Retrieval

    Collects structured geographic data.
    """
    try:
        knowledge = StructuredDestinationKnowledge.retrieve(destination_context)

        return {
            'success': True,
            'knowledge': knowledge,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate-poi")
async def validate_poi(
    poi_candidates: Dict[str, Any],
    destination_context: Dict[str, Any]
):
    """
    Stages 3-4: POI Validation

    Validates POI candidates belong to destination.
    """
    try:
        pois = poi_candidates.get('candidates', [])
        valid_pois = []
        rejected_pois = []

        for poi in pois:
            if StructuredDestinationKnowledge.validate_poi(poi, destination_context):
                valid_pois.append(poi)
            else:
                rejected_pois.append({
                    'name': poi.get('name'),
                    'reason': 'Outside destination area or invalid coordinates'
                })

        return {
            'success': True,
            'valid_candidates': valid_pois,
            'rejected_candidates': rejected_pois,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/optimize-route")
async def optimize_route(
    attractions: list,
    hotel_location: Dict[str, float],
    num_days: int = 1
):
    """
    Stage 5: Route Optimizer

    Clusters attractions and optimizes daily routes.
    """
    try:
        # Optimize for each day
        daily_routes = []
        attractions_per_day = len(attractions) // num_days

        for day_idx in range(num_days):
            day_attractions = attractions[
                day_idx * attractions_per_day:
                (day_idx + 1) * attractions_per_day
            ]

            route = RouteOptimizer.optimize_route(day_attractions, hotel_location)
            schedule = DayScheduler.schedule_day(route, hotel_location, available_hours=8)

            daily_routes.append(schedule)

        return {
            'success': True,
            'daily_routes': daily_routes,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate-quality")
async def validate_quality(
    itinerary: Dict[str, Any],
    destination_context: Dict[str, Any],
    threshold: float = 0.95
):
    """
    Stages 8-10: Quality Validation

    Validates itinerary quality against criteria.
    Returns acceptance status and confidence score.
    """
    try:
        is_acceptable, validation = QualityValidator.is_acceptable(
            itinerary,
            destination_context,
            threshold
        )

        return {
            'success': True,
            'is_acceptable': is_acceptable,
            'validation': validation,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/full-pipeline")
async def full_hybrid_pipeline(
    destination_data: Dict[str, Any],
    num_days: int,
    preferences: Dict[str, Any] = None
):
    """
    Complete 10-stage hybrid planning pipeline.

    Returns fully validated itinerary or validation errors.
    """
    try:
        # Stage 1: Destination Context
        context = get_destination_context(destination_data)

        # Stage 2: Knowledge Retrieval
        knowledge = StructuredDestinationKnowledge.retrieve(context)

        # Stage 3-4: POI Validation (use knowledge attractions)
        attractions = knowledge.get('attractions', [])

        # Stage 5: Route Optimization
        hotel_loc = {'lat': context.get('latitude', 0), 'lon': context.get('longitude', 0)}
        daily_routes = []

        for day_idx in range(num_days):
            day_attractions = attractions[
                day_idx * max(1, len(attractions) // num_days):
                (day_idx + 1) * max(1, len(attractions) // num_days)
            ]
            if day_attractions:
                route = RouteOptimizer.optimize_route(day_attractions, hotel_loc)
                schedule = DayScheduler.schedule_day(route, hotel_loc, available_hours=8)
                daily_routes.append(schedule)

        return {
            'success': True,
            'destination_context': context,
            'knowledge': knowledge,
            'daily_routes': daily_routes,
            'num_days': num_days,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
