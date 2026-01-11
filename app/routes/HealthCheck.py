from flask import Blueprint, jsonify
from datetime import datetime

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify the API is running.
    Returns status, timestamp, and service information.
    """
    return jsonify({
        'status': 'healthy',
        'message': 'API is running successfully',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'FYP Backend API'
    }), 200
