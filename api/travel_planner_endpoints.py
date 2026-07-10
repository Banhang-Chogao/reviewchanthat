#!/usr/bin/env python3
"""
FastAPI endpoints for Travel Planner persistence via Cloudflare R2.

Endpoints:
  POST   /api/travel-planner/save
  GET    /api/travel-planner/{trip_id}
  GET    /api/travel-planner/list
  PUT    /api/travel-planner/{trip_id}
  DELETE /api/travel-planner/{trip_id}
  POST   /api/travel-planner/duplicate
"""

from fastapi import APIRouter, HTTPException, Header, Body
from typing import Optional, List, Dict, Any
from services.trip_repository import TripRepository
from services.r2_storage import R2StorageError

router = APIRouter(prefix='/api/travel-planner', tags=['travel-planner'])


def get_user_id(user_agent: Optional[str] = Header(None)) -> str:
    """
    Extract or derive user ID from request.

    For now, use a fallback identifier. In production, use auth token.
    """
    # TODO: Extract from auth token or session
    # Placeholder: use fixed ID for demo
    return 'default-user'


@router.post('/save')
async def save_trip(
    trip_data: Dict[str, Any] = Body(...),
    user_agent: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Save a trip to R2.

    Request body:
    {
      "destination": "ICN",
      "destinationData": {...},
      "departure": "2026-10-15",
      "returnDate": "2026-10-22",
      ...
    }

    Returns:
    {
      "success": true,
      "trip_id": "uuid",
      "data": {...}
    }
    """
    try:
        user_id = get_user_id(user_agent)
        trip = TripRepository.create_trip(user_id, trip_data)

        return {
            'success': True,
            'trip_id': trip.get('id'),
            'data': trip
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except R2StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Unexpected error: {str(e)}')


@router.get('/{trip_id}')
async def get_trip(
    trip_id: str,
    user_agent: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Get a trip by ID.

    Returns:
    {
      "success": true,
      "data": {...}
    }
    """
    try:
        user_id = get_user_id(user_agent)
        trip = TripRepository.get_trip(user_id, trip_id)

        if not trip:
            raise HTTPException(status_code=404, detail='Trip not found')

        return {
            'success': True,
            'data': trip
        }

    except R2StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Unexpected error: {str(e)}')


@router.get('/list')
async def list_trips(
    user_agent: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    List all trips for current user.

    Returns:
    {
      "success": true,
      "trips": [...]
    }
    """
    try:
        user_id = get_user_id(user_agent)
        trips = TripRepository.list_user_trips(user_id)

        return {
            'success': True,
            'trips': trips,
            'count': len(trips)
        }

    except R2StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Unexpected error: {str(e)}')


@router.put('/{trip_id}')
async def update_trip(
    trip_id: str,
    trip_data: Dict[str, Any] = Body(...),
    user_agent: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Update a trip.

    Returns:
    {
      "success": true,
      "data": {...}
    }
    """
    try:
        user_id = get_user_id(user_agent)
        trip = TripRepository.update_trip(user_id, trip_id, trip_data)

        return {
            'success': True,
            'data': trip
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except R2StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Unexpected error: {str(e)}')


@router.delete('/{trip_id}')
async def delete_trip(
    trip_id: str,
    user_agent: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Delete a trip.

    Returns:
    {
      "success": true
    }
    """
    try:
        user_id = get_user_id(user_agent)
        success = TripRepository.delete_trip(user_id, trip_id)

        return {
            'success': success
        }

    except R2StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Unexpected error: {str(e)}')


@router.post('/duplicate')
async def duplicate_trip(
    source_trip_id: str = Body(...),
    user_agent: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Duplicate a trip.

    Request body:
    {
      "source_trip_id": "uuid"
    }

    Returns:
    {
      "success": true,
      "trip_id": "uuid",
      "data": {...}
    }
    """
    try:
        user_id = get_user_id(user_agent)
        trip = TripRepository.duplicate_trip(user_id, source_trip_id)

        return {
            'success': True,
            'trip_id': trip.get('id'),
            'data': trip
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except R2StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Unexpected error: {str(e)}')


@router.get('/{trip_id}/history')
async def get_trip_history(
    trip_id: str,
    user_agent: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Get version history for a trip.

    Returns:
    {
      "success": true,
      "history": [...]
    }
    """
    try:
        user_id = get_user_id(user_agent)
        history = TripRepository.get_trip_history(user_id, trip_id)

        return {
            'success': True,
            'history': history,
            'count': len(history)
        }

    except R2StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Unexpected error: {str(e)}')
