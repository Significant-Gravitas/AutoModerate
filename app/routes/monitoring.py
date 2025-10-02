"""Monitoring and health check endpoints"""
from flask import Blueprint, jsonify

monitoring_bp = Blueprint('monitoring', __name__)


@monitoring_bp.route('/health')
def health_check():
    """Basic health check endpoint for load balancers and uptime monitoring"""
    return jsonify({
        'status': 'healthy',
        'service': 'AutoModerate'
    })
