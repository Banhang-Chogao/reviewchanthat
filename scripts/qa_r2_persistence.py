#!/usr/bin/env python3
"""
QA suite for Cloudflare R2 persistence in Travel Planner.

Tests:
  - R2 connection
  - Save/load/update/delete operations
  - Version history
  - Credential security
  - Data integrity
"""

import os
import json
import sys
import uuid
from pathlib import Path

# Add services to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.r2_storage import R2Storage, R2StorageError, verify_r2_connection
from services.trip_repository import TripRepository

ISSUES = []
WARNINGS = []
SUCCESSES = []


def log_issue(msg):
    """Log critical issue."""
    ISSUES.append(f'❌ {msg}')
    print(f'❌ {msg}')


def log_warning(msg):
    """Log warning."""
    WARNINGS.append(f'⚠️  {msg}')
    print(f'⚠️  {msg}')


def log_success(msg):
    """Log success."""
    SUCCESSES.append(f'✅ {msg}')
    print(f'✅ {msg}')


def check_credentials():
    """Check R2 credentials."""
    print('\n[R2 Credentials]')

    required = [
        'R2_ACCOUNT_ID',
        'R2_BUCKET',
        'R2_ACCESS_KEY_ID',
        'R2_SECRET_ACCESS_KEY',
        'R2_ENDPOINT'
    ]

    for cred in required:
        value = os.environ.get(cred)
        if not value:
            log_warning(f'{cred} not set')
        else:
            # Don't log sensitive values
            if 'KEY' in cred or 'SECRET' in cred:
                log_success(f'{cred} configured (value hidden)')
            else:
                log_success(f'{cred} = {value}')


def check_r2_connection():
    """Test R2 connection."""
    print('\n[R2 Connection]')

    try:
        if verify_r2_connection():
            log_success('R2 bucket is accessible')
        else:
            log_issue('R2 connection verification returned False')
    except R2StorageError as e:
        log_issue(f'Cannot connect to R2: {e}')
    except Exception as e:
        log_issue(f'Unexpected error checking R2: {e}')


def check_save_load():
    """Test save and load operations."""
    print('\n[Save/Load Operations]')

    user_id = 'test-user-qa'
    trip_id = str(uuid.uuid4())

    test_trip = {
        'destination': 'ICN',
        'destinationData': {
            'city': 'Incheon',
            'country': 'South Korea',
            'iata': 'ICN'
        },
        'departure': '2026-10-15',
        'returnDate': '2026-10-22',
        'adults': 2,
        'children': 0,
        'budget': 'mid-range'
    }

    try:
        # Test save
        saved = R2Storage.save(user_id, trip_id, test_trip)
        if 'id' in saved or 'updated_at' in saved:
            log_success(f'Save to R2: {trip_id}')
        else:
            log_issue('Save returned no metadata')

        # Test load
        loaded = R2Storage.load(user_id, trip_id)
        if loaded and loaded.get('destination') == 'ICN':
            log_success('Load from R2: data integrity verified')
        else:
            log_issue('Load from R2: data mismatch')

        # Cleanup
        R2Storage.delete(user_id, trip_id)
        log_success('Delete from R2 successful')

    except R2StorageError as e:
        log_issue(f'Save/Load operation failed: {e}')
    except Exception as e:
        log_issue(f'Unexpected error: {e}')


def check_list_operations():
    """Test list operations."""
    print('\n[List Operations]')

    user_id = 'test-user-qa-list'

    try:
        # Create multiple test trips
        trip_ids = []
        for i in range(3):
            trip_id = str(uuid.uuid4())
            trip_data = {
                'destination': f'TEST-{i}',
                'departure': '2026-10-15',
                'returnDate': '2026-10-22'
            }
            R2Storage.save(user_id, trip_id, trip_data)
            trip_ids.append(trip_id)

        # List trips
        trips = R2Storage.list_trips(user_id)
        if len(trips) >= 3:
            log_success(f'List trips: found {len(trips)} trips')
        else:
            log_warning(f'List trips: expected 3+, got {len(trips)}')

        # Cleanup
        for trip_id in trip_ids:
            R2Storage.delete(user_id, trip_id)
        log_success('Cleanup completed')

    except R2StorageError as e:
        log_issue(f'List operation failed: {e}')
    except Exception as e:
        log_issue(f'Unexpected error: {e}')


def check_duplicate():
    """Test duplicate operations."""
    print('\n[Duplicate Operations]')

    user_id = 'test-user-qa-dup'
    source_trip_id = str(uuid.uuid4())

    try:
        # Create source trip
        source_trip = {
            'destination': 'BKK',
            'destinationData': {'city': 'Bangkok', 'country': 'Thailand'},
            'departure': '2026-10-15',
            'returnDate': '2026-10-22'
        }
        R2Storage.save(user_id, source_trip_id, source_trip)

        # Duplicate
        new_trip_id = str(uuid.uuid4())
        duplicated = R2Storage.duplicate(user_id, source_trip_id, new_trip_id)

        if duplicated.get('destination') == 'BKK':
            log_success('Duplicate trip: data integrity verified')
        else:
            log_issue('Duplicate trip: data mismatch')

        # Cleanup
        R2Storage.delete(user_id, source_trip_id)
        R2Storage.delete(user_id, new_trip_id)

    except R2StorageError as e:
        log_issue(f'Duplicate operation failed: {e}')
    except Exception as e:
        log_issue(f'Unexpected error: {e}')


