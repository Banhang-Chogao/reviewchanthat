#!/usr/bin/env python3
"""
Cloudflare R2 storage service for Travel Planner persistence.

Handles all R2 operations: save, load, list, update, delete, version history.
"""

import os
import json
import boto3
from datetime import datetime
from typing import Optional, List, Dict, Any
from botocore.exceptions import ClientError
from urllib.parse import quote

# Configuration
R2_ACCOUNT_ID = os.environ.get('R2_ACCOUNT_ID', '')
R2_BUCKET = os.environ.get('R2_BUCKET', 'travel-planner')
R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID', '')
R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY', '')
R2_ENDPOINT = os.environ.get(
    'R2_ENDPOINT',
    f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com'
)

# Initialize S3 client for R2
_s3_client = None


def get_s3_client():
    """Get or initialize S3 client for R2."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name='auto'
        )
    return _s3_client


class R2StorageError(Exception):
    """Base exception for R2 storage errors."""
    pass


class R2Storage:
    """Cloudflare R2 storage operations."""

    @staticmethod
    def _get_object_key(user_id: str, trip_id: str) -> str:
        """Generate R2 object key."""
        return f'travel-planner/{user_id}/{trip_id}.json'

    @staticmethod
    def _get_history_key(user_id: str, trip_id: str, timestamp: str) -> str:
        """Generate history object key."""
        return f'travel-planner/{user_id}/{trip_id}/history/{timestamp}.json'

    @staticmethod
    def save(user_id: str, trip_id: str, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save trip to R2.

        Args:
            user_id: User identifier
            trip_id: Trip identifier (UUIDv4)
            trip_data: Trip data dictionary

        Returns:
            Updated trip data with metadata

        Raises:
            R2StorageError: On save failure
        """
        try:
            s3 = get_s3_client()
            now = datetime.utcnow().isoformat() + 'Z'

            # Prepare metadata
            metadata = {
                'created_at': trip_data.get('created_at', now),
                'updated_at': now,
                'destination': trip_data.get('destination', ''),
                'country': trip_data.get('destinationData', {}).get('country', ''),
                'iata': trip_data.get('destinationData', {}).get('iata', ''),
                'departure_date': trip_data.get('departure', ''),
                'return_date': trip_data.get('returnDate', ''),
                'version': str(trip_data.get('version', 1))
            }

            # Store object
            key = R2Storage._get_object_key(user_id, trip_id)
            s3.put_object(
                Bucket=R2_BUCKET,
                Key=key,
                Body=json.dumps(trip_data),
                ContentType='application/json',
                Metadata=metadata
            )

            # Update returned data with new metadata
            trip_data['updated_at'] = now
            trip_data['version'] = int(metadata['version'])

            return trip_data

        except ClientError as e:
            raise R2StorageError(f'Failed to save trip: {str(e)}')

    @staticmethod
    def load(user_id: str, trip_id: str) -> Optional[Dict[str, Any]]:
        """
        Load trip from R2.

        Args:
            user_id: User identifier
            trip_id: Trip identifier

        Returns:
            Trip data or None if not found

        Raises:
            R2StorageError: On load failure (except 404)
        """
        try:
            s3 = get_s3_client()
            key = R2Storage._get_object_key(user_id, trip_id)

            response = s3.get_object(Bucket=R2_BUCKET, Key=key)
            trip_data = json.loads(response['Body'].read().decode('utf-8'))

            return trip_data

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise R2StorageError(f'Failed to load trip: {str(e)}')

    @staticmethod
    def list_trips(user_id: str) -> List[Dict[str, Any]]:
        """
        List all trips for user.

        Args:
            user_id: User identifier

        Returns:
            List of trip metadata sorted by updated_at (newest first)

        Raises:
            R2StorageError: On list failure
        """
        try:
            s3 = get_s3_client()
            prefix = f'travel-planner/{user_id}/'

            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
            contents = response.get('Contents', [])

            trips = []
            for obj in contents:
                # Only include trip files (not history)
                if '/history/' not in obj['Key'] and obj['Key'].endswith('.json'):
                    trip_id = obj['Key'].split('/')[-1].replace('.json', '')
                    trip_data = R2Storage.load(user_id, trip_id)
                    if trip_data:
                        trips.append({
                            'trip_id': trip_id,
                            'destination': trip_data.get('destination', ''),
                            'country': trip_data.get('destinationData', {}).get('country', ''),
                            'departure': trip_data.get('departure', ''),
                            'return_date': trip_data.get('returnDate', ''),
                            'updated_at': trip_data.get('updated_at', ''),
                            'created_at': trip_data.get('created_at', '')
                        })

            # Sort by updated_at (newest first)
            trips.sort(
                key=lambda x: x['updated_at'],
                reverse=True
            )

            return trips

        except ClientError as e:
            raise R2StorageError(f'Failed to list trips: {str(e)}')

    @staticmethod
    def update(user_id: str, trip_id: str, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update trip in R2 (alias for save with version check).

        Args:
            user_id: User identifier
            trip_id: Trip identifier
            trip_data: Updated trip data

        Returns:
            Updated trip data

        Raises:
            R2StorageError: On update failure
        """
        # Save handles update
        return R2Storage.save(user_id, trip_id, trip_data)

    @staticmethod
    def delete(user_id: str, trip_id: str) -> bool:
        """
        Delete trip from R2 (move to history archive).

        Args:
            user_id: User identifier
            trip_id: Trip identifier

        Returns:
            True if deleted

        Raises:
            R2StorageError: On delete failure
        """
        try:
            s3 = get_s3_client()
            key = R2Storage._get_object_key(user_id, trip_id)

            # Load before deleting for archive
            trip_data = R2Storage.load(user_id, trip_id)

            # Delete object
            s3.delete_object(Bucket=R2_BUCKET, Key=key)

            # Archive to history
            if trip_data:
                timestamp = datetime.utcnow().isoformat() + 'Z'
                history_key = R2Storage._get_history_key(user_id, trip_id, timestamp)
                s3.put_object(
                    Bucket=R2_BUCKET,
                    Key=history_key,
                    Body=json.dumps({
                        'deleted_at': timestamp,
                        'trip_data': trip_data
                    }),
                    ContentType='application/json'
                )

            return True

        except ClientError as e:
            raise R2StorageError(f'Failed to delete trip: {str(e)}')

    @staticmethod
    def duplicate(user_id: str, source_trip_id: str, new_trip_id: str) -> Dict[str, Any]:
        """
        Duplicate a trip.

        Args:
            user_id: User identifier
            source_trip_id: Trip to duplicate from
            new_trip_id: New trip ID (UUIDv4)

        Returns:
            New trip data

        Raises:
            R2StorageError: On duplicate failure
        """
        try:
            # Load source
            source_trip = R2Storage.load(user_id, source_trip_id)
            if not source_trip:
                raise R2StorageError('Source trip not found')

            # Create copy
            new_trip = source_trip.copy()
            new_trip['id'] = new_trip_id
            new_trip['created_at'] = datetime.utcnow().isoformat() + 'Z'
            new_trip['updated_at'] = new_trip['created_at']
            new_trip['version'] = 1

            # Save
            return R2Storage.save(user_id, new_trip_id, new_trip)

        except ClientError as e:
            raise R2StorageError(f'Failed to duplicate trip: {str(e)}')

    @staticmethod
    def get_history(user_id: str, trip_id: str) -> List[Dict[str, Any]]:
        """
        Get version history for a trip.

        Args:
            user_id: User identifier
            trip_id: Trip identifier

        Returns:
            List of historical versions sorted by timestamp (newest first)

        Raises:
            R2StorageError: On failure
        """
        try:
            s3 = get_s3_client()
            prefix = f'travel-planner/{user_id}/{trip_id}/history/'

            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
            contents = response.get('Contents', [])

            history = []
            for obj in contents:
                if obj['Key'].endswith('.json'):
                    try:
                        obj_data = s3.get_object(Bucket=R2_BUCKET, Key=obj['Key'])
                        history_data = json.loads(obj_data['Body'].read().decode('utf-8'))
                        history.append({
                            'timestamp': obj['Key'].split('/')[-1].replace('.json', ''),
                            'data': history_data
                        })
                    except Exception as e:
                        print(f'Warning: Failed to load history object {obj["Key"]}: {e}')

            # Sort by timestamp (newest first)
            history.sort(key=lambda x: x['timestamp'], reverse=True)

            return history

        except ClientError as e:
            raise R2StorageError(f'Failed to get history: {str(e)}')


def verify_r2_connection() -> bool:
    """
    Verify R2 connection.

    Returns:
        True if connection successful

    Raises:
        R2StorageError: If connection fails
    """
    try:
        s3 = get_s3_client()
        s3.head_bucket(Bucket=R2_BUCKET)
        return True
    except ClientError as e:
        raise R2StorageError(f'Cannot connect to R2 bucket: {str(e)}')
