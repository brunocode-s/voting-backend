from flask import Blueprint, request, jsonify, session
from models import Election, Position, Candidate, Vote
from models.audit import AuditLog
from utils.decorators import login_required, admin_required
from extensions import db
from datetime import datetime

elections_bp = Blueprint('elections', __name__, url_prefix='/api')


@elections_bp.route('/elections', methods=['GET'])
def get_elections():
    """Get all elections or active elections"""
    try:
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        
        if active_only:
            elections = Election.query.filter_by(is_active=True).all()
        else:
            elections = Election.query.all()
        
        return jsonify({
            'elections': [e.to_dict() for e in elections]
        }), 200
    except Exception as e:
        print(f"ERROR in get_elections: {str(e)}")  # Add this line
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc() 
        return jsonify({'error': str(e)}), 500


@elections_bp.route('/elections/<int:election_id>', methods=['GET'])
def get_election_details(election_id):
    """Get detailed election information with positions and candidates"""
    try:
        election = Election.query.get_or_404(election_id)
        
        positions_data = []
        for position in election.positions:
            if position.is_active:
                candidates_data = []
                for c in position.candidates:
                    if c.is_active:
                        candidate_dict = c.to_dict()
                        candidate_dict['vote_count'] = Vote.query.filter_by(
                            candidate_id=c.id,
                            is_flagged=False
                        ).count()
                        candidates_data.append(candidate_dict)
                
                position_dict = position.to_dict()
                position_dict['candidates'] = candidates_data
                positions_data.append(position_dict)
        
        election_dict = election.to_dict()
        election_dict['positions'] = positions_data
        
        return jsonify({'election': election_dict}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@elections_bp.route('/elections', methods=['POST'])
@admin_required
def create_election():
    """Create a new election dynamically"""
    try:
        data = request.json
        
        new_election = Election(
            title=data['title'],
            description=data.get('description', ''),
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']),
            is_active=data.get('is_active', False),
            allow_multiple_positions=data.get('allow_multiple_positions', True),
            require_voter_verification=data.get('require_voter_verification', True),
            created_by=session['user_id']
        )
        
        db.session.add(new_election)
        db.session.commit()
        
        AuditLog.log_action(
            user_id=session['user_id'],
            action='ELECTION_CREATED',
            resource_type='election',
            resource_id=new_election.id,
            details={'title': new_election.title},
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'message': 'Election created successfully',
            'election_id': new_election.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@elections_bp.route('/elections/<int:election_id>', methods=['PUT'])
@admin_required
def update_election(election_id):
    """Update an election"""
    try:
        election = Election.query.get_or_404(election_id)
        data = request.json
        
        if 'title' in data:
            election.title = data['title']
        if 'description' in data:
            election.description = data['description']
        if 'start_date' in data:
            election.start_date = datetime.fromisoformat(data['start_date'])
        if 'end_date' in data:
            election.end_date = datetime.fromisoformat(data['end_date'])
        if 'is_active' in data:
            election.is_active = data['is_active']
        
        db.session.commit()
        
        AuditLog.log_action(
            user_id=session['user_id'],
            action='ELECTION_UPDATED',
            resource_type='election',
            resource_id=election_id,
            details=data,
            ip_address=request.remote_addr
        )
        
        return jsonify({'message': 'Election updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@elections_bp.route('/positions', methods=['POST'])
@admin_required
def create_position():
    """Create a new position dynamically"""
    try:
        data = request.json
        
        new_position = Position(
            election_id=data['election_id'],
            title=data['title'],
            description=data.get('description', ''),
            display_order=data.get('display_order', 0),
            max_candidates_to_select=data.get('max_candidates_to_select', 1)
        )
        
        db.session.add(new_position)
        db.session.commit()
        
        AuditLog.log_action(
            user_id=session['user_id'],
            action='POSITION_CREATED',
            resource_type='position',
            resource_id=new_position.id,
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'message': 'Position created successfully',
            'position_id': new_position.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@elections_bp.route('/candidates', methods=['POST'])
@admin_required
def create_candidate():
    """Create a new candidate dynamically with custom fields"""
    try:
        data = request.json
        
        # Extract custom fields
        standard_fields = ['position_id', 'name', 'party', 'biography', 'manifesto', 
                          'image_url', 'video_url', 'social_media', 'display_order']
        custom_fields = {k: v for k, v in data.items() if k not in standard_fields}
        
        new_candidate = Candidate(
            position_id=data['position_id'],
            name=data['name'],
            party=data.get('party', ''),
            biography=data.get('biography', ''),
            manifesto=data.get('manifesto', ''),
            image_url=data.get('image_url', ''),
            video_url=data.get('video_url', ''),
            social_media=data.get('social_media', {}),
            custom_fields=custom_fields if custom_fields else None,
            display_order=data.get('display_order', 0)
        )
        
        db.session.add(new_candidate)
        db.session.commit()
        
        AuditLog.log_action(
            user_id=session['user_id'],
            action='CANDIDATE_CREATED',
            resource_type='candidate',
            resource_id=new_candidate.id,
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'message': 'Candidate created successfully',
            'candidate_id': new_candidate.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@elections_bp.route('/candidates', methods=['GET'])
def get_candidates():
    """Get all active candidates"""
    try:
        candidates = Candidate.query.filter_by(is_active=True).all()

        return jsonify({
            'candidates': [{
                'id': c.id,
                'name': c.name,
                'party': c.party,
                'biography': c.biography,
                'manifesto': c.manifesto,
                'image_url': c.image_url,
                'video_url': c.video_url,
                'position_id': c.position_id,
                'position_title': c.position.title if c.position else None,
                'created_at': c.created_at.isoformat() if c.created_at else None
            } for c in candidates]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@elections_bp.route('/elections/<int:election_id>', methods=['DELETE'])
@admin_required
def delete_election(election_id):
    try:
        election = Election.query.get_or_404(election_id)

        # delete votes → candidates → positions
        for position in election.positions:
            for candidate in position.candidates:
                Vote.query.filter_by(candidate_id=candidate.id).delete()
            Candidate.query.filter_by(position_id=position.id).delete()

        Position.query.filter_by(election_id=election.id).delete()

        db.session.delete(election)
        db.session.commit()

        AuditLog.log_action(
            user_id=session['user_id'],
            action='ELECTION_DELETED',
            resource_type='election',
            resource_id=election_id,
            ip_address=request.remote_addr
        )

        return jsonify({'message': 'Election deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