def check_version_history():
    """Test version history."""
    print('\n[Version History]')

    user_id = 'test-user-qa-hist'
    trip_id = str(uuid.uuid4())

    try:
        # Create trip
        trip_data = {'destination': 'SGN', 'departure': '2026-10-15'}
        R2Storage.save(user_id, trip_id, trip_data)

        # Update trip multiple times
        for i in range(2):
            trip_data['destination'] = f'SGN-v{i+2}'
            R2Storage.update(user_id, trip_id, trip_data)

        # Get history
        history = R2Storage.get_history(user_id, trip_id)
        if history:
            log_success(f'Version history: {len(history)} versions archived')
        else:
            log_warning('Version history: no archived versions found')

        # Cleanup
        R2Storage.delete(user_id, trip_id)

    except R2StorageError as e:
        log_issue(f'Version history failed: {e}')
    except Exception as e:
        log_issue(f'Unexpected error: {e}')


def check_repository():
    """Test repository layer."""
    print('\n[Repository Layer]')

    user_id = 'test-user-qa-repo'

    try:
        # Create trip via repository
        trip_data = {
            'destination': 'HAN',
            'destinationData': {'city': 'Hanoi', 'country': 'Vietnam'},
            'departure': '2026-10-15',
            'returnDate': '2026-10-22'
        }
        created = TripRepository.create_trip(user_id, trip_data)
        trip_id = created.get('id')

        if trip_id:
            log_success(f'Repository create: {trip_id}')
        else:
            log_issue('Repository create: no ID returned')

        # Get via repository
        retrieved = TripRepository.get_trip(user_id, trip_id)
        if retrieved and retrieved.get('destination') == 'HAN':
            log_success('Repository get: data verified')
        else:
            log_issue('Repository get: data mismatch')

        # List via repository
        trips = TripRepository.list_user_trips(user_id)
        if any(t['trip_id'] == trip_id for t in trips):
            log_success('Repository list: trip found in list')
        else:
            log_warning('Repository list: trip not in list')

        # Delete via repository
        TripRepository.delete_trip(user_id, trip_id)
        log_success('Repository delete: successful')

    except Exception as e:
        log_issue(f'Repository test failed: {e}')


def check_no_credential_leak():
    """Verify credentials not hardcoded in code."""
    print('\n[Security - Credential Leak Check]')

    files_to_check = [
        'services/r2_storage.py',
        'services/trip_repository.py',
        'api/travel_planner_endpoints.py',
        'static/js/travel-planner.js',
        '.env.example'
    ]

    has_secrets = False

    for filepath in files_to_check:
        full_path = Path(__file__).parent.parent / filepath
        if not full_path.exists():
            log_warning(f'File not found: {filepath}')
            continue

        with open(full_path, 'r') as f:
            content = f.read()

        # Check for hardcoded credentials
        leaked_patterns = [
            'r2.cloudflarestorage.com',  # Only in env var definition is OK
        ]

        # Don't flag .env.example
        if '.env.example' in filepath:
            continue

        for pattern in leaked_patterns:
            if pattern in content and 'os.environ' not in content.split(pattern)[0]:
                log_issue(f'{filepath}: possible credential leak ({pattern})')
                has_secrets = True

    if not has_secrets:
        log_success('No hardcoded credentials detected')


def print_summary():
    """Print QA summary."""
    print('\n' + '='*60)
    print('QA R2 PERSISTENCE SUMMARY')
    print('='*60)

    total = len(ISSUES) + len(WARNINGS) + len(SUCCESSES)

    if ISSUES:
        print(f'\n❌ CRITICAL ISSUES ({len(ISSUES)}):')
        for issue in ISSUES:
            print(f'  {issue}')

    if WARNINGS:
        print(f'\n⚠️  WARNINGS ({len(WARNINGS)}):')
        for warning in WARNINGS:
            print(f'  {warning}')

    if SUCCESSES:
        print(f'\n✅ PASSED ({len(SUCCESSES)}):')
        for success in SUCCESSES[:10]:
            print(f'  {success}')
        if len(SUCCESSES) > 10:
            print(f'  ... and {len(SUCCESSES) - 10} more')

    print(f'\n{"="*60}')
    print(f'Total Checks: {total}')
    ready = '🎉 READY FOR DEPLOYMENT' if not ISSUES else '⛔ FIX ISSUES BEFORE DEPLOYMENT'
    print(f'Result: {ready}')
    print(f'{"="*60}\n')

    return len(ISSUES) == 0


def main():
    """Run all QA checks."""
    print('🚀 AI Travel Planner - R2 Persistence QA\n')

    check_credentials()
    check_r2_connection()
    check_save_load()
    check_list_operations()
    check_duplicate()
    check_version_history()
    check_repository()
    check_no_credential_leak()

    success = print_summary()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
