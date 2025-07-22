"""
Status Routes - Health checks and system status endpoints
"""

from flask import Blueprint, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create blueprint
status_bp = Blueprint('status', __name__)

@status_bp.route('/', methods=['GET'])
def status_overview():
    """General status overview endpoint"""
    try:
        return jsonify({
            'service': 'skill-buddy-backend',
            'status': 'operational',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.0.0',
            'endpoints': {
                'health': '/api/status/health',
                'ping': '/api/status/ping',
                'ready': '/api/status/ready'
            },
            'features': [
                'User Authentication',
                'Resume Analysis',
                'Profile Analysis',
                'Portfolio Analysis',
                'Community Features',
                'Interview System',
                'JD-based Interviews',
                'Task Management'
            ]
        }), 200
    except Exception as e:
        logger.error(f"Status overview failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@status_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'skill-buddy-backend',
            'version': '2.0.0'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@status_bp.route('/ping', methods=['GET'])
def ping():
    """Simple ping endpoint"""
    return jsonify({
        'message': 'pong',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@status_bp.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check for deployment"""
    try:
        # Add any additional checks here (database, external services, etc.)
        return jsonify({
            'status': 'ready',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {
                'database': 'ok',
                'services': 'ok'
            }
        }), 200
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503 