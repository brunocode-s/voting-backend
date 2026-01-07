from flask import Blueprint, request, jsonify, session
from models import User
from models.vote import FlaggedActivity
from models.audit import AuditLog, SystemConfiguration
from utils.decorators import admin_required
from utils.config_helper import get_system_config, set_system_config
from extensions import db

admin_bp = Blueprint('admin', __name__, url_prefix='/api')


@admin_bp.route('/fraud-dashboard', methods=['GET'])
@admin_required
def fraud_dashboard():
    """Get fraud detection dashboard data"""
    try:
        election_id = request.args.get('election_id', type=int)
        
        query = FlaggedActivity.query
        if election_id:
            query = query.filter_by(election_id=election_id)
        
        flagged = query.order_by(FlaggedActivity.timestamp.desc()).limit(100).all()
        
        return jsonify({
            'flagged_activities': [f.to_dict() for f in flagged],
            'summary': {
                'total_flagged': query.count(),
                'high_risk': query.filter_by(risk_level='HIGH').count(),
                'medium_risk': query.filter_by(risk_level='MEDIUM').count(),
                'resolved': query.filter_by(resolved=True).count()
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/audit-logs', methods=['GET'])
@admin_required
def get_audit_logs():
    """Get audit logs"""
    try:
        limit = request.args.get('limit', 100, type=int)
        action = request.args.get('action')
        
        query = AuditLog.query
        if action:
            query = query.filter_by(action=action)
        
        logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
        
        return jsonify({
            'logs': [log.to_dict() for log in logs]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/config', methods=['GET'])
@admin_required
def get_configuration():
    """Get system configuration"""
    try:
        configs = SystemConfiguration.query.all()
        return jsonify({
            'configurations': [c.to_dict() for c in configs]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/config', methods=['POST'])
@admin_required
def update_configuration():
    """Update system configuration"""
    try:
        data = request.json
        set_system_config(
            data['key'],
            data['value'],
            data.get('type', 'string'),
            data.get('description', '')
        )
        
        AuditLog.log_action(
            user_id=session['user_id'],
            action='CONFIG_UPDATED',
            resource_type='configuration',
            resource_id=None,
            details=data,
            ip_address=request.remote_addr
        )
        
        return jsonify({'message': 'Configuration updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """Get all users"""
    try:
        users = User.query.all()
        return jsonify({
            'users': [u.to_dict() for u in users]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update user information"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.json
        
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'is_verified' in data:
            user.is_verified = data['is_verified']
        if 'role' in data:
            user.role = data['role']
        
        db.session.commit()
        
        AuditLog.log_action(
            user_id=session['user_id'],
            action='USER_UPDATED',
            resource_type='user',
            resource_id=user_id,
            details=data,
            ip_address=request.remote_addr
        )
        
        return jsonify({'message': 'User updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/flagged-activities/<int:activity_id>/resolve', methods=['POST'])
@admin_required
def resolve_flagged_activity(activity_id):
    """Resolve a flagged activity"""
    try:
        activity = FlaggedActivity.query.get_or_404(activity_id)
        data = request.json
        
        activity.resolved = True
        activity.resolved_by = session['user_id']
        activity.resolved_at = db.func.now()
        activity.resolution_notes = data.get('notes', '')
        
        db.session.commit()
        
        AuditLog.log_action(
            user_id=session['user_id'],
            action='FLAGGED_ACTIVITY_RESOLVED',
            resource_type='flagged_activity',
            resource_id=activity_id,
            details=data,
            ip_address=request.remote_addr
        )
        
        return jsonify({'message': 'Flagged activity resolved successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500