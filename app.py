#!/usr/bin/env python3
"""
Simple Flask app for Travel Planner API.
Wraps Python services for destination search and other endpoints.
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys

# Add services to path
sys.path.insert(0, os.path.dirname(__file__))

from services.city_lookup import search_destination

app = Flask(__name__)
CORS(app)


@app.route('/api/destination/search', methods=['GET', 'OPTIONS'])
def api_destination_search():
    """Search for destinations by city name or IATA code."""
    if request.method == 'OPTIONS':
        return '', 204

    q = request.args.get('q', '').strip()

    if not q:
        return jsonify({'error': 'Missing query parameter: q'}), 400

    if len(q) < 2:
        return jsonify({'error': 'Query must be at least 2 characters'}), 400

    try:
        result = search_destination(q)
        return jsonify(result), 200
    except Exception as e:
        print(f'Error: {e}')
        return jsonify({
            'success': False,
            'query': q,
            'error': str(e),
            'results': []
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200


@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'service': 'Travel Planner API',
        'endpoints': {
            '/api/destination/search?q=<query>': 'Search destinations',
            '/health': 'Health check'
        }
    }), 200


if __name__ == '__main__':
    # Development: use debug mode
    # Production: use gunicorn or uwsgi
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
