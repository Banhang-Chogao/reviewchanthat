#!/usr/bin/env python3
"""
Trip repository - domain logic layer for trip persistence.

Abstracts R2 storage operations with business logic.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from services.r2_storage import R2Storage, R2StorageError


class TripRepository:
    """Repository pattern for trip persistence."""

    @staticmethod
    def create_trip(user_id: str, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new trip.

        Args:
            user_id: User identifier
            trip_data: Trip data

        Returns:
            Created trip with ID and metadata

        Raises:
            ValueError: On validation failure
            R2StorageError: On storage failure
        """
        if not user_id:
            raise ValueError('user_id is required')

        # Generate trip ID
        trip_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + 'Z'

        # Initialize metadata
        trip_data['id'] = trip_id
        trip_data['created_at'] = now
        trip_data['updated_at'] = now
        trip_data['version'] = 1

        # Save to R2
        return R2Storage.save(user_id, trip_id, trip_data)

    @staticmethod
    def get_trip(user_id: str, trip_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a trip by ID.

        Args:
            user_id: User identifier
            trip_id: Trip identifier

        Returns:
            Trip data or None if not found
        """
        return R2Storage.load(user_id, trip_id)

    @staticmethod
    def list_user_trips(user_id: str) -> List[Dict[str, Any]]:
        """
        List all trips for a user.

        Args:
            user_id: User identifier

        Returns:
            List of trips sorted by updated_at (newest first)
        """
        return R2Storage.list_trips(user_id)

    @staticmethod
    def update_trip(user_id: str, trip_id: str, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a trip.

        Args:
            user_id: User identifier
            trip_id: Trip identifier
            trip_data: Updated trip data

        Returns:
            Updated trip

        Raises:
            ValueError: On validation failure
            R2StorageError: On storage failure
        """
        if not user_id or not trip_id:
            raise ValueError('user_id and trip_id are required')

        # Preserve original metadata
        existing = R2Storage.load(user_id, trip_id)
        if existing:
            trip_data['id'] = trip_id
            trip_data['created_at'] = existing.get('created_at', trip_data.get('created_at'))
            trip_data['version'] = (existing.get('version', 1) or 1) + 1
        else:
            trip_data['id'] = trip_id
            trip_data['created_at'] = trip_data.get('created_at', datetime.utcnow().isoformat() + 'Z')
            trip_data['version'] = 1

        return R2Storage.update(user_id, trip_id, trip_data)

    @staticmethod
    def delete_trip(user_id: str, trip_id: str) -> bool:
        """
        Delete a trip.

        Args:
            user_id: User identifier
            trip_id: Trip identifier

        Returns:
            True if deleted
        """
        return R2Storage.delete(user_id, trip_id)

    @staticmethod
    def duplicate_trip(user_id: str, source_trip_id: str) -> Dict[str, Any]:
        """
        Duplicate a trip.

        Args:
            user_id: User identifier
            source_trip_id: Trip to duplicate

        Returns:
            Duplicated trip

        Raises:
            ValueError: On validation failure
            R2StorageError: On storage failure
        """
        if not user_id or not source_trip_id:
            raise ValueError('user_id and source_trip_id are required')

        new_trip_id = str(uuid.uuid4())
        return R2Storage.duplicate(user_id, source_trip_id, new_trip_id)

    @staticmethod
    def get_trip_history(user_id: str, trip_id: str) -> List[Dict[str, Any]]:
        """
        Get version history for a trip.

        Args:
            user_id: User identifier
            trip_id: Trip identifier

        Returns:
            List of historical versions
        """
        return R2Storage.get_history(user_id, trip_id)

    @staticmethod
    def get_latest_trip(user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recently updated trip for a user.

        Args:
            user_id: User identifier

        Returns:
            Most recent trip or None if no trips exist
        """
        trips = R2Storage.list_trips(user_id)
        return trips[0] if trips else None
